"""
create_test_sqlite.py
─────────────────────
Creates a complex SQLite test database: `test_ecommerce.db`

Schema (8 tables, ~400 rows of sample data):
  categories   → products (FK)
  suppliers    → products (FK)
  departments  → employees (FK, self-ref manager)
  customers    ← orders → employees
  orders       ← order_items → products
  customers    ← reviews    → products

Run from the backend/ directory:
    python database/create_test_sqlite.py
"""

import sqlite3
import os
import random
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "test_ecommerce.db")


def rand_date(start: date, end: date) -> str:
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).isoformat()


def create(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript("""
    PRAGMA foreign_keys = ON;

    -- ── 1. categories ──────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS categories (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL UNIQUE,
        description TEXT
    );

    -- ── 2. suppliers ───────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS suppliers (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT    NOT NULL,
        contact_name TEXT,
        email        TEXT,
        phone        TEXT,
        country      TEXT
    );

    -- ── 3. departments ─────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS departments (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT    NOT NULL UNIQUE,
        budget REAL
    );

    -- ── 4. employees ───────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS employees (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name    TEXT    NOT NULL,
        last_name     TEXT    NOT NULL,
        title         TEXT,
        department_id INTEGER REFERENCES departments(id),
        hire_date     TEXT,
        salary        REAL,
        manager_id    INTEGER REFERENCES employees(id)
    );

    -- ── 5. products ────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS products (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        name           TEXT    NOT NULL,
        category_id    INTEGER REFERENCES categories(id),
        supplier_id    INTEGER REFERENCES suppliers(id),
        unit_price     REAL    NOT NULL,
        units_in_stock INTEGER DEFAULT 0,
        discontinued   INTEGER DEFAULT 0
    );

    -- ── 6. customers ───────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS customers (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT    NOT NULL,
        contact_name TEXT,
        city         TEXT,
        country      TEXT,
        email        TEXT,
        phone        TEXT
    );

    -- ── 7. orders ──────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS orders (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id   INTEGER NOT NULL REFERENCES customers(id),
        employee_id   INTEGER REFERENCES employees(id),
        order_date    TEXT    NOT NULL,
        shipped_date  TEXT,
        freight       REAL    DEFAULT 0,
        ship_country  TEXT,
        status        TEXT    DEFAULT 'Pending'
    );

    -- ── 8. order_items ─────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS order_items (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id    INTEGER NOT NULL REFERENCES orders(id),
        product_id  INTEGER NOT NULL REFERENCES products(id),
        unit_price  REAL    NOT NULL,
        quantity    INTEGER NOT NULL DEFAULT 1,
        discount    REAL    DEFAULT 0
    );

    -- ── 9. reviews ─────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS reviews (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id  INTEGER NOT NULL REFERENCES products(id),
        customer_id INTEGER NOT NULL REFERENCES customers(id),
        rating      INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
        comment     TEXT,
        review_date TEXT
    );
    """)
    conn.commit()


def seed(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # ── Categories ──────────────────────────────────────────────────────────
    categories = [
        ("Electronics",    "Gadgets, devices and accessories"),
        ("Clothing",       "Apparel for men, women and children"),
        ("Books",          "Fiction, non-fiction and academic titles"),
        ("Home & Kitchen", "Appliances, decor and cookware"),
        ("Sports",         "Equipment and outdoor gear"),
        ("Toys",           "Games and toys for all ages"),
        ("Groceries",      "Food, beverages and consumables"),
        ("Beauty",         "Skincare, cosmetics and personal care"),
    ]
    cur.executemany("INSERT INTO categories (name, description) VALUES (?,?)", categories)

    # ── Suppliers ───────────────────────────────────────────────────────────
    suppliers = [
        ("TechSource Ltd",     "Alan Park",    "apark@techsource.com",   "+1-555-0100", "USA"),
        ("FashionHub GmbH",    "Lena Braun",   "lbraun@fashionhub.de",   "+49-30-2200", "Germany"),
        ("PageTurner Co",      "Rita Rao",     "rrao@pageturner.in",     "+91-99000000","India"),
        ("HomePlus Corp",      "James Wu",     "jwu@homeplus.cn",        "+86-21-5500", "China"),
        ("SportsPro Inc",      "Carlos Ruiz",  "cruiz@sportspro.mx",     "+52-55-4400", "Mexico"),
        ("KidZone Pty",        "Sophie Hall",  "shall@kidzone.au",       "+61-2-9900",  "Australia"),
        ("FreshFarm LLC",      "Omar Hassan",  "ohassan@freshfarm.eg",   "+20-2-3300",  "Egypt"),
        ("GlowBeauty SA",      "Marie Dupont", "mdupont@glowbeauty.fr",  "+33-1-4400",  "France"),
    ]
    cur.executemany(
        "INSERT INTO suppliers (company_name, contact_name, email, phone, country) VALUES (?,?,?,?,?)",
        suppliers,
    )

    # ── Departments ─────────────────────────────────────────────────────────
    depts = [
        ("Engineering",  850000),
        ("Sales",        600000),
        ("Marketing",    400000),
        ("HR",           300000),
        ("Finance",      500000),
        ("Logistics",    350000),
    ]
    cur.executemany("INSERT INTO departments (name, budget) VALUES (?,?)", depts)

    # ── Employees (25) ──────────────────────────────────────────────────────
    employees_data = [
        # (first, last, title, dept_id, hire_date, salary, manager_id)
        ("Alice",   "Martin",  "VP Engineering",      1, "2015-03-01", 145000, None),
        ("Bob",     "Singh",   "VP Sales",            2, "2014-06-15", 140000, None),
        ("Carol",   "Zhang",   "Senior Engineer",     1, "2017-07-20", 110000, 1),
        ("David",   "Okafor",  "Engineer",            1, "2019-09-01",  90000, 1),
        ("Eva",     "Lopez",   "QA Lead",             1, "2018-04-12",  95000, 1),
        ("Frank",   "Weber",   "Sales Manager",       2, "2016-11-05", 115000, 2),
        ("Grace",   "Kim",     "Account Executive",   2, "2020-02-14",  78000, 6),
        ("Henry",   "Nakamura","Account Executive",   2, "2020-08-30",  76000, 6),
        ("Irene",   "Costa",   "Marketing Manager",   3, "2017-01-22", 105000, None),
        ("Jack",    "Brown",   "Content Strategist",  3, "2021-03-10",  72000, 9),
        ("Karen",   "Patel",   "HR Manager",          4, "2016-05-18", 100000, None),
        ("Leo",     "Müller",  "HR Specialist",       4, "2022-01-11",  65000, 11),
        ("Mia",     "Torres",  "CFO",                 5, "2013-09-01", 175000, None),
        ("Nathan",  "Chen",    "Financial Analyst",   5, "2019-07-07",  88000, 13),
        ("Olivia",  "Nguyen",  "Logistics Manager",   6, "2018-02-28",  98000, None),
        ("Paul",    "Adams",   "Warehouse Lead",      6, "2020-06-01",  70000, 15),
        ("Quinn",   "Rashid",  "Engineer",            1, "2021-10-15",  85000, 3),
        ("Rachel",  "Diaz",    "Engineer",            1, "2022-05-20",  83000, 3),
        ("Sam",     "Wilson",  "Sales Rep",           2, "2023-01-09",  68000, 6),
        ("Tina",    "Yamada",  "Sales Rep",           2, "2023-03-20",  67000, 6),
        ("Uma",     "Johansson","Designer",           3, "2021-08-01",  74000, 9),
        ("Victor",  "Petrov",  "Data Scientist",      1, "2020-11-30", 118000, 1),
        ("Wendy",   "Ali",     "Recruiter",           4, "2022-09-14",  63000, 11),
        ("Xavier",  "Gomez",   "Driver",              6, "2021-04-05",  55000, 15),
        ("Yuki",    "Andersen","Financial Analyst",   5, "2020-12-01",  86000, 13),
    ]
    cur.executemany(
        "INSERT INTO employees (first_name, last_name, title, department_id, hire_date, salary, manager_id) "
        "VALUES (?,?,?,?,?,?,?)",
        employees_data,
    )

    # ── Products (40) ───────────────────────────────────────────────────────
    products_data = [
        # (name, cat_id, sup_id, price, stock, discontinued)
        ("4K Smart TV 55\"",            1, 1,  699.99, 45, 0),
        ("Wireless Noise-Cancelling Headphones", 1, 1, 249.99, 120, 0),
        ("Laptop Pro 15",               1, 1, 1299.00,  30, 0),
        ("Bluetooth Speaker",           1, 1,   89.99, 200, 0),
        ("Smartwatch Series 5",         1, 1,  349.99,  85, 0),
        ("Running Jacket",              2, 2,   79.99, 300, 0),
        ("Yoga Pants",                  2, 2,   49.99, 450, 0),
        ("Cotton T-Shirt Pack (3)",     2, 2,   29.99, 600, 0),
        ("Winter Coat",                 2, 2,  149.99, 180, 0),
        ("Denim Jeans",                 2, 2,   69.99, 350, 0),
        ("Python Programming Guide",    3, 3,   39.99, 250, 0),
        ("Data Science Handbook",       3, 3,   44.99, 200, 0),
        ("The Great Novel",             3, 3,   14.99, 400, 0),
        ("History of Civilisation",     3, 3,   24.99, 150, 0),
        ("Children's Atlas",            3, 3,   19.99, 175, 0),
        ("Air Fryer 5L",                4, 4,  129.99,  90, 0),
        ("Stand Mixer",                 4, 4,  199.99,  60, 0),
        ("Bed Sheet Set King",          4, 4,   59.99, 220, 0),
        ("Coffee Maker Deluxe",         4, 4,   89.99, 110, 0),
        ("Non-Stick Pan Set",           4, 4,   74.99, 140, 0),
        ("Mountain Bike 29\"",          5, 5,  549.99,  25, 0),
        ("Tennis Racket Pro",           5, 5,   99.99,  80, 0),
        ("Yoga Mat Extra Thick",        5, 5,   34.99, 300, 0),
        ("Running Shoes",               5, 5,  119.99, 200, 0),
        ("Camping Tent 4-Person",       5, 5,  219.99,  55, 0),
        ("LEGO City Set",               6, 6,   59.99, 180, 0),
        ("RC Racing Car",               6, 6,   44.99, 130, 0),
        ("Dollhouse Deluxe",            6, 6,   89.99,  70, 0),
        ("Board Game: Strategy",        6, 6,   34.99, 200, 0),
        ("Educational Coding Kit",      6, 6,   49.99, 160, 0),
        ("Organic Olive Oil 1L",        7, 7,   12.99, 500, 0),
        ("Whole Grain Pasta 5-pack",    7, 7,    8.99, 800, 0),
        ("Premium Coffee Beans 1kg",    7, 7,   18.99, 350, 0),
        ("Protein Powder Vanilla 2kg",  7, 7,   39.99, 250, 0),
        ("Herbal Tea Variety Box",      7, 7,    9.99, 400, 0),
        ("Vitamin C Serum",             8, 8,   27.99, 300, 0),
        ("Moisturising Night Cream",    8, 8,   32.99, 280, 0),
        ("Perfume Eau de Parfum",       8, 8,   64.99, 150, 0),
        ("Shampoo & Conditioner Set",   8, 8,   19.99, 400, 0),
        ("Sunscreen SPF 50",            8, 8,   15.99, 350, 0),
    ]
    cur.executemany(
        "INSERT INTO products (name, category_id, supplier_id, unit_price, units_in_stock, discontinued) "
        "VALUES (?,?,?,?,?,?)",
        products_data,
    )

    # ── Customers (30) ──────────────────────────────────────────────────────
    customers_data = [
        ("Apex Retail", "John Doe",     "New York",    "USA",       "john@apexretail.com",    "+1-555-1001"),
        ("Blue Ocean Co", "Sarah Lee",  "London",      "UK",        "slee@blueocean.co.uk",   "+44-20-7001"),
        ("Sunrise Mart", "Ahmed Khan",  "Dubai",       "UAE",       "akhan@sunrisemart.ae",   "+971-4-5001"),
        ("TechWorld",   "Lisa Wang",    "Shanghai",    "China",     "lwang@techworld.cn",     "+86-21-6001"),
        ("Euro Trade",  "Hans Bauer",   "Berlin",      "Germany",   "hbauer@eurotrade.de",    "+49-30-7001"),
        ("Nordic Shop", "Ingrid Olsen", "Oslo",        "Norway",    "iolsen@nordicshop.no",   "+47-22-8001"),
        ("Maple Store", "Emma Wilson",  "Toronto",     "Canada",    "ewilson@maplestore.ca",  "+1-416-9001"),
        ("Sakura Ltd",  "Kenji Suzuki", "Tokyo",       "Japan",     "ksuzuki@sakura.jp",      "+81-3-1001"),
        ("Sol Market",  "Maria Santos", "São Paulo",   "Brazil",    "msantos@solmarket.br",   "+55-11-2001"),
        ("Cape Traders","Nelson Dube",  "Cape Town",   "S. Africa", "ndube@capetraders.za",   "+27-21-3001"),
        ("Desert Rose",  "Fatima Hassan","Riyadh",     "Saudi",     "fhassan@desertrose.sa",  "+966-11-4001"),
        ("Kangaroo Co", "Steve Black",  "Sydney",      "Australia", "sblack@kangaroo.au",     "+61-2-5001"),
        ("Alpine Goods","Pierre Fontaine","Zurich",    "Switzerland","pfontaine@alpine.ch",   "+41-44-6001"),
        ("Taj Emporium","Priya Sharma", "Mumbai",      "India",     "psharma@taj.in",         "+91-22-7001"),
        ("Nordic Fresh","Anna Lindqvist","Stockholm",  "Sweden",    "alindqvist@nordicfresh.se","+46-8-8001"),
        ("Pampas Corp", "Diego Torres", "Buenos Aires","Argentina", "dtorres@pampas.ar",      "+54-11-9001"),
        ("Nile Bazaar", "Youssef Farid","Cairo",       "Egypt",     "yfarid@nilebazaar.eg",   "+20-2-1001"),
        ("Kimchi Store","Ji-Yeon Park", "Seoul",       "South Korea","jypark@kimchi.kr",      "+82-2-2001"),
        ("Olive Grove", "Nikos Papadopoulos","Athens", "Greece",    "npapadopoulos@olive.gr", "+30-21-3001"),
        ("Tulip Trade", "Jan de Boer",  "Amsterdam",   "Netherlands","jdeboer@tulip.nl",      "+31-20-4001"),
        ("Savanna Co",  "Amara Diallo", "Nairobi",     "Kenya",     "adiallo@savanna.ke",     "+254-20-5001"),
        ("Baltic Hub",  "Andris Kalns", "Riga",        "Latvia",    "akalns@baltichub.lv",    "+371-67-6001"),
        ("Panda Mart",  "Wei Chen",     "Beijing",     "China",     "wchen@pandamart.cn",     "+86-10-7001"),
        ("Gulf Traders","Khalid Al-Sayed","Manama",    "Bahrain",   "kalsayed@gulf.bh",       "+973-17-8001"),
        ("Everest Co",  "Ravi Koirala", "Kathmandu",   "Nepal",     "rkoirala@everest.np",    "+977-1-9001"),
        ("Rio Direct",  "Luisa Ferreira","Rio de Janeiro","Brazil", "lferreira@rio.br",       "+55-21-1001"),
        ("Iberia Shop", "Carmen Vega",  "Madrid",      "Spain",     "cvega@iberia.es",        "+34-91-2001"),
        ("Fjord Retail","Lars Eriksen", "Copenhagen",  "Denmark",   "leriksen@fjord.dk",      "+45-33-3001"),
        ("Monsoon Bazaar","Laleh Ahmadi","Tehran",     "Iran",      "lahmadi@monsoon.ir",     "+98-21-4001"),
        ("Kiwi Goods",  "Fiona Campbell","Auckland",   "New Zealand","fcampbell@kiwi.nz",     "+64-9-5001"),
    ]
    cur.executemany(
        "INSERT INTO customers (company_name, contact_name, city, country, email, phone) VALUES (?,?,?,?,?,?)",
        customers_data,
    )

    # ── Orders (80) ─────────────────────────────────────────────────────────
    statuses = ["Delivered", "Delivered", "Delivered", "Shipped", "Processing", "Cancelled"]
    ship_countries = ["USA", "UK", "Germany", "Japan", "Canada", "Australia", "France", "India"]
    random.seed(42)

    order_rows = []
    for _ in range(80):
        cust_id = random.randint(1, 30)
        emp_id  = random.randint(6, 20)
        o_date  = rand_date(date(2023, 1, 1), date(2024, 6, 30))
        s_date  = rand_date(date(2024, 1, 1), date(2024, 12, 31))
        freight = round(random.uniform(5, 80), 2)
        country = random.choice(ship_countries)
        status  = random.choice(statuses)
        order_rows.append((cust_id, emp_id, o_date, s_date, freight, country, status))

    cur.executemany(
        "INSERT INTO orders (customer_id, employee_id, order_date, shipped_date, freight, ship_country, status) "
        "VALUES (?,?,?,?,?,?,?)",
        order_rows,
    )

    # ── Order Items (200) ───────────────────────────────────────────────────
    item_rows = []
    for order_id in range(1, 81):
        n_items = random.randint(1, 4)
        prod_ids = random.sample(range(1, 41), n_items)
        for pid in prod_ids:
            qty      = random.randint(1, 10)
            price    = round(random.uniform(10, 700), 2)
            discount = round(random.choice([0, 0, 0, 0.05, 0.1, 0.15, 0.2]), 2)
            item_rows.append((order_id, pid, price, qty, discount))

    cur.executemany(
        "INSERT INTO order_items (order_id, product_id, unit_price, quantity, discount) VALUES (?,?,?,?,?)",
        item_rows,
    )

    # ── Reviews (120) ───────────────────────────────────────────────────────
    comments = [
        "Excellent product, highly recommend!",
        "Good quality but a bit pricey.",
        "Arrived quickly, great packaging.",
        "Not what I expected.",
        "Perfect for my needs.",
        "Will definitely buy again.",
        "Average quality.",
        "Outstanding value for money!",
        "Disappointed with the durability.",
        "Exactly as described.",
    ]
    review_rows = []
    used = set()
    while len(review_rows) < 120:
        pid  = random.randint(1, 40)
        cid  = random.randint(1, 30)
        if (pid, cid) in used:
            continue
        used.add((pid, cid))
        rating  = random.randint(1, 5)
        comment = random.choice(comments)
        r_date  = rand_date(date(2023, 6, 1), date(2024, 12, 31))
        review_rows.append((pid, cid, rating, comment, r_date))

    cur.executemany(
        "INSERT INTO reviews (product_id, customer_id, rating, comment, review_date) VALUES (?,?,?,?,?)",
        review_rows,
    )

    conn.commit()
    print("Seeded all tables successfully.")


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed old DB: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    print(f"Creating {DB_PATH} ...")
    create(conn)
    seed(conn)
    conn.close()

    size_kb = os.path.getsize(DB_PATH) / 1024
    print(f"Done! Database: {DB_PATH}  ({size_kb:.1f} KB)")
    print()
    print("Sample queries to try:")
    print('  "List all products in the Electronics category"')
    print('  "Which customers are from Germany?"')
    print('  "Show the top 5 most expensive products"')
    print('  "How many orders were delivered?"')
    print('  "What is the average salary in the Engineering department?"')
    print('  "List employees who earn more than 100000"')
    print('  "Which products have the highest average rating?"')


if __name__ == "__main__":
    main()
