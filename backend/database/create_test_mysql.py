"""
create_test_mysql.py
────────────────────
Creates a complex MySQL test database: `test_ecommerce`

Run from the backend/ directory.
Requires mysql-connector-python and a running MySQL server.
"""

import random
from datetime import date, timedelta
try:
    import mysql.connector
except ImportError:
    print("Please install mysql-connector-python to run this script.")
    exit(1)

# Default credentials - adjust if necessary for your local setup
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "", # Add password if your local root has one
    "port": 3306
}
DB_NAME = "test_ecommerce"

def rand_date(start: date, end: date) -> str:
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).isoformat()

def create_database():
    print(f"Connecting to MySQL server to create database {DB_NAME}...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(f"DROP DATABASE IF EXISTS {DB_NAME};")
        cur.execute(f"CREATE DATABASE {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cur.close()
        conn.close()
        print(f"Database {DB_NAME} created successfully.")
    except Exception as e:
        print(f"Failed to create database: {e}")
        print("You may need to create it manually or adjust the credentials in this script.")
        exit(1)

def create_tables(conn):
    cur = conn.cursor()
    
    # ── 1. categories ──────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        name        VARCHAR(255) NOT NULL UNIQUE,
        description TEXT
    );
    """)

    # ── 2. suppliers ───────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        company_name VARCHAR(255) NOT NULL,
        contact_name VARCHAR(255),
        email        VARCHAR(255),
        phone        VARCHAR(50),
        country      VARCHAR(100)
    );
    """)

    # ── 3. departments ─────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id   INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        budget DECIMAL(15, 2)
    );
    """)

    # ── 4. employees ───────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        first_name    VARCHAR(100) NOT NULL,
        last_name     VARCHAR(100) NOT NULL,
        title         VARCHAR(100),
        department_id INT,
        hire_date     DATE,
        salary        DECIMAL(15, 2),
        manager_id    INT,
        FOREIGN KEY (department_id) REFERENCES departments(id),
        FOREIGN KEY (manager_id) REFERENCES employees(id)
    );
    """)

    # ── 5. products ────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id             INT AUTO_INCREMENT PRIMARY KEY,
        name           VARCHAR(255) NOT NULL,
        category_id    INT,
        supplier_id    INT,
        unit_price     DECIMAL(10, 2) NOT NULL,
        units_in_stock INT DEFAULT 0,
        discontinued   TINYINT(1) DEFAULT 0,
        FOREIGN KEY (category_id) REFERENCES categories(id),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    );
    """)

    # ── 6. customers ───────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        company_name VARCHAR(255) NOT NULL,
        contact_name VARCHAR(255),
        city         VARCHAR(100),
        country      VARCHAR(100),
        email        VARCHAR(255),
        phone        VARCHAR(50)
    );
    """)

    # ── 7. orders ──────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        customer_id   INT NOT NULL,
        employee_id   INT,
        order_date    DATE NOT NULL,
        shipped_date  DATE,
        freight       DECIMAL(10, 2) DEFAULT 0,
        ship_country  VARCHAR(100),
        status        VARCHAR(50) DEFAULT 'Pending',
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    );
    """)

    # ── 8. order_items ─────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        order_id    INT NOT NULL,
        product_id  INT NOT NULL,
        unit_price  DECIMAL(10, 2) NOT NULL,
        quantity    INT NOT NULL DEFAULT 1,
        discount    DECIMAL(4, 2) DEFAULT 0,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """)

    # ── 9. reviews ─────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        product_id  INT NOT NULL,
        customer_id INT NOT NULL,
        rating      INT NOT NULL CHECK(rating BETWEEN 1 AND 5),
        comment     TEXT,
        review_date DATE,
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );
    """)
    conn.commit()

def seed(conn):
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
    cur.executemany("INSERT INTO categories (name, description) VALUES (%s,%s)", categories)

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
        "INSERT INTO suppliers (company_name, contact_name, email, phone, country) VALUES (%s,%s,%s,%s,%s)",
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
    cur.executemany("INSERT INTO departments (name, budget) VALUES (%s,%s)", depts)

    # ── Employees (25) ──────────────────────────────────────────────────────
    employees_data = [
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
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        employees_data,
    )

    # ── Products (40) ───────────────────────────────────────────────────────
    products_data = [
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
        "VALUES (%s,%s,%s,%s,%s,%s)",
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
        "INSERT INTO customers (company_name, contact_name, city, country, email, phone) VALUES (%s,%s,%s,%s,%s,%s)",
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
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
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
        "INSERT INTO order_items (order_id, product_id, unit_price, quantity, discount) VALUES (%s,%s,%s,%s,%s)",
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
        "INSERT INTO reviews (product_id, customer_id, rating, comment, review_date) VALUES (%s,%s,%s,%s,%s)",
        review_rows,
    )

    conn.commit()
    print("Seeded all tables successfully.")

def main():
    create_database()
    
    print(f"Connecting to {DB_NAME} to create tables and insert data...")
    db_conn_config = DB_CONFIG.copy()
    db_conn_config["database"] = DB_NAME
    
    try:
        conn = mysql.connector.connect(**db_conn_config)
        create_tables(conn)
        seed(conn)
        conn.close()
        print(f"Done! Database '{DB_NAME}' is ready.")
        print(f"You can connect using DSN: mysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_NAME}")
    except Exception as e:
        print(f"Error seeding database: {e}")

if __name__ == "__main__":
    main()
