from pydantic import BaseModel, Field, BeforeValidator, conlist
from typing import List, Optional, Dict, Any
from typing_extensions import Annotated

from bson import ObjectId

# Custom ObjectId Pydantic type for MongoDB _id
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema) -> None:
        field_schema.type = "string"
        field_schema.format = "mongo-objectid"


# --- Product Models ---

class ProductSize(BaseModel):
    size: str = Field(..., description="Size of the product (e.g., S, M, L)")
    quantity: int = Field(..., ge=0, description="Quantity available for this size")

class ProductCreate(BaseModel):
    name: str = Field(..., description="Product name")
    price: float = Field(..., gt=0, description="Product price")
    sizes: List[ProductSize] = Field(..., description="Available sizes and their quantities")

class ProductCreateResponse(BaseModel):
    id: Annotated[PyObjectId, BeforeValidator(str)] = Field(alias="_id", description="Unique ID of the created product")

    class Config:
        populate_by_name = True 
        arbitrary_types_allowed = True 
        json_encoders = {ObjectId: str} 

class ProductListingItem(BaseModel):
    id: Annotated[PyObjectId, BeforeValidator(str)] = Field(alias="_id", description="Unique ID of the product")
    name: str = Field(..., description="Product name")
    price: float = Field(..., description="Product price")
    
    class Config:
        populate_by_name = True 
        arbitrary_types_allowed = True 
        json_encoders = {ObjectId: str} 

class PaginationInfo(BaseModel):
    next: Optional[str] = Field(None, description="Next page starting index/ID")
    limit: int = Field(0, description="Number of records in current page")
    previous: Optional[str] = Field(None, description="Previous page starting index/ID")

class ProductListResponse(BaseModel):
    data: List[ProductListingItem]
    page: PaginationInfo

# --- Order Models ---

class OrderItemRequest(BaseModel):
    productId: str = Field(..., description="ID of the product selected by user")
    qty: int = Field(..., gt=0, description="Quantity of the product to order")

class OrderCreate(BaseModel):
    userId: str = Field("user_1", description="User ID placing the order (can be hardcoded)")
    items: List[OrderItemRequest] = Field(..., description="List of items in the order")

class OrderCreateResponse(BaseModel):
    id: Annotated[PyObjectId, BeforeValidator(str)] = Field(alias="_id", description="Unique ID of the created order")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True 
        json_encoders = {ObjectId: str} 


class ProductDetailsInOrder(BaseModel):
    id: Annotated[PyObjectId, BeforeValidator(str)] = Field(alias="_id", description="Product ID from product collection")
    name: str = Field(..., description="Name of the product")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class OrderItemResponse(BaseModel):
    productDetails: ProductDetailsInOrder = Field(..., description="Details of the ordered product")
    qty: int = Field(..., description="Quantity ordered for this product")

class OrderResponse(BaseModel):
    id: Annotated[PyObjectId, BeforeValidator(str)] = Field(alias="_id", description="Order ID")
    items: List[OrderItemResponse] = Field(..., description="List of items in the order with product details")
    total: float = Field(..., description="Total amount of the order")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}    


class OrderListResponse(BaseModel):
    data: List[OrderResponse]
    page: PaginationInfo 