import streamlit as st
import sqlite3
import json
import os
import hashlib
import secrets
import random
from datetime import datetime, timedelta
try:
    import psycopg2
    from psycopg2 import pool
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None

# --- DATABASE CONFIGURATION ---
# We check if Supabase/Postgres secrets are available.
# If available, we use PostgreSQL. Otherwise, we fallback to SQLite.
DB_PATH = "database/crm_database.db"

def get_db_config():
    """Determine if we should use Cloud (Postgres) or Local (SQLite)."""
    # Try multiple ways to get the URL
    url = None
    try:
        # Check standard Streamlit connections format
        if "connections" in st.secrets and "postgresql" in st.secrets["connections"]:
            url = st.secrets["connections"]["postgresql"].get("url")
        elif "DATABASE_URL" in st.secrets:
            url = st.secrets["DATABASE_URL"]
        elif "SUPABASE_URL" in st.secrets:
            url = st.secrets["SUPABASE_URL"]
    except Exception:
        pass
    
    if url and url != "" and "[YOUR-PASSWORD]" not in url and url.startswith(("postgres://", "postgresql://")):
        return "postgres", url
    return "sqlite", DB_PATH

DB_TYPE, DB_URL = get_db_config()

# --- CONNECTION POOLING ---
@st.cache_resource
def get_connection_pool():
    if DB_TYPE == "postgres" and psycopg2:
        try:
            # Threaded pool is better for Streamlit's architecture
            return psycopg2.pool.ThreadedConnectionPool(1, 20, DB_URL)
        except Exception as e:
            st.error(f"Failed to create connection pool: {e}")
            return None
    return None

POSTGRES_POOL = get_connection_pool()

def get_connection():
    if DB_TYPE == "postgres":
        if not psycopg2:
            st.error("psycopg2 not installed. Please run 'pip install psycopg2-binary'")
            return None
        
        if POSTGRES_POOL:
            try:
                return POSTGRES_POOL.getconn()
            except Exception as e:
                st.error(f"Error getting connection from pool: {e}")
                # Fallback to direct connection if pool fails
                return psycopg2.connect(DB_URL)
        else:
            return psycopg2.connect(DB_URL)
    else:
        # Ensure directory exists for local setups
        db_dir = os.path.dirname(DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def release_connection(conn):
    if DB_TYPE == "postgres" and POSTGRES_POOL and conn:
        try:
            POSTGRES_POOL.putconn(conn)
        except Exception:
            conn.close()
    elif conn:
        conn.close()

def execute_query(query, params=(), commit=False, fetch="all"):
    """
    Unified query executor that handles placeholder differences between SQLite (?) and Postgres (%s).
    """
    conn = get_connection()
    if not conn: return None
    
    # Adjust placeholders for Postgres if needed
    if DB_TYPE == "postgres":
        query = query.replace('?', '%s')
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()

    try:
        cursor.execute(query, params)
        
        result = None
        if fetch == "all":
            result = cursor.fetchall()
        elif fetch == "one":
            result = cursor.fetchone()
        elif fetch == "lastrowid":
            if DB_TYPE == "postgres":
                result = None 
            else:
                result = cursor.lastrowid

        if commit:
            conn.commit()
        
        return result
    finally:
        cursor.close()
        release_connection(conn)

def _hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f"{salt}:{h}"

@st.cache_resource
def init_db():
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    
    # SQL Adjustments for Postgres compatibility
    pk_type = "SERIAL PRIMARY KEY" if DB_TYPE == "postgres" else "INTEGER PRIMARY KEY AUTOINCREMENT"
    bool_type = "BOOLEAN" if DB_TYPE == "postgres" else "BOOLEAN DEFAULT 0"
    
    # Leads Table
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS leads (
            id {pk_type},
            name TEXT NOT NULL,
            company TEXT,
            email TEXT,
            phone TEXT,
            status TEXT DEFAULT 'New',
            temperature TEXT DEFAULT 'Warm',
            source TEXT DEFAULT 'Manual Entry',
            notes TEXT,
            remind_email TEXT,
            followup_date TEXT,
            last_followup_date TEXT,
            last_followup_notes TEXT,
            created_at TEXT
        )
    ''')
    
    # Tasks Table
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS tasks (
            id {pk_type},
            lead_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT DEFAULT 'Medium',
            due_date TEXT,
            remind_email TEXT,
            done {bool_type},
            status TEXT DEFAULT 'Pending',
            created_at TEXT,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
    ''')

    # Migration for Status Column in Tasks
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN status TEXT DEFAULT 'Pending'")
        conn.commit()
    except Exception:
        # In Postgres, if a command fails, the transaction is poisoned.
        # We must rollback to continue using the connection.
        if DB_TYPE == "postgres":
            conn.rollback()
        pass 
    
    # Settings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Reminder Logs
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS reminder_logs (
            id {pk_type},
            timestamp TEXT,
            emails_sent INTEGER,
            tasks_checked INTEGER,
            leads_checked INTEGER
        )
    ''')

    # Email Templates
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS email_templates (
            id {pk_type},
            name TEXT NOT NULL,
            subject TEXT,
            body TEXT,
            created_at TEXT
        )
    ''')

    # Campaigns
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS campaigns (
            id {pk_type},
            name TEXT NOT NULL,
            template_id INTEGER,
            subject TEXT,
            body TEXT,
            status TEXT DEFAULT 'Scheduled',
            stats_sent INTEGER DEFAULT 0,
            stats_failed INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (template_id) REFERENCES email_templates (id)
        )
    ''')
    
    # Campaign Logs
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS campaign_logs (
            id {pk_type},
            campaign_id INTEGER,
            email TEXT,
            status TEXT,
            error_message TEXT,
            sent_at TEXT,
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
        )
    ''')

    # Tactical Follow-up Intelligence Logs
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS followup_logs (
            id {pk_type},
            lead_id INTEGER,
            timestamp TEXT,
            method TEXT,
            result TEXT,
            notes TEXT,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
    ''')

    # Sales Report
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS sales_report (
            id {pk_type},
            month_year TEXT NOT NULL,
            category TEXT NOT NULL,
            client TEXT NOT NULL,
            amount REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT
        )
    ''')
    
    # Recurring Clients
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS recurring_clients (
            id {pk_type},
            client TEXT NOT NULL,
            default_amount REAL DEFAULT 0,
            default_notes TEXT
        )
    ''')
    
    # Users Table
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS users (
            id {pk_type},
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'User',
            allowed_pages TEXT,
            created_at TEXT
        )
    ''')

    if DB_TYPE == "postgres":
        conn.commit()

    # Initialize Default Admin if none exists
    hashed_admin = _hash_password("admin123")
    if DB_TYPE == "postgres":
        sql = """
        INSERT INTO users (username, password, role, allowed_pages, created_at) 
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (username) DO NOTHING
        """
        cursor.execute(sql, ("admin", hashed_admin, "Admin", "all", str(datetime.now())))
        conn.commit()
    else:
        sql = "INSERT OR IGNORE INTO users (username, password, role, allowed_pages, created_at) VALUES (?, ?, ?, ?, ?)"
        cursor.execute(sql, ("admin", hashed_admin, "Admin", "all", str(datetime.now())))
        conn.commit()
    
    cursor.close()
    
    if DB_TYPE == "postgres":
        sync_postgres_sequences()
        
    release_connection(conn)

def sync_postgres_sequences():
    """Resets Postgres sequences to the current max ID + 1 to prevent UniqueViolation errors."""
    tables = [
        'leads', 'tasks', 'settings', 'reminder_logs', 'email_templates', 
        'campaigns', 'campaign_logs', 'sales_report', 'recurring_clients', 'users'
    ]
    for table in tables:
        try:
            # PostgreSQL default sequence name for SERIAL/IDENTITY is usually table_column_seq
            # We target the 'id' column mostly, except settings which uses 'key' (not a sequence)
            if table == 'settings': continue
            
            # Use COALESCE to handle empty tables
            fix_sql = f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table}"
            db_call(fix_sql, commit=True)
        except Exception:
            # If pg_get_serial_sequence fails, try the standard name pattern
            try:
                standard_seq = f"{table}_id_seq"
                fix_sql = f"SELECT setval('{standard_seq}', COALESCE(MAX(id), 1)) FROM {table}"
                db_call(fix_sql, commit=True)
            except Exception:
                pass # Skip if sequence doesn't exist or isn't named normally

# --- HELPER FOR DB ACCESS ---
# To avoid rewriting every function, we make a small wrapper to handle connections
def db_call(query, params=(), fetch="all", commit=True):
    # This is a bit lazy but effective for migration
    conn = get_connection()
    if not conn: return [] if fetch == "all" else None

    if DB_TYPE == "postgres":
        query = query.replace('?', '%s')
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()

    try:
        cursor.execute(query, params)
        if commit: conn.commit()
        
        if fetch == "all":
            if DB_TYPE == "postgres" and cursor.description is None:
                return []
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        elif fetch == "one":
            if DB_TYPE == "postgres" and cursor.description is None:
                return None
            row = cursor.fetchone()
            return dict(row) if row else None
        elif fetch == "lastrowid":
            if DB_TYPE == "postgres":
                return None
            return cursor.lastrowid
    finally:
        cursor.close()
        release_connection(conn)

# --- REWRITTEN API ---
def verify_user(username, password):
    user = db_call("SELECT * FROM users WHERE username = ?", (username,), fetch="one")
    if user:
        stored_password = user['password']
        if ":" in stored_password:
            try:
                salt, h = stored_password.split(":")
                hashed_input = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
                if hashed_input == h:
                    return user
            except Exception:
                pass
    return None

@st.cache_data
def get_all_users():
    return db_call("SELECT * FROM users ORDER BY id DESC")

def add_user(data):
    try:
        if "password" in data:
            data["password"] = _hash_password(data["password"])
        keys = data.keys()
        columns = ', '.join(keys)
        placeholders = ', '.join(['?' for _ in keys])
        sql = f"INSERT INTO users ({columns}) VALUES ({placeholders})"
        db_call(sql, list(data.values()))
        get_all_users.clear()
        return True
    except Exception:
        return False

def update_user(user_id, data):
    if "password" in data and data["password"]:
        data["password"] = _hash_password(data["password"])
    elif "password" in data:
        del data["password"]
    
    keys = data.keys()
    set_clause = ', '.join([f"{k} = ?" for k in keys])
    sql = f"UPDATE users SET {set_clause} WHERE id = ?"
    db_call(sql, list(data.values()) + [user_id])
    get_all_users.clear()

def delete_user(user_id):
    db_call("DELETE FROM users WHERE id = ?", (user_id,))
    get_all_users.clear()

@st.cache_data
def get_all_sales():
    return db_call("SELECT * FROM sales_report ORDER BY month_year DESC, category ASC")

def add_sale(data):
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO sales_report ({columns}) VALUES ({placeholders})"
    db_call(sql, list(data.values()))
    get_all_sales.clear()
    return True

def delete_sale(sale_id):
    db_call("DELETE FROM sales_report WHERE id = ?", (sale_id,))
    get_all_sales.clear()

@st.cache_data
def get_recurring_clients():
    return db_call("SELECT * FROM recurring_clients ORDER BY client ASC")

def add_recurring_client(data):
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO recurring_clients ({columns}) VALUES ({placeholders})"
    db_call(sql, list(data.values()))
    get_recurring_clients.clear()
    return True

def delete_recurring_client(client_id):
    db_call("DELETE FROM recurring_clients WHERE id = ?", (client_id,))
    get_recurring_clients.clear()

@st.cache_data
def get_all_leads():
    return db_call("SELECT * FROM leads ORDER BY id DESC")

def add_lead(data):
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO leads ({columns}) VALUES ({placeholders})"
    db_call(sql, list(data.values()))
    get_all_leads.clear()
    return True

def update_lead(lead_id, data):
    keys = data.keys()
    set_clause = ', '.join([f"{k} = ?" for k in keys])
    sql = f"UPDATE leads SET {set_clause} WHERE id = ?"
    db_call(sql, list(data.values()) + [lead_id])
    get_all_leads.clear()

def delete_lead(lead_id):
    db_call("DELETE FROM tasks WHERE lead_id = ?", (lead_id,))
    db_call("DELETE FROM leads WHERE id = ?", (lead_id,))
    get_all_leads.clear()
    get_all_tasks.clear()

@st.cache_data
def get_all_tasks():
    return db_call("SELECT * FROM tasks ORDER BY id DESC")

def add_task(data):
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO tasks ({columns}) VALUES ({placeholders})"
    db_call(sql, list(data.values()))
    get_all_tasks.clear()
    return True

def update_task(task_id, data):
    keys = data.keys()
    set_clause = ', '.join([f"{k} = ?" for k in keys])
    sql = f"UPDATE tasks SET {set_clause} WHERE id = ?"
    db_call(sql, list(data.values()) + [task_id])
    get_all_tasks.clear()

def delete_task(task_id):
    db_call("DELETE FROM tasks WHERE id = ?", (task_id,))
    get_all_tasks.clear()

@st.cache_data
def get_settings(defaults):
    rows = db_call("SELECT key, value FROM settings")
    settings = defaults.copy()
    for row in rows:
        key, val = row['key'], row['value']
        if val.lower() == 'true': val = True
        elif val.lower() == 'false': val = False
        elif str(val).isdigit(): val = int(val)
        settings[key] = val
    return settings

def save_settings(settings_dict):
    for key, val in settings_dict.items():
        if DB_TYPE == "postgres":
            sql = """
            INSERT INTO settings (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """
            db_call(sql, (key, str(val)))
        else:
            db_call("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(val)))
    get_settings.clear()

def add_log(emails_sent, tasks_checked, leads_checked):
    db_call("INSERT INTO reminder_logs (timestamp, emails_sent, tasks_checked, leads_checked) VALUES (?, ?, ?, ?)",
            (str(datetime.now()), emails_sent, tasks_checked, leads_checked))
    get_logs.clear()

@st.cache_data
def get_logs(limit=30):
    return db_call("SELECT * FROM reminder_logs ORDER BY id DESC LIMIT ?", (limit,))

@st.cache_data
def get_all_templates():
    return db_call("SELECT * FROM email_templates ORDER BY id DESC")

def add_template(data):
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO email_templates ({columns}) VALUES ({placeholders})"
    db_call(sql, list(data.values()))
    get_all_templates.clear()
    return True

def delete_template(template_id):
    db_call("DELETE FROM email_templates WHERE id = ?", (template_id,))
    get_all_templates.clear()

def update_template(template_id, data):
    keys = data.keys()
    set_clause = ', '.join([f"{k} = ?" for k in keys])
    sql = f"UPDATE email_templates SET {set_clause} WHERE id = ?"
    db_call(sql, list(data.values()) + [template_id])
    get_all_templates.clear()

@st.cache_data
def get_all_campaigns():
    return db_call("SELECT * FROM campaigns ORDER BY id DESC")

def add_campaign(data):
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO campaigns ({columns}) VALUES ({placeholders})"
    db_call(sql, list(data.values()))
    get_all_campaigns.clear()
    return True

def update_campaign_stats(campaign_id, sent, failed):
    db_call("UPDATE campaigns SET stats_sent = ?, stats_failed = ?, status = 'Completed' WHERE id = ?", 
            (sent, failed, campaign_id))
    get_all_campaigns.clear()

def add_campaign_log(campaign_id, email, status, error_message=""):
    db_call("INSERT INTO campaign_logs (campaign_id, email, status, error_message, sent_at) VALUES (?, ?, ?, ?, ?)",
            (campaign_id, email, status, error_message, str(datetime.now())))
    get_campaign_logs.cache_clear() if hasattr(get_campaign_logs, 'cache_clear') else None

def clear_all_db_caches():
    """Manually clear all Streamlit caches for database functions."""
    try:
        get_all_leads.clear()
        get_all_tasks.clear()
        get_all_sales.clear()
        get_recurring_clients.clear()
        if hasattr(get_settings, 'clear'): get_settings.clear()
        if hasattr(get_all_campaigns, 'clear'): get_all_campaigns.clear()
        if hasattr(get_campaign_logs, 'clear'): get_campaign_logs.clear()
    except Exception:
        pass

def generate_dummy_data():
    """Generates two years of realistic dummy data (leads, tasks, and sales) for 2025 and 2026."""
    import random
    
    # 1. GENERATE LEADS (15 records)
    lead_names = [
        "Ahmed Khan", "Sara Malik", "Zainab Ali", "Usman Sheikh", "Faizan Qureshi",
        "Ayesha Siddiqa", "Bilal Ahmed", "Hira Shah", "Imran Abbas", "Kiran Noor",
        "Muneeb Farooq", "Nida Yasir", "Omar Lodhi", "Rabia Batool", "Sami Ullah"
    ]
    companies = ["Global Tech", "Marketing Pro", "Real Estate Co", "Freelance Hub", "Retail Group", "Hospitality Solutions", "Education Inst"]
    sources = ["Website", "Referral", "Ads", "Other"]
    temps = ["Hot", "Warm", "Cold"]
    statuses = ["New", "In Progress", "Closed"]

    for i in range(15):
        name = lead_names[i]
        comp = random.choice(companies)
        temp = random.choice(temps)
        stat = random.choice(statuses)
        src = random.choice(sources)
        followup = (datetime.now() + timedelta(days=random.randint(-30, 365))).strftime('%Y-%m-%d')
        
        add_lead({
            "name": name, "company": comp, "email": f"{name.lower().replace(' ', '.')}@example.com",
            "phone": f"03{random.randint(10, 45)}-{random.randint(1000000, 9999999)}",
            "status": stat, "temperature": temp, "source": src,
            "notes": f"High potential lead from {src} looking for {comp} services.",
            "followup_date": followup, "created_at": str(datetime.now() - timedelta(days=random.randint(1, 365)))
        })

    # 2. GENERATE SALES (Weekly for 2 years)
    categories = ["Software License", "Professional Services", "System Integration", "Cloud Hosting", "Training & Support"]
    months_2025 = [f"2025-{str(m).zfill(2)}" for m in range(1, 13)]
    months_2026 = [f"2026-{str(m).zfill(2)}" for m in range(1, 13)]
    all_months = months_2025 + months_2026

    for m_y in all_months:
        for _ in range(2):
            add_sale({
                "month_year": m_y,
                "category": random.choice(categories),
                "client": random.choice(lead_names),
                "amount": round(random.uniform(500, 15000), 2),
                "notes": "Automated dummy entry for performance testing.",
                "created_at": f"{m_y}-15 10:00:00"
            })

    # 3. GENERATE TASKS (30 records)
    all_leads = get_all_leads()
    task_titles = ["Follow up email", "Initial pitch", "Requirement gathering", "Proposal submission", "Contract signing", "System setup"]
    
    if all_leads:
        for i in range(30):
            lead = random.choice(all_leads)
            due = (datetime.now() + timedelta(days=random.randint(-15, 60))).strftime('%Y-%m-%d')
            add_task({
                "lead_id": lead['id'],
                "title": f"{random.choice(task_titles)} — {lead['name']}",
                "description": "Standard operational task for the sales pipeline.",
                "priority": random.choice(["High", "Medium", "Low"]),
                "due_date": due, "done": random.choice([True, False]),
                "status": "Completed" if random.random() > 0.5 else "Pending",
                "created_at": str(datetime.now())
            })
    
    clear_all_db_caches()
    return True

@st.cache_data
def get_campaign_logs(campaign_id):
    return db_call("SELECT * FROM campaign_logs WHERE campaign_id = ?", (campaign_id,))

@st.cache_data
def get_followup_logs(lead_id):
    return db_call("SELECT * FROM followup_logs WHERE lead_id = ? ORDER BY timestamp DESC", (lead_id,))

def add_followup_log(data):
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO followup_logs ({columns}) VALUES ({placeholders})"
    db_call(sql, list(data.values()))
    get_followup_logs.clear()
    return True
