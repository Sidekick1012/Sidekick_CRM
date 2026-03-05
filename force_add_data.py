
import os
import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "database/crm_database.db"

def add_lead(conn, data):
    keys = data.keys()
    cols = ', '.join(keys)
    ph = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO leads ({cols}) VALUES ({ph})"
    conn.execute(sql, list(data.values()))

def add_sale(conn, data):
    keys = data.keys()
    cols = ', '.join(keys)
    ph = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO sales_report ({cols}) VALUES ({ph})"
    conn.execute(sql, list(data.values()))

def add_task(conn, data):
    keys = data.keys()
    cols = ', '.join(keys)
    ph = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO tasks ({cols}) VALUES ({ph})"
    conn.execute(sql, list(data.values()))

def generate():
    if not os.path.exists(DB_PATH):
        print("DB not found at", DB_PATH)
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Ensure status column exists in tasks
    try:
        conn.execute("ALTER TABLE tasks ADD COLUMN status TEXT DEFAULT 'Pending'")
    except:
        pass

    # Ensure sales_report table exists
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sales_report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_year TEXT NOT NULL,
            category TEXT NOT NULL,
            client TEXT NOT NULL,
            amount REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT
        )
    ''')

    # 1. LEADS
    lead_names = ["Ahmed Khan", "Sara Malik", "Zainab Ali", "Usman Sheikh", "Faizan Qureshi", "Ayesha Siddiqa", "Bilal Ahmed", "Hira Shah", "Imran Abbas", "Kiran Noor", "Muneeb Farooq", "Nida Yasir", "Omar Lodhi", "Rabia Batool", "Sami Ullah"]
    companies = ["Global Tech", "Marketing Pro", "Real Estate Co", "Freelance Hub", "Retail Group"]
    
    print("Adding 15 Leads...")
    for name in lead_names:
        add_lead(conn, {
            "name": name,
            "company": random.choice(companies),
            "email": f"{name.lower().replace(' ', '.')}@example.com",
            "phone": f"03{random.randint(11, 45)}-{random.randint(1000000, 9999999)}",
            "status": random.choice(["New", "In Progress", "Closed"]),
            "temperature": random.choice(["Hot", "Warm", "Cold"]),
            "source": random.choice(["Website", "Referral", "Ads", "Other"]),
            "notes": "Generated dummy lead.",
            "followup_date": (datetime.now() + timedelta(days=random.randint(1, 60))).strftime('%Y-%m-%d'),
            "created_at": str(datetime.now())
        })

    # 2. SALES
    print("Adding 48 Sales records (2025-2026)...")
    cats = ["Software License", "Services", "Integration"]
    all_months = [f"2025-{str(m).zfill(2)}" for m in range(1, 13)] + [f"2026-{str(m).zfill(2)}" for m in range(1, 13)]
    for m_y in all_months:
        for _ in range(2):
            add_sale(conn, {
                "month_year": m_y,
                "category": random.choice(cats),
                "client": random.choice(lead_names),
                "amount": round(random.uniform(1000, 10000), 2),
                "notes": "Project Fee",
                "created_at": f"{m_y}-15 12:00:00"
            })

    # 3. TASKS
    print("Adding 30 Tasks...")
    leads = conn.execute("SELECT id, name FROM leads ORDER BY id DESC LIMIT 15").fetchall()
    titles = ["Follow up", "Proposal", "Meeting", "Contract"]
    for i in range(30):
        lead = random.choice(leads)
        add_task(conn, {
            "lead_id": lead[0],
            "title": f"{random.choice(titles)}: {lead[1]}",
            "priority": random.choice(["High", "Medium", "Low"]),
            "due_date": (datetime.now() + timedelta(days=random.randint(-10, 30))).strftime('%Y-%m-%d'),
            "done": random.choice([0, 1]),
            "status": random.choice(["Pending", "In Progress", "Completed"]),
            "created_at": str(datetime.now())
        })

    conn.commit()
    conn.close()
    print("SUCCESS: 2025-2026 Data Integrated.")

if __name__ == "__main__":
    generate()
