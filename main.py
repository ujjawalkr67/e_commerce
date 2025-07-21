from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from bson import ObjectId
from typing import List, Optional
import os
from datetime import datetime
import re
from urllib.parse import quote_plus
from bson import ObjectId
from dotenv import load_dotenv

from models import (
    ProductCreate, ProductCreateResponse, ProductListingItem, ProductListResponse, PaginationInfo,
    OrderCreate, OrderCreateResponse, OrderItemRequest, OrderResponse, OrderItemResponse,
    ProductDetailsInOrder, OrderListResponse
)

# Initialize FastAPI app
app = FastAPI(
    title="Ecommerce Backend API",
    description="A sample ecommerce backend built with FastAPI and MongoDB",
    version="1.0.0"
)

load_dotenv()

# --- MongoDB Connection ---
# Retrieve individual components from environment variables
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_CLUSTER_URL = os.getenv("MONGO_CLUSTER_URL")
MONGO_APP_NAME = os.getenv("MONGO_APP_NAME")
MONGO_DATABASE_NAME = os.getenv("MONGO_DATABASE_NAME") # For the default database connection

# Validate that all required environment variables are set
if not all([MONGO_USERNAME, MONGO_PASSWORD, MONGO_CLUSTER_URL, MONGO_APP_NAME, MONGO_DATABASE_NAME]):
    raise ValueError("One or more MongoDB environment variables (MONGO_USERNAME, MONGO_PASSWORD, MONGO_CLUSTER_URL, MONGO_APP_NAME, MONGO_DATABASE_NAME) are not set. Please check your .env file.")

# URL-encode the password
encoded_password = quote_plus(MONGO_PASSWORD)

# Construct the MongoDB URI
MONGO_URI = f"mongodb+srv://{MONGO_USERNAME}:{encoded_password}@{MONGO_CLUSTER_URL}/?retryWrites=true&w=majority&appName={MONGO_APP_NAME}"

try:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DATABASE_NAME]
    products_collection = db.products
    orders_collection = db.orders
    
    # Test connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

@app.get("/")
async def root():
    return {"message": "Ecommerce Backend API is running!"}

@app.post("/products", response_model=ProductCreateResponse, status_code=201)
async def create_product(product: ProductCreate):
    """
    Create a new product with name, price, and available sizes.
    """
    try:
        # Convert Pydantic model to dict, ensuring sizes are correctly structured
        product_dict = product.model_dump(by_alias=True) # Use model_dump to get dictionary, by_alias=True to use aliases if any

        # Add timestamp for creation
        product_dict["created_at"] = datetime.utcnow()

        # Insert into MongoDB
        result = products_collection.insert_one(product_dict)

        # Return only the ID as per spec 
        return ProductCreateResponse(id=str(result.inserted_id)) # Directly return the dictionary for FastAPI to serialize
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating product: {str(e)}")


@app.get("/products", response_model=ProductListResponse, status_code=200)
async def list_products(
    name: Optional[str] = Query(None, description="Filter by product name (supports partial search/regex)"),
    size: Optional[str] = Query(None, description="Filter by available size (e.g., 'large')"),
    limit: int = Query(10, ge=1, le=100, description="Number of documents to return"),
    offset: int = Query(0, ge=0, description="Number of documents to skip while paginating (sorted by _id)")
):
    """
    List products with optional filtering by name (regex/partial) and size,
    and supports pagination.
    """
    try:
        query_filter = {}

        if name:
            # Use regex for partial name search (case-insensitive) [cite: 33]
            query_filter["name"] = {"$regex": re.escape(name), "$options": "i"}

        if size:
            # Filter products where any of the 'sizes' sub-documents contains the specified size string
            # This looks for products that have a size document where the 'size' field matches. 
            query_filter["sizes.size"] = size

        # Fetch products with pagination
        # Sort by _id for consistent pagination [cite: 36]
        cursor = products_collection.find(query_filter).sort("_id", 1).skip(offset).limit(limit)
        products = []
        for product_doc in cursor:
            # Manually map to ProductListingItem, handling _id to id [cite: 40, 46, 48]
            products.append(
                ProductListingItem(
                    id=str(product_doc["_id"]),
                    name=product_doc["name"],
                    price=product_doc["price"]
                )
            )

        # Calculate pagination info [cite: 53]
        next_offset = offset + limit if len(products) == limit else None
        previous_offset = offset - limit if offset - limit >= 0 else -10 # Spec says -10 if no previous [cite: 56]
        # In a real app, 'next' and 'previous' would ideally point to actual URLs or specific IDs
        # Here, we're mimicking the "next page starting index" with offsets.

        # Ensure "previous" is null/None if it's the first page
        if offset == 0:
            previous_offset = None

        page_info = PaginationInfo(
            next=str(next_offset) if next_offset is not None else None,
            limit=len(products), # number of records in current page 
            previous=str(previous_offset) if previous_offset is not None else None
        )

        return ProductListResponse(data=products, page=page_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching products: {str(e)}")


@app.post("/orders", response_model=OrderCreateResponse, status_code=201)
async def create_order(order: OrderCreate):
    """
    Create a new order for a user, validating product existence and calculating total.
    """
    try:
        total_amount = 0.0
        order_items_to_store = []

        for item_request in order.items:
            # Find product by ID
            # Ensure the product ID is a valid ObjectId before querying
            try:
                product_id_obj = ObjectId(item_request.productId)
            except Exception:
                raise HTTPException(status_code=400, detail=f"Invalid productId format: {item_request.productId}")

            product = products_collection.find_one({"_id": product_id_obj})
            if not product:
                raise HTTPException(status_code=404, detail=f"Product with ID {item_request.productId} not found")

            item_total = product["price"] * item_request.qty
            total_amount += item_total

            order_items_to_store.append({
                "productId": product_id_obj, # Store as string
                "qty": item_request.qty,
                "price_at_order": product["price"] # Store price at time of order for historical accuracy
            })

        # Create order document
        order_dict = {
            "userId": order.userId, # Use userId as per model
            "items": order_items_to_store,
            "total": total_amount, # Use total as per model
            "created_at": datetime.utcnow(),
            "status": "pending" # Example status
        }

        # Insert into MongoDB
        result = orders_collection.insert_one(order_dict)

        # Return only the ID as per spec 
        return OrderCreateResponse(id=str(result.inserted_id))
    except HTTPException:
        raise # Re-raise HTTPException directly
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating order: {str(e)}")


@app.get("/orders/{user_id}", response_model=OrderListResponse, status_code=200)
async def get_user_orders(
    user_id: str,
    limit: int = Query(10, ge=1, le=100, description="Number of documents to return"),
    offset: int = Query(0, ge=0, description="Number of documents to skip while paginating (sorted by _id)")
):
    """
    Get list of orders for a specific user with pagination and product details lookup.
    """
    try:
        query_filter = {"userId": user_id}
        total_count = orders_collection.count_documents(query_filter)

        pipeline = [
            {"$match": query_filter},
            {"$sort": {"_id": 1}},
            {"$skip": offset},
            {"$limit": limit},
            {"$unwind": "$items"},
            {
                "$lookup": {
                    "from": "products",
                    "localField": "items.productId",
                    "foreignField": "_id",
                    "as": "itemProductDetails"
                }
            },
            {"$unwind": "$itemProductDetails"},
            {
                "$group": {
                    "_id": "$_id", # Group back by order ID
                    "userId": {"$first": "$userId"},
                    "total": {"$first": "$total"},
                    "created_at": {"$first": "$created_at"},
                    "items": {
                        "$push": {
                            "productDetails": {
                                # CHANGE HERE: Project it as '_id' for internal Pydantic validation
                                "_id": "$itemProductDetails._id",
                                "name": "$itemProductDetails.name"
                            },
                            "qty": "$items.qty"
                        }
                    }
                }
            },
            {"$project": {
                # CHANGE HERE: Project the top-level order ID as '_id' for internal Pydantic validation
                "_id": "$_id", # Keep _id for the top-level OrderResponse model
                "items": 1,
                "total": 1
                # No need to explicitly map to "id": {"$toString": "$_id"} here.
                # Pydantic's `OrderResponse(id: Annotated[PyObjectId, BeforeValidator(str)] = Field(alias="_id", ...))`
                # will handle mapping the incoming '_id' to its 'id' field for the final JSON output.
            }}
        ]

        orders_cursor = orders_collection.aggregate(pipeline)
        orders_data_raw = list(orders_cursor)

        orders_response_list = []
        for order_doc in orders_data_raw:
            # Here, OrderResponse(**order_doc) will correctly receive '_id' and map it to 'id'
            # due to Field(alias="_id") and populate_by_name=True
            orders_response_list.append(OrderResponse(**order_doc))

                # Calculate pagination info [cite: 111]
        next_offset = offset + limit if len(orders_response_list) == limit else None
        previous_offset = offset - limit if offset - limit >= 0 else -10 # Spec says -10 if no previous [cite: 114]

        if offset == 0:
            previous_offset = None

        page_info = PaginationInfo(
            next=str(next_offset) if next_offset is not None else None,
            limit=len(orders_response_list), # number of records in current page
            previous=str(previous_offset) if previous_offset is not None else None
        )
        return OrderListResponse(data=orders_response_list, page=page_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching orders: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
