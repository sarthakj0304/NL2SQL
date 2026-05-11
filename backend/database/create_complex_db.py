import sqlite3
import random
from datetime import datetime, timedelta

def create_database():
    conn = sqlite3.connect('customer_care_sales.db')
    cursor = conn.cursor()

    # Create Tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            registration_date DATE NOT NULL,
            loyalty_tier TEXT DEFAULT 'Standard'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            hire_date DATE NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            is_subscription BOOLEAN DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            agent_id INTEGER,
            interaction_type TEXT NOT NULL,
            duration_seconds INTEGER,
            interaction_date DATETIME NOT NULL,
            resolution_status TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
            FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            agent_id INTEGER,
            product_id INTEGER,
            interaction_id INTEGER,
            sale_amount REAL NOT NULL,
            sale_date DATETIME NOT NULL,
            discount_applied REAL DEFAULT 0,
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
            FOREIGN KEY (agent_id) REFERENCES agents (agent_id),
            FOREIGN KEY (product_id) REFERENCES products (product_id),
            FOREIGN KEY (interaction_id) REFERENCES interactions (interaction_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            interaction_id INTEGER,
            customer_id INTEGER,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            comments TEXT,
            feedback_date DATETIME NOT NULL,
            FOREIGN KEY (interaction_id) REFERENCES interactions (interaction_id),
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
        )
    ''')

    # Insert Dummy Data
    
    # 1. Agents
    departments = ['Sales', 'Support', 'Retention']
    for i in range(1, 11):
        cursor.execute('''
            INSERT INTO agents (first_name, last_name, email, department, hire_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (f'Agent{i}', f'Smith{i}', f'agent{i}@ccare.com', random.choice(departments), '2023-01-15'))

    # 2. Products
    categories = ['Software', 'Hardware', 'Service', 'Subscription']
    for i in range(1, 21):
        cursor.execute('''
            INSERT INTO products (product_name, category, price, is_subscription)
            VALUES (?, ?, ?, ?)
        ''', (f'Product {i}', random.choice(categories), round(random.uniform(10.0, 500.0), 2), random.choice([0, 1])))

    # 3. Customers
    tiers = ['Standard', 'Silver', 'Gold', 'Platinum']
    for i in range(1, 101):
        reg_date = datetime.now() - timedelta(days=random.randint(10, 1000))
        cursor.execute('''
            INSERT INTO customers (first_name, last_name, email, phone, registration_date, loyalty_tier)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (f'Customer{i}', f'Doe{i}', f'customer{i}@email.com', f'555-01{i:02d}', reg_date.strftime('%Y-%m-%d'), random.choice(tiers)))

    # 4. Interactions and Sales
    types = ['Call', 'Chat', 'Email']
    statuses = ['Resolved', 'Escalated', 'Pending']
    
    for _ in range(300):
        cust_id = random.randint(1, 100)
        agent_id = random.randint(1, 10)
        inter_date = datetime.now() - timedelta(days=random.randint(1, 365), hours=random.randint(1, 24))
        
        cursor.execute('''
            INSERT INTO interactions (customer_id, agent_id, interaction_type, duration_seconds, interaction_date, resolution_status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (cust_id, agent_id, random.choice(types), random.randint(60, 3600), inter_date.strftime('%Y-%m-%d %H:%M:%S'), random.choice(statuses)))
        
        interaction_id = cursor.lastrowid
        
        # 30% chance of an interaction leading to a sale
        if random.random() < 0.3:
            prod_id = random.randint(1, 20)
            cursor.execute('SELECT price FROM products WHERE product_id = ?', (prod_id,))
            price = cursor.fetchone()[0]
            
            discount = round(random.uniform(0, 0.2) * price, 2)
            sale_amount = price - discount
            
            cursor.execute('''
                INSERT INTO sales (customer_id, agent_id, product_id, interaction_id, sale_amount, sale_date, discount_applied)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (cust_id, agent_id, prod_id, interaction_id, sale_amount, inter_date.strftime('%Y-%m-%d %H:%M:%S'), discount))

            # 50% chance of feedback if there was a sale
            if random.random() < 0.5:
                 cursor.execute('''
                    INSERT INTO feedback (interaction_id, customer_id, rating, comments, feedback_date)
                    VALUES (?, ?, ?, ?, ?)
                 ''', (interaction_id, cust_id, random.randint(3, 5), 'Great service!', (inter_date + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')))

    conn.commit()
    conn.close()
    print("Database 'customer_care_sales.db' created successfully with mock data.")

if __name__ == '__main__':
    create_database()
