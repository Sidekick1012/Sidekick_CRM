import sqlite3
import json
import os
import hashlib
import secrets
from datetime import datetime
import streamlit as st

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
        # Check a flattened format as fallback
        elif "SUPABASE_URL" in st.secrets:
            url = st.secrets["SUPABASE_URL"]
    except Exception:
        pass
    
    if url and url != "" and "[YOUR-PASSWORD]" not in url:
        return "postgres", url
    return "sqlite", DB_PATH

DB_TYPE, DB_URL = get_db_config()

def get_connection():
    if DB_TYPE == "postgres":
        import psycopg2
        from psycopg2.extras import RealDictCursor
        try:
            conn = psycopg2.connect(DB_URL)
            return conn
        except Exception as e:
            st.error(f"PostgreSQL Connection Error: {e}")
            # Fallback (optional, but maybe better to show error)
            raise e
    else:
        # Ensure directory exists for local setups
        db_dir = os.path.dirname(DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(query, params=(), commit=False, fetch="all"):
    """
    Unified query executor that handles placeholder differences between SQLite (?) and Postgres (%s).
    """
    conn = get_connection()
    
    # Adjust placeholders for Postgres if needed
    if DB_TYPE == "postgres":
        query = query.replace('?', '%s')
        # Postgres expects SERIAL/IDENTITY for PKs, we handle that in init_db
        # We also need a cursor that returns dict-like objects
        import psycopg2.extras
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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
                # Postgres doesn't have lastrowid on the cursor like SQLite
                # Usually requires 'RETURNING id' in the query
                # However, for simplicity in migration, we'll try to find another way or just return None
                result = None 
            else:
                result = cursor.lastrowid

        if commit:
            conn.commit()
        
        return result
    finally:
        cursor.close()
        conn.close()

def _hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f"{salt}:{h}"

def init_db():
    conn = get_connection()
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
            created_at TEXT,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
    ''')
    
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

    # Initialize Default Admin
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()
    # Handle dict/row access robustly
    if isinstance(count, (tuple, list)):
        actual_count = count[0]
    elif isinstance(count, dict):
        # Postgres often returns lowercase 'count', SQLite often 'COUNT(*)'
        actual_count = count.get('count') or count.get('COUNT(*)') or list(count.values())[0]
    else:
        actual_count = 0
    
    if actual_count == 0:
        hashed_admin = _hash_password("admin123")
        sql = "INSERT INTO users (username, password, role, allowed_pages, created_at) VALUES (?, ?, ?, ?, ?)"
        if DB_TYPE == "postgres": sql = sql.replace('?', '%s')
        cursor.execute(sql, ("admin", hashed_admin, "Admin", "all", str(datetime.now())))
        conn.commit()
    
    conn.close()

# --- HELPER FOR DB ACCESS ---
# To avoid rewriting every function, we make a small wrapper to handle connections
def db_call(query, params=(), fetch="all", commit=True):
    # This is a bit lazy but effective for migration
    if DB_TYPE == "postgres":
        query = query.replace('?', '%s')
        import psycopg2.extras
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        conn = get_connection()
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
        conn.close()

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

def delete_user(user_id):
    db_call("DELETE FROM users WHERE id = ?", (user_id,))

def get_all_sales():
    return db_call("SELECT * FROM sales_report ORDER BY month_year DESC, category ASC")

def add_sale(data):
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO sales_report ({columns}) VALUES ({placeholders})"
    # For postgres, lastrowid is tricky without RETURNING, but let's try
    db_call(sql, list(data.values()))
    return True

def delete_sale(sale_id):
    db_call("DELETE FROM sales_report WHERE id = ?", (sale_id,))

def get_recurring_clients():
    return db_call("SELECT * FROM recurring_clients ORDER BY client ASC")

def add_recurring_client(data):
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO recurring_clients ({columns}) VALUES ({placeholders})"
    db_call(sql, list(data.values()))
    return True

def delete_recurring_client(client_id):
    db_call("DELETE FROM recurring_clients WHERE id = ?", (client_id,))

def get_all_leads():
    return db_call("SELECT * FROM leads ORDER BY id DESC")

def add_lead(data):
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO leads ({columns}) VALUES ({placeholders})"
    db_call(sql, list(data.values()))
    return True

def update_lead(lead_id, data):
    keys = data.keys()
    set_clause = ', '.join([f"{k} = ?" for k in keys])
    sql = f"UPDATE leads SET {set_clause} WHERE id = ?"
    db_call(sql, list(data.values()) + [lead_id])

def delete_lead(lead_id):
    db_call("DELETE FROM leads WHERE id = ?", (lead_id,))
    db_call("DELETE FROM tasks WHERE lead_id = ?", (lead_id,))

def get_all_tasks():
    return db_call("SELECT * FROM tasks ORDER BY id DESC")

def add_task(data):
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO tasks ({columns}) VALUES ({placeholders})"
    db_call(sql, list(data.values()))
    return True

def update_task(task_id, data):
    keys = data.keys()
    set_clause = ', '.join([f"{k} = ?" for k in keys])
    sql = f"UPDATE tasks SET {set_clause} WHERE id = ?"
    db_call(sql, list(data.values()) + [task_id])

def delete_task(task_id):
    db_call("DELETE FROM tasks WHERE id = ?", (task_id,))

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
        # Postgres doesn't have INSERT OR REPLACE, use UPSERT logic
        if DB_TYPE == "postgres":
            sql = """
            INSERT INTO settings (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """
            db_call(sql, (key, str(val)))
        else:
            db_call("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(val)))

def add_log(emails_sent, tasks_checked, leads_checked):
    db_call("INSERT INTO reminder_logs (timestamp, emails_sent, tasks_checked, leads_checked) VALUES (?, ?, ?, ?)",
            (str(datetime.now()), emails_sent, tasks_checked, leads_checked))

def get_logs(limit=30):
    return db_call("SELECT * FROM reminder_logs ORDER BY id DESC LIMIT ?", (limit,))

def get_all_templates():
    return db_call("SELECT * FROM email_templates ORDER BY id DESC")

def add_template(data):
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO email_templates ({columns}) VALUES ({placeholders})"
    db_call(sql, list(data.values()))
    return True

def delete_template(template_id):
    db_call("DELETE FROM email_templates WHERE id = ?", (template_id,))

def update_template(template_id, data):
    keys = data.keys()
    set_clause = ', '.join([f"{k} = ?" for k in keys])
    sql = f"UPDATE email_templates SET {set_clause} WHERE id = ?"
    db_call(sql, list(data.values()) + [template_id])

def get_all_campaigns():
    return db_call("SELECT * FROM campaigns ORDER BY id DESC")

def add_campaign(data):
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO campaigns ({columns}) VALUES ({placeholders})"
    db_call(sql, list(data.values()))
    return True

def update_campaign_stats(campaign_id, sent, failed):
    db_call("UPDATE campaigns SET stats_sent = ?, stats_failed = ?, status = 'Completed' WHERE id = ?", 
            (sent, failed, campaign_id))

def add_campaign_log(campaign_id, email, status, error_message=""):
    db_call("INSERT INTO campaign_logs (campaign_id, email, status, error_message, sent_at) VALUES (?, ?, ?, ?, ?)",
            (campaign_id, email, status, error_message, str(datetime.now())))

def get_campaign_logs(campaign_id):
    return db_call("SELECT * FROM campaign_logs WHERE campaign_id = ?", (campaign_id,))
