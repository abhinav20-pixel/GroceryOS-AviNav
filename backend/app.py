from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import database

app = FastAPI(title="Grocery Store Management System API")

# Setup CORS to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    database.init_db()

# --- Pydantic Models ---
class ProductBase(BaseModel):
    name: str
    category: str
    price: float
    quantity: int
    supplier: Optional[str] = None
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int

class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class Customer(CustomerBase):
    id: int
    total_purchases: float

class OrderItemInput(BaseModel):
    product_id: int
    quantity: int
    price: float

class OrderCreate(BaseModel):
    customer_id: Optional[int] = None
    items: List[OrderItemInput]
    tax: float
    discount: float = 0.0

# --- Dashboard & Analytics Routes ---
@app.get("/api/dashboard")
def get_dashboard_stats():
    conn = database.get_db_connection()
    c = conn.cursor()
    
    # Total Orders
    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]
    
    # Total Customers
    c.execute("SELECT COUNT(*) FROM customers")
    total_customers = c.fetchone()[0]
    
    # Total Products
    c.execute("SELECT COUNT(*) FROM products")
    total_products = c.fetchone()[0]
    
    # Total Revenue
    c.execute("SELECT SUM(grand_total) FROM orders")
    total_revenue = c.fetchone()[0] or 0.0
    
    # Low stock alerts (qty < 10)
    c.execute("SELECT COUNT(*) FROM products WHERE quantity < 10")
    low_stock = c.fetchone()[0]
    
    conn.close()
    
    return {
        "total_orders": total_orders,
        "total_customers": total_customers,
        "total_products": total_products,
        "total_revenue": total_revenue,
        "low_stock_alerts": low_stock
    }

# --- Product Routes ---
@app.get("/api/products")
def get_products(search: str = None):
    conn = database.get_db_connection()
    c = conn.cursor()
    if search:
        c.execute("SELECT * FROM products WHERE name LIKE ?", ('%' + search + '%',))
    else:
        c.execute("SELECT * FROM products")
    products = [dict(row) for row in c.fetchall()]
    conn.close()
    return products

@app.post("/api/products", status_code=201)
def create_product(product: ProductCreate):
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO products (name, category, price, quantity, supplier, image_url)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (product.name, product.category, product.price, product.quantity, product.supplier, product.image_url))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return {"id": new_id, "message": "Product created successfully"}

@app.put("/api/products/{product_id}")
def update_product(product_id: int, product: ProductCreate):
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE products
        SET name=?, category=?, price=?, quantity=?, supplier=?, image_url=?
        WHERE id=?
    ''', (product.name, product.category, product.price, product.quantity, product.supplier, product.image_url, product_id))
    conn.commit()
    if c.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    conn.close()
    return {"message": "Product updated successfully"}

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int):
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    if c.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    conn.close()
    return {"message": "Product deleted successfully"}

# --- Customer Routes ---
@app.get("/api/customers")
def get_customers():
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM customers")
    customers = [dict(row) for row in c.fetchall()]
    conn.close()
    return customers

@app.post("/api/customers", status_code=201)
def create_customer(customer: CustomerCreate):
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO customers (name, phone, email, address)
        VALUES (?, ?, ?, ?)
    ''', (customer.name, customer.phone, customer.email, customer.address))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return {"id": new_id, "message": "Customer created successfully"}

# --- Order Routes ---
@app.post("/api/orders", status_code=201)
def create_order(order: OrderCreate):
    conn = database.get_db_connection()
    c = conn.cursor()
    
    try:
        # Calculate totals securely on backend
        total_amount = sum(item.quantity * item.price for item in order.items)
        grand_total = total_amount + order.tax - order.discount
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Insert Order
        c.execute('''
            INSERT INTO orders (customer_id, total_amount, tax, discount, grand_total, date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (order.customer_id, total_amount, order.tax, order.discount, grand_total, date_str))
        order_id = c.lastrowid
        
        # 2. Insert Order Items & Update Stock
        for item in order.items:
            c.execute('''
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
            ''', (order_id, item.product_id, item.quantity, item.price))
            
            # Decrease product quantity
            c.execute("UPDATE products SET quantity = quantity - ? WHERE id = ?", (item.quantity, item.product_id))
            
        # 3. Insert Invoice
        c.execute("INSERT INTO invoices (order_id, date) VALUES (?, ?)", (order_id, date_str))
        
        # 4. Update Customer Total Purchases
        if order.customer_id:
            c.execute("UPDATE customers SET total_purchases = total_purchases + ? WHERE id = ?", (grand_total, order.customer_id))
            
        conn.commit()
        return {"id": order_id, "message": "Order placed successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.get("/api/orders")
def get_orders():
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT o.id, o.total_amount, o.grand_total, o.date, c.name as customer_name 
        FROM orders o 
        LEFT JOIN customers c ON o.customer_id = c.id
        ORDER BY o.date DESC
    ''')
    orders = [dict(row) for row in c.fetchall()]
    conn.close()
    return orders

@app.get("/api/invoices")
def get_invoices():
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT i.id as invoice_id, o.id as order_id, i.date, i.status, o.grand_total, c.name as customer_name
        FROM invoices i
        JOIN orders o ON i.order_id = o.id
        LEFT JOIN customers c ON o.customer_id = c.id
        ORDER BY i.date DESC
    ''')
    invoices = [dict(row) for row in c.fetchall()]
    conn.close()
    return invoices

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
