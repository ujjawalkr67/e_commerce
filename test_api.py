import requests
import json

# Base URL - replace with your deployed URL if not local
BASE_URL = "http://localhost:8000"

def test_create_product():
    """Test creating a product"""
    url = f"{BASE_URL}/products"
    data = {
        "name": "Test Hoodie", # Updated product name
        "price": 45.50,
        "sizes": [ # Corrected field name from 'available_sizes' to 'sizes'
            {"size": "S", "quantity": 30},
            {"size": "M", "quantity": 50},
            {"size": "XL", "quantity": 20}
        ]
    }

    response = requests.post(url, json=data)
    print(f"Create Product Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # The product ID is now returned as 'id', not 'product_id'
    return response.json().get("id")

def test_list_products():
    """Test listing products with various filters"""
    url = f"{BASE_URL}/products"

    print("\n--- Listing All Products ---")
    response_all = requests.get(url)
    print(f"List Products (All) Status: {response_all.status_code}")
    print(f"Response (All): {json.dumps(response_all.json(), indent=2)}")

    print("\n--- Listing Products filtered by Name 'Hoodie' ---")
    params_name = {"name": "Hoodie"}
    response_name = requests.get(url, params=params_name)
    print(f"List Products (Name Filter) Status: {response_name.status_code}")
    print(f"Response (Name Filter): {json.dumps(response_name.json(), indent=2)}")

    print("\n--- Listing Products filtered by Size 'M' ---")
    params_size = {"size": "M"}
    response_size = requests.get(url, params=params_size)
    print(f"List Products (Size Filter) Status: {response_size.status_code}")
    print(f"Response (Size Filter): {json.dumps(response_size.json(), indent=2)}")

    print("\n--- Listing Products with Limit 1, Offset 0 ---")
    params_pagination = {"limit": 1, "offset": 0}
    response_pag1 = requests.get(url, params=params_pagination)
    print(f"List Products (Paginated 1) Status: {response_pag1.status_code}")
    print(f"Response (Paginated 1): {json.dumps(response_pag1.json(), indent=2)}")

    print("\n--- Listing Products with Limit 1, Offset 1 ---")
    params_pagination = {"limit": 1, "offset": 1}
    response_pag2 = requests.get(url, params=params_pagination)
    print(f"List Products (Paginated 2) Status: {response_pag2.status_code}")
    print(f"Response (Paginated 2): {json.dumps(response_pag2.json(), indent=2)}")


def test_create_order(product_id_to_order):
    """Test creating an order"""
    url = f"{BASE_URL}/orders"
    data = {
        "userId": "user456", # Corrected field name from 'user_id' to 'userId'
        "items": [
            {
                "productId": product_id_to_order, # Corrected field name from 'product_id' to 'productId'
                "qty": 2 # Corrected field name from 'bought_quantity' to 'qty'
            }
        ]
    }

    response = requests.post(url, json=data)
    print(f"Create Order Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # The order ID is now returned as 'id', not 'order_id'
    return response.json().get("id")

def test_get_user_orders(user_id_to_test):
    """Test getting user orders"""
    url = f"{BASE_URL}/orders/{user_id_to_test}" # Pass user_id as URL parameter

    print(f"\n--- Getting Orders for User: {user_id_to_test} (All) ---")
    response_all = requests.get(url)
    print(f"Get User Orders (All) Status: {response_all.status_code}")
    print(f"Response (All): {json.dumps(response_all.json(), indent=2)}")

    print(f"\n--- Getting Orders for User: {user_id_to_test} (Limit 1, Offset 0) ---")
    params_pagination = {"limit": 1, "offset": 0}
    response_pag1 = requests.get(url, params=params_pagination)
    print(f"Get User Orders (Paginated 1) Status: {response_pag1.status_code}")
    print(f"Response (Paginated 1): {json.dumps(response_pag1.json(), indent=2)}")

    print(f"\n--- Getting Orders for User: {user_id_to_test} (Limit 1, Offset 1) ---")
    params_pagination = {"limit": 1, "offset": 1}
    response_pag2 = requests.get(url, params=params_pagination)
    print(f"Get User Orders (Paginated 2) Status: {response_pag2.status_code}")
    print(f"Response (Paginated 2): {json.dumps(response_pag2.json(), indent=2)}")


if __name__ == "__main__":
    print("Testing FastAPI Ecommerce Backend...\n")

    # --- Test 1: Create a Product ---
    print("="*50)
    print("STEP 1: Testing Create Product API")
    product_id = test_create_product()
    if product_id:
        print(f"Successfully created product with ID: {product_id}")
    else:
        print("Failed to create product or retrieve ID.")
    print("="*50 + "\n")

    # --- Test 2: List Products ---
    print("="*50)
    print("STEP 2: Testing List Products API")
    test_list_products()
    print("="*50 + "\n")

    # --- Test 3: Create an Order ---
    order_user_id = "user456" # User ID to be used for order creation and retrieval
    if product_id:
        print("="*50)
        print("STEP 3: Testing Create Order API")
        order_id = test_create_order(product_id)
        if order_id:
            print(f"Successfully created order with ID: {order_id}")
            # Create another order for the same user to test pagination
            print("\nCreating a second order for the same user...")
            requests.post(f"{BASE_URL}/orders", json={
                "userId": order_user_id,
                "items": [
                    {"productId": product_id, "qty": 1}
                ]
            })
        else:
            print("Failed to create order or retrieve ID.")
        print("="*50 + "\n")

        # --- Test 4: Get User Orders ---
        print("="*50)
        print("STEP 4: Testing Get User Orders API")
        test_get_user_orders(order_user_id)
        print("="*50 + "\n")
    else:
        print("Skipping order creation and user order retrieval as product creation failed.")

    print("All tests completed.")