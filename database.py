"""
Flower Shop Management System - Database Layer
Implements SQLite schema, migrations, seed data, and query helpers.
Based on Software Engineering Project Report Specification.
"""

import sqlite3
import hashlib
import os
from datetime import datetime, timedelta

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flowershop.db")

def hash_password(password: str) -> str:
    """Generate SHA-256 hash for passwords."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_db_connection():
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(force_recreate: bool = False):
    """Creates database tables and loads seed data if needed."""
    if force_recreate and os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
        except Exception:
            pass

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. CUSTOMERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        loyalty_points INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. STAFF (Florists, Delivery Persons, Administrators)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS staff (
        staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL, -- 'Admin', 'Florist', 'Delivery'
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        phone TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. CATEGORIES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT NOT NULL UNIQUE,
        description TEXT,
        image_url TEXT
    )
    """)

    # 4. SUPPLIERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT,
        email TEXT,
        address TEXT
    )
    """)

    # 5. FLOWERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS flowers (
        flower_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        supplier_id INTEGER,
        name TEXT NOT NULL,
        color TEXT,
        occasion TEXT,
        price REAL NOT NULL,
        stock_qty INTEGER NOT NULL DEFAULT 0,
        description TEXT,
        image_url TEXT,
        FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE CASCADE,
        FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id) ON DELETE SET NULL
    )
    """)

    # 6. ORDERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        order_date TEXT NOT NULL,
        delivery_date TEXT,
        delivery_time_slot TEXT,
        delivery_address TEXT NOT NULL,
        recipient_name TEXT,
        recipient_phone TEXT,
        greeting_message TEXT,
        status TEXT NOT NULL DEFAULT 'Order Placed', -- 'Order Placed', 'Payment Confirmed', 'Preparing', 'Ready', 'Out for Delivery', 'Delivered', 'Cancelled'
        subtotal REAL NOT NULL,
        delivery_charge REAL DEFAULT 50.0,
        discount REAL DEFAULT 0.0,
        total_amount REAL NOT NULL,
        payment_status TEXT DEFAULT 'Paid', -- 'Paid', 'Pending', 'Failed'
        payment_method TEXT DEFAULT 'Card',
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE
    )
    """)

    # 7. ORDER_ITEMS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        flower_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE,
        FOREIGN KEY (flower_id) REFERENCES flowers (flower_id) ON DELETE CASCADE
    )
    """)

    # 8. PAYMENTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL UNIQUE,
        method TEXT NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL, -- 'Success', 'Pending', 'Failed'
        paid_on TEXT,
        transaction_ref TEXT,
        FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE
    )
    """)

    # 9. DELIVERIES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deliveries (
        delivery_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL UNIQUE,
        staff_id INTEGER,
        address TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Assigned', -- 'Assigned', 'Out for Delivery', 'Delivered'
        assigned_on TEXT,
        delivered_on TEXT,
        notes TEXT,
        FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE,
        FOREIGN KEY (staff_id) REFERENCES staff (staff_id) ON DELETE SET NULL
    )
    """)

    conn.commit()

    # Check if seed data exists
    cursor.execute("SELECT COUNT(*) as count FROM staff")
    if cursor.fetchone()["count"] == 0:
        seed_database(conn)

    conn.close()

def seed_database(conn):
    """Seed database with initial data matching project specification."""
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Seed Staff & Admin
    staff_data = [
        ("Admin User", "Admin", "admin@flowershop.com", hash_password("admin123"), "+91 98765 43210"),
        ("Sarah Jenkins", "Florist", "florist@flowershop.com", hash_password("staff123"), "+91 98765 43211"),
        ("Alex Kumar", "Delivery", "delivery@flowershop.com", hash_password("delivery123"), "+91 98765 43212"),
        ("John Doe", "Florist", "john@flowershop.com", hash_password("staff123"), "+91 98765 43213")
    ]
    cursor.executemany(
        "INSERT INTO staff (name, role, email, password_hash, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        [(s[0], s[1], s[2], s[3], s[4], now_str) for s in staff_data]
    )

    # 2. Seed Customers (including Ananya from report Example Section 4.3)
    customer_data = [
        ("Ananya Sharma", "ananya@example.com", hash_password("customer123"), "+91 98123 45678", "42 Green Valley Apartments, MG Road, Bangalore", 150),
        ("Rahul Verma", "rahul@example.com", hash_password("customer123"), "+91 98234 56789", "12 Lotus Residency, Indiranagar, Bangalore", 50),
        ("Priya Nair", "priya@example.com", hash_password("customer123"), "+91 98345 67890", "7 Sunrise Villa, Koramangala, Bangalore", 200)
    ]
    cursor.executemany(
        "INSERT INTO customers (name, email, password_hash, phone, address, loyalty_points, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(c[0], c[1], c[2], c[3], c[4], c[5], now_str) for c in customer_data]
    )

    # 3. Seed Suppliers
    suppliers_data = [
        ("Bloomfield Exotic Flora", "+91 98450 11223", "orders@bloomfieldflora.in", "Plot 14, Ooty Hills Estate, Nilgiris"),
        ("Mysore Orchid Farms", "+91 98450 44556", "supply@mysoreorchids.com", "Ring Road Farm 8, Mysore"),
        ("Himalayan Blossom Imports", "+91 98450 77889", "contact@himalayanblossoms.com", "Sector 3, Dehradun"),
        ("Sunrise Flora Wholesalers", "+91 98450 99001", "sales@sunriseflora.com", "Flower Market Yard 4, Bangalore")
    ]
    cursor.executemany(
        "INSERT INTO suppliers (name, contact, email, address) VALUES (?, ?, ?, ?)",
        suppliers_data
    )

    # 4. Seed Categories
    categories_data = [
        ("Roses", "Classic fresh cut roses in premium vibrant shades", "roses"),
        ("Orchids", "Exotic and elegant long-lasting orchids", "orchids"),
        ("Lilies", "Fragrant oriental and Asiatic lilies", "lilies"),
        ("Tulips", "Fresh Holland spring tulips", "tulips"),
        ("Sunflowers", "Bright, uplifting yellow sunflower arrangements", "sunflowers"),
        ("Bouquets & Arrangements", "Artisan mixed bouquets for all special occasions", "bouquets"),
        ("Exotic & Carnations", "Long-lasting cheerful carnations and exotic greens", "carnations")
    ]
    cursor.executemany(
        "INSERT INTO categories (category_name, description, image_url) VALUES (?, ?, ?)",
        categories_data
    )

    # 5. Seed Flowers (Matching report: Red Roses 450, Orchid Bouquet 600, etc.)
    flowers_data = [
        (1, 1, "Classic Red Roses (Bunch of 12)", "Red", "Anniversary / Romance", 450.0, 35, "Twelve velvety long-stem red roses hand-tied with elegant satin ribbon.", "red_roses.jpg"),
        (1, 1, "Velvet Pink Roses (Bunch of 10)", "Pink", "Birthday", 420.0, 20, "Soft pastel pink roses symbolizing grace, gratitude, and joy.", "pink_roses.jpg"),
        (1, 4, "Snow White Roses (Bunch of 10)", "White", "Wedding", 480.0, 15, "Pristine white blooms symbolizing pure love and new beginnings.", "white_roses.jpg"),
        (1, 4, "Sunshine Yellow Roses", "Yellow", "Celebration", 390.0, 25, "Vibrant sunny yellow roses celebrating genuine friendship and positivity.", "yellow_roses.jpg"),
        (2, 2, "Imperial Orchid Bouquet", "Purple", "Anniversary", 600.0, 18, "Exquisite purple dendrobium orchids delicately wrapped in artisanal craft paper.", "purple_orchids.jpg"),
        (2, 2, "Blue Twilight Orchids", "Blue", "Birthday", 650.0, 12, "Striking rare dyed electric blue orchid stems, guaranteed to dazzle.", "blue_orchids.jpg"),
        (3, 3, "Stargazer Oriental Lilies", "Pink", "Celebration", 550.0, 14, "Intensely fragrant multi-bloom pink oriental stargazer lilies.", "pink_lilies.jpg"),
        (3, 3, "Royal White Asiatic Lilies", "White", "Sympathy / Wedding", 520.0, 8, "Elegant pure white lilies with lush foliage, clean and peaceful.", "white_lilies.jpg"),
        (4, 3, "Crimson Holland Tulips", "Red", "Valentine's", 720.0, 10, "Imported fresh Dutch tulips with pristine cupped crimson blooms.", "red_tulips.jpg"),
        (4, 3, "Pastel Sunset Tulips Mix", "Mixed", "Birthday", 750.0, 6, "A delightful assortment of peach, yellow, and pastel pink tulips.", "mixed_tulips.jpg"),
        (5, 1, "Radiant Sunshine Sunflowers", "Yellow", "Celebration", 380.0, 22, "Large cheerful sunflowers hand-arranged with baby's breath and greens.", "sunflowers.jpg"),
        (6, 4, "Pastel Dream Deluxe Bouquet", "Mixed", "Birthday", 850.0, 16, "A luxury mix of baby pink roses, white lilies, carnations, and eucalyptus.", "pastel_dream.jpg"),
        (6, 4, "Romantic Love Symphony", "Red", "Valentine's", 950.0, 15, "24 premium scarlet roses, gypsophila filler, and rich green wrapping.", "love_symphony.jpg"),
        (7, 1, "Coral Carnation Cascade", "Pink", "Mother's Day", 350.0, 5, "Long-lasting ruffled carnations in shades of coral and peach.", "carnations.jpg"),
        (7, 4, "Elegance Gerbera Delight", "Mixed", "Celebration", 400.0, 30, "Colorful, lively gerbera daisies that brighten any room instantly.", "gerberas.jpg")
    ]
    cursor.executemany(
        """INSERT INTO flowers 
           (category_id, supplier_id, name, color, occasion, price, stock_qty, description, image_url) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        flowers_data
    )

    # 6. Seed Sample Orders (Including Order 1001 from Section 4.3 & 14)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
    INSERT INTO orders (
        order_id, customer_id, order_date, delivery_date, delivery_time_slot,
        delivery_address, recipient_name, recipient_phone, greeting_message,
        status, subtotal, delivery_charge, discount, total_amount, payment_status, payment_method
    ) VALUES (
        1001, 1, ?, ?, 'Afternoon (12:00 PM - 04:00 PM)',
        '42 Green Valley Apartments, MG Road, Bangalore', 'Ananya Sharma', '+91 98123 45678',
        'Happy Anniversary to the best partner in the world!',
        'Out for Delivery', 1500.0, 50.0, 100.0, 1450.0, 'Paid', 'Credit/Debit Card'
    )
    """, (yesterday, today))

    cursor.execute("""
    INSERT INTO order_items (order_id, flower_id, quantity, unit_price, subtotal)
    VALUES (1001, 1, 2, 450.0, 900.0)
    """)
    cursor.execute("""
    INSERT INTO order_items (order_id, flower_id, quantity, unit_price, subtotal)
    VALUES (1001, 5, 1, 600.0, 600.0)
    """)

    cursor.execute("""
    INSERT INTO payments (order_id, method, amount, status, paid_on, transaction_ref)
    VALUES (1001, 'Credit/Debit Card', 1450.0, 'Success', ?, 'TXN-FLW-1001-9874')
    """, (yesterday,))

    cursor.execute("""
    INSERT INTO deliveries (order_id, staff_id, address, status, assigned_on, notes)
    VALUES (1001, 3, '42 Green Valley Apartments, MG Road, Bangalore', 'Out for Delivery', ?, 'Handle with care. Fresh flowers with water vials.')
    """, (yesterday,))

    # Seed order 1002
    cursor.execute("""
    INSERT INTO orders (
        order_id, customer_id, order_date, delivery_date, delivery_time_slot,
        delivery_address, recipient_name, recipient_phone, greeting_message,
        status, subtotal, delivery_charge, discount, total_amount, payment_status, payment_method
    ) VALUES (
        1002, 2, ?, ?, 'Evening (04:00 PM - 08:00 PM)',
        '12 Lotus Residency, Indiranagar, Bangalore', 'Sneha Verma', '+91 98234 56789',
        'Wishing you a super wonderful birthday!',
        'Preparing', 850.0, 50.0, 0.0, 900.0, 'Paid', 'UPI / QR'
    )
    """, (now_str, today))

    cursor.execute("""
    INSERT INTO order_items (order_id, flower_id, quantity, unit_price, subtotal)
    VALUES (1002, 12, 1, 850.0, 850.0)
    """)

    cursor.execute("""
    INSERT INTO payments (order_id, method, amount, status, paid_on, transaction_ref)
    VALUES (1002, 'UPI / QR', 900.0, 'Success', ?, 'UPI-FLW-1002-8321')
    """, (now_str,))

    cursor.execute("""
    INSERT INTO deliveries (order_id, staff_id, address, status, assigned_on, notes)
    VALUES (1002, 3, '12 Lotus Residency, Indiranagar, Bangalore', 'Assigned', ?, 'Please ring the bell.')
    """, (now_str,))

    conn.commit()

if __name__ == "__main__":
    init_db(force_recreate=True)
    print("Database initialized and seeded successfully.")
