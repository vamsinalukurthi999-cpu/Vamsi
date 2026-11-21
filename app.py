"""
Flower Shop Management System - Web Server and REST API
Built using Python Standard Library ThreadingHTTPServer & SQLite.
Zero external dependencies required.
"""

import sys
import os
import json
import sqlite3
import mimetypes
import uuid
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from database import get_db_connection, init_db, hash_password, DB_FILE

# Global in-memory active sessions: token -> user dict
SESSIONS = {}

def get_current_user(token: str):
    """Retrieve user from active sessions."""
    if not token:
        return None
    return SESSIONS.get(token)

def row_to_dict(row):
    """Convert sqlite3.Row to standard Python dictionary."""
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}

def rows_to_list(rows):
    """Convert list of sqlite3.Row to list of dicts."""
    return [row_to_dict(r) for r in rows]

class FlowerShopAPIHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for Flower Shop REST API & Static Frontend."""

    def send_json(self, data, status_code=200):
        """Send JSON response with CORS headers."""
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message, status_code=400):
        """Send formatted error JSON."""
        self.send_json({"error": message, "success": False}, status_code=status_code)

    def do_OPTIONS(self):
        """Handle pre-flight CORS requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def get_auth_token(self):
        """Extract token from Authorization header or cookie."""
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        cookie_header = self.headers.get("Cookie", "")
        for item in cookie_header.split(";"):
            item = item.strip()
            if item.startswith("token="):
                return item[6:].strip()
        return None

    def read_json_body(self):
        """Reads and parses incoming JSON payload."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                return {}
            raw_data = self.rfile.read(content_length).decode("utf-8")
            return json.loads(raw_data) if raw_data else {}
        except Exception as e:
            return None

    # ==================== ROUTE DISPATCHERS ====================

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Static assets
        if not path.startswith("/api/"):
            self.serve_static_file(path)
            return

        token = self.get_auth_token()
        user = get_current_user(token)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # --- AUTH: Current User ---
            if path == "/api/auth/me":
                if user:
                    self.send_json({"success": True, "user": user})
                else:
                    self.send_json({"success": False, "user": None})

            # --- CATEGORIES ---
            elif path == "/api/categories":
                cursor.execute("""
                    SELECT c.*, COUNT(f.flower_id) as flower_count 
                    FROM categories c 
                    LEFT JOIN flowers f ON c.category_id = f.category_id 
                    GROUP BY c.category_id
                    ORDER BY c.category_name ASC
                """)
                self.send_json({"success": True, "categories": rows_to_list(cursor.fetchall())})

            # --- FLOWERS (CATALOG) ---
            elif path == "/api/flowers":
                sql = """
                    SELECT f.*, c.category_name, s.name as supplier_name 
                    FROM flowers f 
                    JOIN categories c ON f.category_id = c.category_id 
                    LEFT JOIN suppliers s ON f.supplier_id = s.supplier_id 
                    WHERE 1=1
                """
                params = []

                if "category" in query and query["category"][0]:
                    cat = query["category"][0]
                    if cat.isdigit():
                        sql += " AND f.category_id = ?"
                        params.append(int(cat))
                    else:
                        sql += " AND c.category_name = ?"
                        params.append(cat)

                if "color" in query and query["color"][0]:
                    sql += " AND LOWER(f.color) = LOWER(?)"
                    params.append(query["color"][0])

                if "occasion" in query and query["occasion"][0]:
                    sql += " AND f.occasion LIKE ?"
                    params.append(f"%{query['occasion'][0]}%")

                if "search" in query and query["search"][0]:
                    q = query["search"][0]
                    sql += " AND (f.name LIKE ? OR f.description LIKE ? OR c.category_name LIKE ?)"
                    params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

                if "min_price" in query and query["min_price"][0]:
                    try:
                        sql += " AND f.price >= ?"
                        params.append(float(query["min_price"][0]))
                    except ValueError:
                        pass

                if "max_price" in query and query["max_price"][0]:
                    try:
                        sql += " AND f.price <= ?"
                        params.append(float(query["max_price"][0]))
                    except ValueError:
                        pass

                if "in_stock" in query and query["in_stock"][0] == "1":
                    sql += " AND f.stock_qty > 0"

                sort = query.get("sort", ["name_asc"])[0]
                if sort == "price_asc":
                    sql += " ORDER BY f.price ASC"
                elif sort == "price_desc":
                    sql += " ORDER BY f.price DESC"
                elif sort == "stock_asc":
                    sql += " ORDER BY f.stock_qty ASC"
                else:
                    sql += " ORDER BY f.name ASC"

                cursor.execute(sql, params)
                self.send_json({"success": True, "flowers": rows_to_list(cursor.fetchall())})

            # --- SINGLE FLOWER ---
            elif re.match(r"^/api/flowers/(\d+)$", path):
                flower_id = int(re.match(r"^/api/flowers/(\d+)$", path).group(1))
                cursor.execute("""
                    SELECT f.*, c.category_name, s.name as supplier_name 
                    FROM flowers f 
                    JOIN categories c ON f.category_id = c.category_id 
                    LEFT JOIN suppliers s ON f.supplier_id = s.supplier_id 
                    WHERE f.flower_id = ?
                """, (flower_id,))
                flower = cursor.fetchone()
                if flower:
                    self.send_json({"success": True, "flower": row_to_dict(flower)})
                else:
                    self.send_error_json("Flower not found", 404)

            # --- ORDERS LIST ---
            elif path == "/api/orders":
                if not user:
                    self.send_error_json("Authentication required to view orders", 401)
                    conn.close()
                    return

                role = user.get("role")
                if role == "Customer":
                    cursor.execute("""
                        SELECT o.*, c.name as customer_name, c.email as customer_email,
                               d.status as delivery_status, s.name as delivery_person_name
                        FROM orders o
                        JOIN customers c ON o.customer_id = c.customer_id
                        LEFT JOIN deliveries d ON o.order_id = d.order_id
                        LEFT JOIN staff s ON d.staff_id = s.staff_id
                        WHERE o.customer_id = ?
                        ORDER BY o.order_id DESC
                    """, (user["id"],))
                elif role == "Delivery":
                    cursor.execute("""
                        SELECT o.*, c.name as customer_name, c.phone as customer_phone, c.email as customer_email,
                               d.delivery_id, d.status as delivery_status, d.notes as delivery_notes,
                               d.assigned_on, d.delivered_on, s.name as delivery_person_name
                        FROM orders o
                        JOIN customers c ON o.customer_id = c.customer_id
                        JOIN deliveries d ON o.order_id = d.order_id
                        LEFT JOIN staff s ON d.staff_id = s.staff_id
                        WHERE d.staff_id = ? OR d.staff_id IS NULL
                        ORDER BY o.order_id DESC
                    """, (user["id"],))
                else:
                    cursor.execute("""
                        SELECT o.*, c.name as customer_name, c.phone as customer_phone, c.email as customer_email,
                               d.delivery_id, d.status as delivery_status, d.staff_id as delivery_staff_id,
                               s.name as delivery_person_name
                        FROM orders o
                        JOIN customers c ON o.customer_id = c.customer_id
                        LEFT JOIN deliveries d ON o.order_id = d.order_id
                        LEFT JOIN staff s ON d.staff_id = s.staff_id
                        ORDER BY o.order_id DESC
                    """)

                orders = rows_to_list(cursor.fetchall())

                for order in orders:
                    cursor.execute("""
                        SELECT oi.*, f.name as flower_name, f.image_url, f.color
                        FROM order_items oi
                        JOIN flowers f ON oi.flower_id = f.flower_id
                        WHERE oi.order_id = ?
                    """, (order["order_id"],))
                    order["items"] = rows_to_list(cursor.fetchall())

                self.send_json({"success": True, "orders": orders})

            # --- SINGLE ORDER & INVOICE ---
            elif re.match(r"^/api/orders/(\d+)$", path) or re.match(r"^/api/orders/(\d+)/invoice$", path):
                match = re.match(r"^/api/orders/(\d+)", path)
                order_id = int(match.group(1))

                cursor.execute("""
                    SELECT o.*, c.name as customer_name, c.phone as customer_phone, c.email as customer_email,
                           c.address as customer_saved_address,
                           p.method as payment_method_used, p.status as payment_record_status,
                           p.transaction_ref, p.paid_on,
                           d.delivery_id, d.status as delivery_status, d.assigned_on, d.delivered_on, d.notes as delivery_notes,
                           s.name as delivery_person_name, s.phone as delivery_person_phone
                    FROM orders o
                    JOIN customers c ON o.customer_id = c.customer_id
                    LEFT JOIN payments p ON o.order_id = p.order_id
                    LEFT JOIN deliveries d ON o.order_id = d.order_id
                    LEFT JOIN staff s ON d.staff_id = s.staff_id
                    WHERE o.order_id = ?
                """, (order_id,))
                order = cursor.fetchone()

                if not order:
                    self.send_error_json("Order not found", 404)
                    conn.close()
                    return

                order_dict = row_to_dict(order)

                cursor.execute("""
                    SELECT oi.*, f.name as flower_name, f.color, f.image_url
                    FROM order_items oi
                    JOIN flowers f ON oi.flower_id = f.flower_id
                    WHERE oi.order_id = ?
                """, (order_id,))
                order_dict["items"] = rows_to_list(cursor.fetchall())

                self.send_json({"success": True, "order": order_dict})

            # --- SUPPLIERS ---
            elif path == "/api/suppliers":
                cursor.execute("SELECT * FROM suppliers ORDER BY name ASC")
                self.send_json({"success": True, "suppliers": rows_to_list(cursor.fetchall())})

            # --- STAFF ---
            elif path == "/api/staff":
                cursor.execute("SELECT staff_id, name, role, email, phone, created_at FROM staff ORDER BY role, name")
                self.send_json({"success": True, "staff": rows_to_list(cursor.fetchall())})

            # --- CUSTOMERS (Admin) ---
            elif path == "/api/customers":
                cursor.execute("""
                    SELECT c.customer_id, c.name, c.email, c.phone, c.address, c.loyalty_points, c.created_at,
                           COUNT(o.order_id) as total_orders,
                           COALESCE(SUM(o.total_amount), 0) as total_spent
                    FROM customers c
                    LEFT JOIN orders o ON c.customer_id = o.customer_id
                    GROUP BY c.customer_id
                    ORDER BY c.name ASC
                """)
                self.send_json({"success": True, "customers": rows_to_list(cursor.fetchall())})

            # --- REPORTS & ANALYTICS ---
            elif path == "/api/reports/dashboard":
                cursor.execute("SELECT COALESCE(SUM(total_amount), 0) as total_revenue, COUNT(*) as total_orders FROM orders WHERE status != 'Cancelled'")
                revenue_row = cursor.fetchone()

                cursor.execute("SELECT COUNT(*) as pending_count FROM orders WHERE status IN ('Order Placed', 'Payment Confirmed', 'Preparing', 'Ready')")
                pending_count = cursor.fetchone()["pending_count"]

                cursor.execute("""
                    SELECT f.flower_id, f.name, f.stock_qty, f.price, c.category_name 
                    FROM flowers f 
                    JOIN categories c ON f.category_id = c.category_id 
                    WHERE f.stock_qty < 10 
                    ORDER BY f.stock_qty ASC
                """)
                low_stock_items = rows_to_list(cursor.fetchall())

                cursor.execute("SELECT COUNT(*) as count FROM customers")
                customer_count = cursor.fetchone()["count"]

                cursor.execute("SELECT COUNT(*) as count FROM staff")
                staff_count = cursor.fetchone()["count"]

                cursor.execute("""
                    SELECT c.category_name, SUM(oi.subtotal) as total_sales, SUM(oi.quantity) as items_sold
                    FROM order_items oi
                    JOIN flowers f ON oi.flower_id = f.flower_id
                    JOIN categories c ON f.category_id = c.category_id
                    JOIN orders o ON oi.order_id = o.order_id
                    WHERE o.status != 'Cancelled'
                    GROUP BY c.category_id
                    ORDER BY total_sales DESC
                """)
                category_sales = rows_to_list(cursor.fetchall())

                cursor.execute("SELECT status, COUNT(*) as count FROM orders GROUP BY status")
                status_breakdown = rows_to_list(cursor.fetchall())

                cursor.execute("""
                    SELECT o.order_id, o.order_date, o.total_amount, o.status, c.name as customer_name
                    FROM orders o
                    JOIN customers c ON o.customer_id = c.customer_id
                    ORDER BY o.order_id DESC
                    LIMIT 5
                """)
                recent_orders = rows_to_list(cursor.fetchall())

                self.send_json({
                    "success": True,
                    "metrics": {
                        "total_revenue": revenue_row["total_revenue"],
                        "total_orders": revenue_row["total_orders"],
                        "pending_orders": pending_count,
                        "low_stock_count": len(low_stock_items),
                        "total_customers": customer_count,
                        "total_staff": staff_count
                    },
                    "low_stock_items": low_stock_items,
                    "category_sales": category_sales,
                    "status_breakdown": status_breakdown,
                    "recent_orders": recent_orders
                })

            else:
                self.send_error_json("API endpoint not found", 404)

            conn.close()
        except Exception as e:
            self.send_error_json(f"Server exception: {str(e)}", 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.read_json_body()

        if body is None:
            self.send_error_json("Invalid JSON body in request", 400)
            return

        token = self.get_auth_token()
        user = get_current_user(token)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # --- AUTH: LOGIN ---
            if path == "/api/auth/login":
                email = body.get("email", "").strip().lower()
                password = body.get("password", "")
                selected_role = body.get("role", "")

                if not email or not password:
                    self.send_error_json("Email and password are required")
                    conn.close()
                    return

                pwd_hash = hash_password(password)

                user_found = None
                if selected_role in ["Admin", "Florist", "Delivery", "Staff", ""]:
                    cursor.execute("SELECT * FROM staff WHERE LOWER(email) = ? AND password_hash = ?", (email, pwd_hash))
                    staff_row = cursor.fetchone()
                    if staff_row:
                        user_found = {
                            "id": staff_row["staff_id"],
                            "name": staff_row["name"],
                            "email": staff_row["email"],
                            "role": staff_row["role"],
                            "phone": staff_row["phone"],
                            "is_staff": True
                        }

                if not user_found and (selected_role in ["Customer", ""] or not selected_role):
                    cursor.execute("SELECT * FROM customers WHERE LOWER(email) = ? AND password_hash = ?", (email, pwd_hash))
                    cust_row = cursor.fetchone()
                    if cust_row:
                        user_found = {
                            "id": cust_row["customer_id"],
                            "name": cust_row["name"],
                            "email": cust_row["email"],
                            "role": "Customer",
                            "phone": cust_row["phone"],
                            "address": cust_row["address"],
                            "loyalty_points": cust_row["loyalty_points"],
                            "is_staff": False
                        }

                if not user_found:
                    self.send_error_json("Invalid email or password", 401)
                    conn.close()
                    return

                new_token = str(uuid.uuid4())
                SESSIONS[new_token] = user_found

                self.send_json({
                    "success": True,
                    "message": "Login successful",
                    "token": new_token,
                    "user": user_found
                })

            # --- AUTH: REGISTER CUSTOMER ---
            elif path == "/api/auth/register":
                name = body.get("name", "").strip()
                email = body.get("email", "").strip().lower()
                password = body.get("password", "")
                phone = body.get("phone", "").strip()
                address = body.get("address", "").strip()

                if not name or not email or not password:
                    self.send_error_json("Name, email and password are required")
                    conn.close()
                    return

                cursor.execute("SELECT customer_id FROM customers WHERE LOWER(email) = ?", (email,))
                if cursor.fetchone():
                    self.send_error_json("Email already registered. Please log in.")
                    conn.close()
                    return

                pwd_hash = hash_password(password)
                cursor.execute("""
                    INSERT INTO customers (name, email, password_hash, phone, address, loyalty_points)
                    VALUES (?, ?, ?, ?, ?, 100)
                """, (name, email, pwd_hash, phone, address))
                conn.commit()
                cust_id = cursor.lastrowid

                new_user = {
                    "id": cust_id,
                    "name": name,
                    "email": email,
                    "role": "Customer",
                    "phone": phone,
                    "address": address,
                    "loyalty_points": 100,
                    "is_staff": False
                }
                new_token = str(uuid.uuid4())
                SESSIONS[new_token] = new_user

                self.send_json({
                    "success": True,
                    "message": "Account created successfully with 100 welcome loyalty points!",
                    "token": new_token,
                    "user": new_user
                })

            # --- AUTH: LOGOUT ---
            elif path == "/api/auth/logout":
                if token and token in SESSIONS:
                    del SESSIONS[token]
                self.send_json({"success": True, "message": "Logged out successfully"})

            # --- CREATE ORDER (Customer / Checkout) ---
            elif path == "/api/orders":
                if not user:
                    self.send_error_json("Please login or register to place an order", 401)
                    conn.close()
                    return

                items = body.get("items", [])
                if not items:
                    self.send_error_json("Your cart is empty. Add flowers before checkout.")
                    conn.close()
                    return

                delivery_address = body.get("delivery_address", "").strip()
                delivery_date = body.get("delivery_date", datetime.now().strftime("%Y-%m-%d"))
                delivery_time_slot = body.get("delivery_time_slot", "Morning (09:00 AM - 12:00 PM)")
                recipient_name = body.get("recipient_name", user.get("name", "Customer")).strip()
                recipient_phone = body.get("recipient_phone", user.get("phone", "")).strip()
                greeting_message = body.get("greeting_message", "").strip()
                payment_method = body.get("payment_method", "Credit/Debit Card")
                coupon_code = body.get("coupon_code", "").strip().upper()

                if not delivery_address:
                    self.send_error_json("Delivery address is required.")
                    conn.close()
                    return

                subtotal = 0.0
                validated_items = []
                for item in items:
                    f_id = item.get("flower_id")
                    qty = int(item.get("quantity", 1))
                    if qty <= 0:
                        continue

                    cursor.execute("SELECT flower_id, name, price, stock_qty FROM flowers WHERE flower_id = ?", (f_id,))
                    flower = cursor.fetchone()
                    if not flower:
                        self.send_error_json(f"Flower with ID {f_id} not found in catalog")
                        conn.close()
                        return

                    if flower["stock_qty"] < qty:
                        self.send_error_json(f"Out of stock: '{flower['name']}' only has {flower['stock_qty']} in stock, but {qty} requested.")
                        conn.close()
                        return

                    item_subtotal = flower["price"] * qty
                    subtotal += item_subtotal
                    validated_items.append({
                        "flower_id": flower["flower_id"],
                        "name": flower["name"],
                        "unit_price": flower["price"],
                        "quantity": qty,
                        "subtotal": item_subtotal
                    })

                if not validated_items:
                    self.send_error_json("No valid items in cart")
                    conn.close()
                    return

                delivery_charge = 50.0

                discount = 0.0
                if coupon_code == "FLOWER100":
                    discount = 100.0
                elif coupon_code == "WELCOME20":
                    discount = round(subtotal * 0.20, 2)
                elif coupon_code == "FREESHIP":
                    discount = 50.0

                total_amount = max(0.0, subtotal + delivery_charge - discount)
                order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute("""
                    INSERT INTO orders (
                        customer_id, order_date, delivery_date, delivery_time_slot,
                        delivery_address, recipient_name, recipient_phone, greeting_message,
                        status, subtotal, delivery_charge, discount, total_amount,
                        payment_status, payment_method
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user["id"], order_date, delivery_date, delivery_time_slot,
                    delivery_address, recipient_name, recipient_phone, greeting_message,
                    "Order Placed", subtotal, delivery_charge, discount, total_amount,
                    "Paid" if payment_method != "Cash on Delivery" else "Pending", payment_method
                ))
                order_id = cursor.lastrowid

                for vi in validated_items:
                    cursor.execute("""
                        INSERT INTO order_items (order_id, flower_id, quantity, unit_price, subtotal)
                        VALUES (?, ?, ?, ?, ?)
                    """, (order_id, vi["flower_id"], vi["quantity"], vi["unit_price"], vi["subtotal"]))

                    cursor.execute("""
                        UPDATE flowers SET stock_qty = stock_qty - ? WHERE flower_id = ?
                    """, (vi["quantity"], vi["flower_id"]))

                txn_ref = f"TXN-FLW-{order_id}-{int(datetime.now().timestamp()) % 10000}"
                cursor.execute("""
                    INSERT INTO payments (order_id, method, amount, status, paid_on, transaction_ref)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    order_id, payment_method, total_amount,
                    "Success" if payment_method != "Cash on Delivery" else "Pending",
                    order_date, txn_ref
                ))

                cursor.execute("SELECT staff_id FROM staff WHERE role = 'Delivery' LIMIT 1")
                deliv_staff = cursor.fetchone()
                assigned_staff_id = deliv_staff["staff_id"] if deliv_staff else None

                cursor.execute("""
                    INSERT INTO deliveries (order_id, staff_id, address, status, assigned_on, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (order_id, assigned_staff_id, delivery_address, "Assigned", order_date, "Standard delivery"))

                points_earned = int(total_amount // 20)
                if points_earned > 0 and user.get("role") == "Customer":
                    cursor.execute("UPDATE customers SET loyalty_points = loyalty_points + ? WHERE customer_id = ?", (points_earned, user["id"]))

                conn.commit()

                self.send_json({
                    "success": True,
                    "message": "Order placed successfully! Fresh flowers are being prepared.",
                    "order_id": order_id,
                    "invoice_url": f"/api/orders/{order_id}/invoice",
                    "total_amount": total_amount,
                    "points_earned": points_earned
                })

            # --- ADD FLOWER (Admin / Florist) ---
            elif path == "/api/flowers":
                if not user or user.get("role") not in ["Admin", "Florist"]:
                    self.send_error_json("Admin or Florist privilege required to add flowers", 403)
                    conn.close()
                    return

                name = body.get("name", "").strip()
                category_id = int(body.get("category_id", 1))
                supplier_id = int(body.get("supplier_id", 1)) if body.get("supplier_id") else None
                color = body.get("color", "Red")
                occasion = body.get("occasion", "All Occasions")
                price = float(body.get("price", 100))
                stock_qty = int(body.get("stock_qty", 10))
                description = body.get("description", "")
                image_url = body.get("image_url", "default_flower.jpg")

                cursor.execute("""
                    INSERT INTO flowers (category_id, supplier_id, name, color, occasion, price, stock_qty, description, image_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (category_id, supplier_id, name, color, occasion, price, stock_qty, description, image_url))
                conn.commit()
                new_id = cursor.lastrowid

                self.send_json({
                    "success": True,
                    "message": f"Flower '{name}' added to catalog successfully.",
                    "flower_id": new_id
                })

            # --- ADD CATEGORY (Admin) ---
            elif path == "/api/categories":
                if not user or user.get("role") != "Admin":
                    self.send_error_json("Admin privilege required", 403)
                    conn.close()
                    return

                name = body.get("category_name", "").strip()
                description = body.get("description", "")
                image_url = body.get("image_url", "category.jpg")

                cursor.execute("INSERT INTO categories (category_name, description, image_url) VALUES (?, ?, ?)", (name, description, image_url))
                conn.commit()
                self.send_json({"success": True, "message": "Category added successfully", "category_id": cursor.lastrowid})

            # --- ADD SUPPLIER (Admin) ---
            elif path == "/api/suppliers":
                if not user or user.get("role") != "Admin":
                    self.send_error_json("Admin privilege required", 403)
                    conn.close()
                    return

                name = body.get("name", "").strip()
                contact = body.get("contact", "")
                email = body.get("email", "")
                address = body.get("address", "")

                cursor.execute("INSERT INTO suppliers (name, contact, email, address) VALUES (?, ?, ?, ?)", (name, contact, email, address))
                conn.commit()
                self.send_json({"success": True, "message": "Supplier registered successfully", "supplier_id": cursor.lastrowid})

            # --- ADD STAFF (Admin) ---
            elif path == "/api/staff":
                if not user or user.get("role") != "Admin":
                    self.send_error_json("Admin privilege required to add staff", 403)
                    conn.close()
                    return

                name = body.get("name", "").strip()
                role = body.get("role", "Florist")
                email = body.get("email", "").strip().lower()
                password = body.get("password", "staff123")
                phone = body.get("phone", "")

                cursor.execute("SELECT staff_id FROM staff WHERE LOWER(email) = ?", (email,))
                if cursor.fetchone():
                    self.send_error_json("Staff email already exists")
                    conn.close()
                    return

                cursor.execute("""
                    INSERT INTO staff (name, role, email, password_hash, phone)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, role, email, hash_password(password), phone))
                conn.commit()
                self.send_json({"success": True, "message": f"Staff member {name} ({role}) added successfully", "staff_id": cursor.lastrowid})

            # --- ASSIGN DELIVERY (Florist / Admin) ---
            elif re.match(r"^/api/orders/(\d+)/assign-delivery$", path):
                if not user or user.get("role") not in ["Admin", "Florist"]:
                    self.send_error_json("Permission denied", 403)
                    conn.close()
                    return

                order_id = int(re.match(r"^/api/orders/(\d+)/assign-delivery$", path).group(1))
                staff_id = int(body.get("staff_id"))
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute("""
                    UPDATE deliveries SET staff_id = ?, assigned_on = ? WHERE order_id = ?
                """, (staff_id, now_str, order_id))
                conn.commit()
                self.send_json({"success": True, "message": "Delivery person assigned successfully"})

            else:
                self.send_error_json("Endpoint not found", 404)

            conn.close()
        except Exception as e:
            self.send_error_json(f"Server exception: {str(e)}", 500)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.read_json_body()

        token = self.get_auth_token()
        user = get_current_user(token)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # --- UPDATE ORDER STATUS ---
            if re.match(r"^/api/orders/(\d+)/status$", path):
                if not user:
                    self.send_error_json("Authentication required", 401)
                    conn.close()
                    return

                order_id = int(re.match(r"^/api/orders/(\d+)/status$", path).group(1))
                new_status = body.get("status")
                valid_statuses = ['Order Placed', 'Payment Confirmed', 'Preparing', 'Ready', 'Out for Delivery', 'Delivered', 'Cancelled']

                if new_status not in valid_statuses:
                    self.send_error_json(f"Invalid status '{new_status}'")
                    conn.close()
                    return

                if user.get("role") == "Delivery" and new_status not in ["Out for Delivery", "Delivered"]:
                    self.send_error_json("Delivery personnel can only mark Out for Delivery or Delivered", 403)
                    conn.close()
                    return

                cursor.execute("SELECT status FROM orders WHERE order_id = ?", (order_id,))
                current_order = cursor.fetchone()
                if not current_order:
                    self.send_error_json("Order not found", 404)
                    conn.close()
                    return

                if new_status == "Cancelled" and current_order["status"] != "Cancelled":
                    cursor.execute("SELECT flower_id, quantity FROM order_items WHERE order_id = ?", (order_id,))
                    items = cursor.fetchall()
                    for item in items:
                        cursor.execute("UPDATE flowers SET stock_qty = stock_qty + ? WHERE flower_id = ?", (item["quantity"], item["flower_id"]))

                cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", (new_status, order_id))

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if new_status == "Delivered":
                    cursor.execute("UPDATE deliveries SET status = 'Delivered', delivered_on = ? WHERE order_id = ?", (now_str, order_id))
                    cursor.execute("UPDATE orders SET payment_status = 'Paid' WHERE order_id = ?", (order_id,))
                    cursor.execute("UPDATE payments SET status = 'Success', paid_on = ? WHERE order_id = ?", (now_str, order_id))
                elif new_status == "Out for Delivery":
                    cursor.execute("UPDATE deliveries SET status = 'Out for Delivery' WHERE order_id = ?", (order_id,))

                conn.commit()
                self.send_json({
                    "success": True,
                    "message": f"Order #{order_id} status updated to '{new_status}'",
                    "order_id": order_id,
                    "new_status": new_status
                })

            # --- UPDATE FLOWER / RESTOCK ---
            elif re.match(r"^/api/flowers/(\d+)$", path):
                if not user or user.get("role") not in ["Admin", "Florist"]:
                    self.send_error_json("Admin or Florist privilege required", 403)
                    conn.close()
                    return

                flower_id = int(re.match(r"^/api/flowers/(\d+)$", path).group(1))

                fields = []
                values = []
                for key in ["name", "category_id", "supplier_id", "color", "occasion", "price", "stock_qty", "description", "image_url"]:
                    if key in body:
                        fields.append(f"{key} = ?")
                        values.append(body[key])

                if not fields:
                    self.send_error_json("No fields to update")
                    conn.close()
                    return

                values.append(flower_id)
                sql = f"UPDATE flowers SET {', '.join(fields)} WHERE flower_id = ?"
                cursor.execute(sql, values)
                conn.commit()

                self.send_json({"success": True, "message": "Flower updated successfully"})

            else:
                self.send_error_json("Endpoint not found", 404)

            conn.close()
        except Exception as e:
            self.send_error_json(f"Server exception: {str(e)}", 500)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        token = self.get_auth_token()
        user = get_current_user(token)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # --- DELETE FLOWER (Admin) ---
            if re.match(r"^/api/flowers/(\d+)$", path):
                if not user or user.get("role") != "Admin":
                    self.send_error_json("Only Admin can delete flowers", 403)
                    conn.close()
                    return

                flower_id = int(re.match(r"^/api/flowers/(\d+)$", path).group(1))
                cursor.execute("DELETE FROM flowers WHERE flower_id = ?", (flower_id,))
                conn.commit()
                self.send_json({"success": True, "message": "Flower deleted successfully"})

            # --- DELETE CATEGORY (Admin) ---
            elif re.match(r"^/api/categories/(\d+)$", path):
                if not user or user.get("role") != "Admin":
                    self.send_error_json("Only Admin can delete categories", 403)
                    conn.close()
                    return

                category_id = int(re.match(r"^/api/categories/(\d+)$", path).group(1))
                cursor.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))
                conn.commit()
                self.send_json({"success": True, "message": "Category deleted successfully"})

            # --- DELETE STAFF (Admin) ---
            elif re.match(r"^/api/staff/(\d+)$", path):
                if not user or user.get("role") != "Admin":
                    self.send_error_json("Only Admin can delete staff", 403)
                    conn.close()
                    return

                staff_id = int(re.match(r"^/api/staff/(\d+)$", path).group(1))
                cursor.execute("DELETE FROM staff WHERE staff_id = ?", (staff_id,))
                conn.commit()
                self.send_json({"success": True, "message": "Staff member removed"})

            else:
                self.send_error_json("Endpoint not found", 404)

            conn.close()
        except Exception as e:
            self.send_error_json(f"Server exception: {str(e)}", 500)

    # ==================== STATIC FILE SERVING ====================

    def serve_static_file(self, path):
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

        if path == "/" or path == "":
            path = "/index.html"

        rel_path = path.lstrip("/").replace("/", os.sep)
        file_path = os.path.join(static_dir, rel_path)

        if not os.path.isfile(file_path):
            if not any(file_path.endswith(ext) for ext in [".css", ".js", ".png", ".jpg", ".svg", ".json", ".ico"]):
                file_path = os.path.join(static_dir, "index.html")
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"404 Not Found")
                return

        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "text/html" if file_path.endswith(".html") else "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if "text" in mime_type or "javascript" in mime_type else mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache, must-revalidate")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"500 Internal Server Error: {str(e)}".encode("utf-8"))

def run_server(host="0.0.0.0", port=8000):
    init_db()
    server = ThreadingHTTPServer((host, port), FlowerShopAPIHandler)
    print(f"============================================================")
    print(f"🌸 Flower Shop Management System Server Started Successfully!")
    print(f"   URL: http://localhost:{port}")
    print(f"   Listening on: {host}:{port}")
    print(f"   Database: SQLite ({DB_FILE})")
    print(f"============================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port=port)
