# 🌸 BloomCraft Florals - Flower Shop Management System

A full-stack, enterprise-grade **Flower Shop Management System** designed and built strictly according to the **Software Engineering Project Report Specification** (covering *Communication, Planning, Modeling, Construction, Testing, and Deployment*).

---

## 🌟 Key Highlights & Stakeholder Roles

The system supports 4 distinct user roles with full role-based access control (RBAC), SQLite persistent database, responsive web UI, and real-time order lifecycle tracking:

1. **🛍️ Customer**:
   - Register and login (auto-credited with 100 loyalty points).
   - Browse and search flowers by Category, Color, Occasion, and Price.
   - Interactive shopping cart with real-time stock guard.
   - Delivery scheduling (date & time slots), gift card message, promo coupons (`FLOWER100`, `WELCOME20`, `FREESHIP`).
   - Payment method selection (Card, UPI / QR, Cash on Delivery).
   - Live order lifecycle progress tracking (5 visual stages).
   - Instant printable GST Tax Invoice generation.

2. **💐 Florist / Shop Staff**:
   - Staff login with secure authentication.
   - Live queue of incoming and pending orders.
   - Order stage advancement: *Start Preparing* ➡️ *Mark Ready* ➡️ *Dispatch for Delivery*.
   - Assign orders to delivery riders.
   - Inventory stock monitoring table with automatic yellow low-stock warnings (< 10 stems) and 1-click restock buttons (`+10`, `+25`).
   - Instant invoice generation and printing.

3. **🛵 Delivery Rider**:
   - View assigned orders with delivery address, customer phone, scheduled time slot, and greeting note.
   - One-click status updates: *Start Delivery (Out for Delivery)* ➡️ *Mark Delivered (Confirm Delivery)*.
   - Direct click-to-call customer button.

4. **👑 Administrator**:
   - Executive dashboard with real-time KPI metrics: Total Revenue (₹), Total Orders, Pending Orders, Low Stock Alerts, Total Customers.
   - Visual sales reports: Sales by Category progress bars & Order status distribution.
   - Full CRUD over Flower Catalog, Categories, Suppliers, and Staff members.
   - Customer directory with lifetime value (LTV) and loyalty points.

---

## 🔑 Demo Accounts & Quick Switcher

The top of the web app features a **⚡ Quick Role Switcher** bar for 1-click testing:

| Role | Name | Email | Password | Pre-loaded Data |
| :--- | :--- | :--- | :--- | :--- |
| **👑 Administrator** | Sarah Admin | `admin@flowershop.com` | `admin123` | Full system control & analytics |
| **💐 Florist / Staff** | John Doe | `florist@flowershop.com` | `staff123` | Active order queue & inventory |
| **🛵 Delivery Rider** | Alex Kumar | `delivery@flowershop.com` | `delivery123` | Assigned deliveries |
| **🛍️ Customer** | Ananya Sharma | `ananya@example.com` | `customer123` | Existing Order #1001 & #1002 |

*New customers can also self-register with full name, email, phone, and address.*

---

## 🗄️ Database Architecture (SQLite)

Designed exactly as per Section 3.7 Entity Relationship (ER) Diagram of the project specification:

- `customers`: `customer_id`, `name`, `email`, `password_hash`, `phone`, `address`, `loyalty_points`, `created_at`
- `staff`: `staff_id`, `name`, `role` (Admin/Florist/Delivery), `email`, `password_hash`, `phone`, `created_at`
- `categories`: `category_id`, `category_name`, `description`, `image_url`
- `suppliers`: `supplier_id`, `name`, `contact`, `email`, `address`
- `flowers`: `flower_id`, `category_id`, `supplier_id`, `name`, `color`, `occasion`, `price`, `stock_qty`, `description`, `image_url`
- `orders`: `order_id`, `customer_id`, `order_date`, `delivery_date`, `delivery_time_slot`, `delivery_address`, `recipient_name`, `recipient_phone`, `greeting_message`, `status`, `subtotal`, `delivery_charge`, `discount`, `total_amount`, `payment_status`, `payment_method`
- `order_items`: `item_id`, `order_id`, `flower_id`, `quantity`, `unit_price`, `subtotal`
- `payments`: `payment_id`, `order_id`, `method`, `amount`, `status`, `paid_on`, `transaction_ref`
- `deliveries`: `delivery_id`, `order_id`, `staff_id`, `address`, `status`, `assigned_on`, `delivered_on`, `notes`

---

## 📐 Order Life Cycle (State Diagram Implementation)

```
[In Cart] ➡️ [Order Placed] ➡️ [Payment Confirmed] ➡️ [Preparing / Ready] ➡️ [Out for Delivery] ➡️ [Delivered]
                                        ↳ (or Cancelled ➡️ Stock Automatically Restored)
```

---

## 🚀 How to Run the Application

### Option A: Double-Click Launcher (Windows)
Double-click `run_server.bat` in the root folder.

### Option B: Command Line
Open PowerShell or Command Prompt in this folder and run:
```powershell
& "C:\Users\Vamsi\AppData\Local\Programs\Thonny\python.exe" app.py
```
*(or simply `python app.py` if python is in your system PATH)*

Then open your browser and navigate to:
👉 **`http://localhost:8000`**

---

## 🧪 Automated Testing Suite (Section 5)

All 12 test cases specified in the project report are automated in `test_system.py`:

```powershell
& "C:\Users\Vamsi\AppData\Local\Programs\Thonny\python.exe" test_system.py
```

### Verification Matrix:
- **TC01**: Valid username/password login ➡️ ✅ PASS
- **TC02**: Invalid password error handling ➡️ ✅ PASS
- **TC03**: Admin adds flower to catalog ➡️ ✅ PASS
- **TC04**: Search flowers by category ➡️ ✅ PASS
- **TC05**: Add flower to cart & price calculation ➡️ ✅ PASS
- **TC06**: Order more than available stock guard ➡️ ✅ PASS
- **TC07**: Place order & invoice calculation (`Total = Subtotal + Delivery - Discount`) ➡️ ✅ PASS
- **TC08**: Empty cart / validation failure ➡️ ✅ PASS
- **TC09**: Staff updates order status ➡️ ✅ PASS
- **TC10**: Delivery person marks delivered ➡️ ✅ PASS
- **TC11**: Admin generates sales & revenue report ➡️ ✅ PASS
- **TC12**: Unauthorized customer blocked from admin API (HTTP 403) ➡️ ✅ PASS

---

## 📁 Project Structure

```
flower-shop-management-system/
├── app.py              # Multi-threaded Python HTTP Server & REST API
├── database.py         # SQLite schema initialization and seed data
├── test_system.py      # Automated test runner covering TC01-TC12
├── run_server.bat      # Windows 1-click launcher
├── README.md           # Documentation
└── static/
    ├── index.html      # Single Page Application
    ├── css/
    │   └── styles.css  # Elegant floral design system
    └── js/
        └── app.js      # Frontend controller & API client
```
