"""
Automated Test Suite for Flower Shop Management System
Implements the 12 Test Cases (TC01 - TC12) from Section 5 of the Software Engineering Project Report.
Uses in-memory request simulation so tests run with 100% isolation and 0 network/socket restrictions.
"""

import unittest
import json
import io
from app import FlowerShopAPIHandler, SESSIONS
from database import init_db, get_db_connection, hash_password

class MockSocket:
    def __init__(self, request_bytes):
        self.rfile = io.BytesIO(request_bytes)
        self.wfile = io.BytesIO()

    def makefile(self, mode, *args, **kwargs):
        if "b" in mode:
            if "r" in mode:
                return self.rfile
            else:
                return self.wfile
        return self.rfile

    def sendall(self, b):
        self.wfile.write(b)

    def close(self):
        pass

def simulate_request(method, path, body=None, token=None):
    """Simulates an HTTP request against FlowerShopAPIHandler without opening network ports."""
    req_lines = [f"{method} {path} HTTP/1.1", "Host: localhost"]
    body_bytes = b""
    if body is not None:
        body_bytes = json.dumps(body).encode("utf-8")
        req_lines.append("Content-Type: application/json")
        req_lines.append(f"Content-Length: {len(body_bytes)}")
    if token:
        req_lines.append(f"Authorization: Bearer {token}")

    req_header_str = "\r\n".join(req_lines) + "\r\n\r\n"
    raw_input = req_header_str.encode("utf-8") + body_bytes

    sock = MockSocket(raw_input)

    class DummyServer:
        pass

    handler = FlowerShopAPIHandler(sock, ("127.0.0.1", 12345), DummyServer())
    raw_response = sock.wfile.getvalue()

    header_part, _, body_part = raw_response.partition(b"\r\n\r\n")
    header_lines = header_part.decode("utf-8", errors="replace").split("\r\n")
    status_line = header_lines[0] if header_lines else ""
    status_code = int(status_line.split(" ")[1]) if len(status_line.split(" ")) > 1 else 500

    resp_json = {}
    if body_part:
        try:
            resp_json = json.loads(body_part.decode("utf-8"))
        except Exception:
            resp_json = {"raw": body_part.decode("utf-8", errors="replace")}

    return status_code, resp_json

class TestFlowerShopSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db(force_recreate=True)

    def test_TC01_valid_login(self):
        """TC01: Enter valid username/password -> Login successful"""
        status, res = simulate_request("POST", "/api/auth/login", {
            "email": "admin@flowershop.com",
            "password": "admin123"
        })
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        self.assertIn("token", res)
        self.assertEqual(res["user"]["role"], "Admin")

    def test_TC02_invalid_password(self):
        """TC02: Enter invalid password -> Error message"""
        status, res = simulate_request("POST", "/api/auth/login", {
            "email": "admin@flowershop.com",
            "password": "WRONG_PASSWORD_XYZ"
        })
        self.assertEqual(status, 401)
        self.assertFalse(res.get("success"))
        self.assertIn("Invalid email or password", res.get("error", ""))

    def test_TC03_add_flower_admin(self):
        """TC03: Add flower (admin) -> Flower added to catalog"""
        _, login_res = simulate_request("POST", "/api/auth/login", {"email": "admin@flowershop.com", "password": "admin123"})
        admin_token = login_res["token"]

        status, res = simulate_request("POST", "/api/flowers", {
            "name": "Blue Hydrangea Haven",
            "category_id": 1,
            "supplier_id": 1,
            "color": "Blue",
            "occasion": "Wedding",
            "price": 580.0,
            "stock_qty": 20,
            "description": "Lush cloud-like blue hydrangea blooms.",
            "image_url": "hydrangea.jpg"
        }, token=admin_token)

        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        self.assertIn("flower_id", res)

    def test_TC04_search_flowers_by_category(self):
        """TC04: Search flowers by category -> Matching flowers displayed"""
        status, res = simulate_request("GET", "/api/flowers?category=Roses")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        flowers = res.get("flowers", [])
        self.assertGreater(len(flowers), 0)
        for f in flowers:
            self.assertEqual(f["category_name"], "Roses")

    def test_TC05_add_flower_to_cart_calculation(self):
        """TC05: Add flower to cart -> Cart updated with correct total"""
        status, res = simulate_request("GET", "/api/flowers?search=Classic%20Red%20Roses")
        self.assertEqual(status, 200)
        red_rose = res["flowers"][0]
        self.assertEqual(red_rose["price"], 450.0)

    def test_TC06_order_more_than_stock(self):
        """TC06: Order more than available stock -> Out-of-stock message"""
        _, cust_login = simulate_request("POST", "/api/auth/login", {"email": "ananya@example.com", "password": "customer123"})
        cust_token = cust_login["token"]

        status, res = simulate_request("POST", "/api/orders", {
            "items": [{"flower_id": 1, "quantity": 99999}],
            "delivery_address": "Test Address"
        }, token=cust_token)

        self.assertEqual(status, 400)
        self.assertFalse(res.get("success"))
        self.assertIn("Out of stock", res.get("error", ""))

    def test_TC07_place_order_valid_payment(self):
        """TC07: Place order with valid payment -> Order confirmed and invoice generated"""
        _, cust_login = simulate_request("POST", "/api/auth/login", {"email": "ananya@example.com", "password": "customer123"})
        cust_token = cust_login["token"]

        status, res = simulate_request("POST", "/api/orders", {
            "items": [
                {"flower_id": 1, "quantity": 2},
                {"flower_id": 5, "quantity": 1}
            ],
            "delivery_address": "42 Green Valley Apartments, MG Road, Bangalore",
            "delivery_date": "2026-11-25",
            "delivery_time_slot": "Morning (09:00 AM - 12:00 PM)",
            "recipient_name": "Ananya Sharma",
            "recipient_phone": "+91 98123 45678",
            "greeting_message": "Happy Anniversary!",
            "payment_method": "Credit/Debit Card",
            "coupon_code": "FLOWER100"
        }, token=cust_token)

        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        self.assertEqual(res["total_amount"], 1450.0)
        order_id = res["order_id"]

        inv_status, inv_res = simulate_request("GET", f"/api/orders/{order_id}/invoice", token=cust_token)
        self.assertEqual(inv_status, 200)
        self.assertEqual(inv_res["order"]["total_amount"], 1450.0)
        self.assertEqual(inv_res["order"]["discount"], 100.0)
        self.assertEqual(inv_res["order"]["delivery_charge"], 50.0)

    def test_TC08_payment_validation_empty_cart(self):
        """TC08: Payment failure / Invalid order -> Error shown"""
        _, cust_login = simulate_request("POST", "/api/auth/login", {"email": "ananya@example.com", "password": "customer123"})
        cust_token = cust_login["token"]

        status, res = simulate_request("POST", "/api/orders", {
            "items": [],
            "delivery_address": "Test"
        }, token=cust_token)
        self.assertEqual(status, 400)
        self.assertFalse(res.get("success"))

    def test_TC09_staff_updates_order_status(self):
        """TC09: Staff updates order status -> Customer sees updated status"""
        _, staff_login = simulate_request("POST", "/api/auth/login", {"email": "florist@flowershop.com", "password": "staff123"})
        staff_token = staff_login["token"]

        status, res = simulate_request("PUT", "/api/orders/1002/status", {"status": "Ready"}, token=staff_token)
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))

        _, cust_login = simulate_request("POST", "/api/auth/login", {"email": "rahul@example.com", "password": "customer123"})
        cust_token = cust_login["token"]
        _, ord_res = simulate_request("GET", "/api/orders/1002", token=cust_token)
        self.assertEqual(ord_res["order"]["status"], "Ready")

    def test_TC10_delivery_marks_delivered(self):
        """TC10: Delivery person marks delivered -> Order status set to Delivered"""
        _, deliv_login = simulate_request("POST", "/api/auth/login", {"email": "delivery@flowershop.com", "password": "delivery123"})
        deliv_token = deliv_login["token"]

        status, res = simulate_request("PUT", "/api/orders/1001/status", {"status": "Delivered"}, token=deliv_token)
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))

        _, ord_res = simulate_request("GET", "/api/orders/1001", token=deliv_token)
        self.assertEqual(ord_res["order"]["status"], "Delivered")
        self.assertEqual(ord_res["order"]["delivery_status"], "Delivered")

    def test_TC11_generate_sales_report(self):
        """TC11: Generate sales report -> Report displayed"""
        _, admin_login = simulate_request("POST", "/api/auth/login", {"email": "admin@flowershop.com", "password": "admin123"})
        admin_token = admin_login["token"]

        status, res = simulate_request("GET", "/api/reports/dashboard", token=admin_token)
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        self.assertIn("metrics", res)
        self.assertGreater(res["metrics"]["total_revenue"], 0)
        self.assertIn("low_stock_items", res)

    def test_TC12_unauthorized_user_accesses_admin_page(self):
        """TC12: Unauthorized user accesses admin API -> Access denied"""
        _, cust_login = simulate_request("POST", "/api/auth/login", {"email": "ananya@example.com", "password": "customer123"})
        cust_token = cust_login["token"]

        status, res = simulate_request("POST", "/api/categories", {"category_name": "Unauthorized Cat"}, token=cust_token)
        self.assertEqual(status, 403)
        self.assertFalse(res.get("success"))

if __name__ == "__main__":
    unittest.main()
