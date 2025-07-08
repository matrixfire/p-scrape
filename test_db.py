from mysqll3 import MySQLHandler, ProductService, DB_CONFIG

# Step 1: Create DB handler
db = MySQLHandler(DB_CONFIG)

# Step 2: Create service instance
service = ProductService(db)

# Step 3: Prepare some test data
test_product = {
    "sku": "ABC123",
    "id": 1001,
    "default_product_name_en": "Test Widget",
    "main_img": "https://example.com/test.jpg",
    "weight": 2.5
}

test_stock = {
    "sku": "ABC123",
    "id": 1001,
    "stock": 50,
    "price": 9.99,
    "status": "active"
}

# Step 4: Use the service methods
# service.insert_product(test_product)
# service.insert_stock(test_stock)
# service.update_stock({"sku": "ABC123", "price": 8.99, "stock": 55})
products = service.query_products()
print(products)

stock = service.query_stock()
print(stock)

# Step 5: Close DB connection
db.close()
