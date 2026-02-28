import sqlite3
import json
import os
import hashlib
import secrets
from datetime import datetime

DB_PATH = "database/crm_database.db"

def get_connection():
    # Ensure directory exists for deployment/local setups
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _hash_password(password, salt=None):
    """Securely hash a password using scrypt with a unique salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    # Using scrypt (standard in Python 3.6+)
    # n=2^14, r=8, p=1 are standard recommendations
    h = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f"{salt}:{h}"

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Leads Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT DEFAULT 'Medium',
            due_date TEXT,
            remind_email TEXT,
            done BOOLEAN DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
    ''')
    
    # Settings Table (Key-Value)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Reminder Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminder_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            emails_sent INTEGER,
            tasks_checked INTEGER,
            leads_checked INTEGER
        )
    ''')

    # Email Templates Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT,
            body TEXT,
            created_at TEXT
        )
    ''')

    # Campaigns Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    
    # Campaign Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaign_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            email TEXT,
            status TEXT,
            error_message TEXT,
            sent_at TEXT,
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
        )
    ''')
    # Sales Report Table
    cursor.execute('''
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
    
    # Recurring Clients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recurring_clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client TEXT NOT NULL,
            default_amount REAL DEFAULT 0,
            default_notes TEXT
        )
    ''')
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'User',
            allowed_pages TEXT,
            created_at TEXT
        )
    ''')

    # Initialize Default Admin if none exists
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        hashed_admin = _hash_password("admin123")
        cursor.execute("INSERT INTO users (username, password, role, allowed_pages, created_at) VALUES (?, ?, ?, ?, ?)",
                       ("admin", hashed_admin, "Admin", "all", str(datetime.now())))
    
    # Automatic Password Migration (Transition plain-text or SHA-256 to salted scrypt)
    cursor.execute("SELECT id, password FROM users")
    all_users = cursor.fetchall()
    for u in all_users:
        stored_p = u['password']
        # If it doesn't have a colon, it's either plain-text or SHA-256
        if ":" not in stored_p:
            # If length is 64, it's SHA-256. If not, it's plain-text.
            # In both cases, we want to upgrade it. 
            # Note: We can only upgrade if we have the plain-text. 
            # If it's already SHA-256, we can't get plain-text back, 
            # but we can wrap it or just wait for next login.
            # Best approach: If it's short (plain-text), upgrade it now.
            if len(stored_p) != 64 and len(stored_p) != 129: # 129 is salt:hash approx
                new_h = _hash_password(stored_p)
                cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_h, u['id']))
    
    conn.commit()
    conn.close()

# --- Users API ---
def verify_user(username, password):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    
    if user:
        stored_password = user['password']
        if ":" in stored_password:
            # Modern Salted Scrypt format
            try:
                salt, h = stored_password.split(":")
                hashed_input = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
                if hashed_input == h:
                    return dict(user)
            except Exception:
                pass
        else:
            # Legacy SHA-256 format (for backward compatibility)
            hashed_input = hashlib.sha256(password.encode()).hexdigest()
            if hashed_input == stored_password:
                # JIT Upgrade to salted scrypt
                new_h = _hash_password(password)
                conn = get_connection()
                conn.execute("UPDATE users SET password = ? WHERE id = ?", (new_h, user['id']))
                conn.commit()
                conn.close()
                return dict(user)
    return None

def get_all_users():
    conn = get_connection()
    users = [dict(row) for row in conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()]
    conn.close()
    return users

def add_user(data):
    try:
        if "password" in data:
            data["password"] = _hash_password(data["password"])
        conn = get_connection()
        keys = data.keys()
        columns = ', '.join(keys)
        placeholders = ', '.join(['?' for _ in keys])
        sql = f"INSERT INTO users ({columns}) VALUES ({placeholders})"
        cursor = conn.cursor()
        cursor.execute(sql, list(data.values()))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def update_user(user_id, data):
    if "password" in data and data["password"]:
        data["password"] = _hash_password(data["password"])
    elif "password" in data:
        # Don't update password if it's empty string
        del data["password"]
    
    conn = get_connection()
    keys = data.keys()
    set_clause = ', '.join([f"{k} = ?" for k in keys])
    sql = f"UPDATE users SET {set_clause} WHERE id = ?"
    conn.execute(sql, list(data.values()) + [user_id])
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- Sales Report API ---
def get_all_sales():
    conn = get_connection()
    sales = [dict(row) for row in conn.execute("SELECT * FROM sales_report ORDER BY month_year DESC, category ASC").fetchall()]
    conn.close()
    return sales

def add_sale(data):
    conn = get_connection()
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO sales_report ({columns}) VALUES ({placeholders})"
    cursor = conn.cursor()
    cursor.execute(sql, list(data.values()))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def delete_sale(sale_id):
    conn = get_connection()
    conn.execute("DELETE FROM sales_report WHERE id = ?", (sale_id,))
    conn.commit()
    conn.close()

# --- Recurring Clients API ---
def get_recurring_clients():
    conn = get_connection()
    clients = [dict(row) for row in conn.execute("SELECT * FROM recurring_clients ORDER BY client ASC").fetchall()]
    conn.close()
    return clients

def add_recurring_client(data):
    conn = get_connection()
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO recurring_clients ({columns}) VALUES ({placeholders})"
    cursor = conn.cursor()
    cursor.execute(sql, list(data.values()))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def delete_recurring_client(client_id):
    conn = get_connection()
    conn.execute("DELETE FROM recurring_clients WHERE id = ?", (client_id,))
    conn.commit()
    conn.close()

# --- Leads API ---
def get_all_leads():
    conn = get_connection()
    leads = [dict(row) for row in conn.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()]
    conn.close()
    return leads

def add_lead(data):
    conn = get_connection()
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO leads ({columns}) VALUES ({placeholders})"
    cursor = conn.cursor()
    cursor.execute(sql, list(data.values()))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_lead(lead_id, data):
    conn = get_connection()
    keys = data.keys()
    set_clause = ', '.join([f"{k} = ?" for k in keys])
    sql = f"UPDATE leads SET {set_clause} WHERE id = ?"
    conn.execute(sql, list(data.values()) + [lead_id])
    conn.commit()
    conn.close()

def delete_lead(lead_id):
    conn = get_connection()
    conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
    conn.execute("DELETE FROM tasks WHERE lead_id = ?", (lead_id,))
    conn.commit()
    conn.close()

# --- Tasks API ---
def get_all_tasks():
    conn = get_connection()
    tasks = [dict(row) for row in conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()]
    conn.close()
    return tasks

def add_task(data):
    conn = get_connection()
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO tasks ({columns}) VALUES ({placeholders})"
    cursor = conn.cursor()
    cursor.execute(sql, list(data.values()))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_task(task_id, data):
    conn = get_connection()
    keys = data.keys()
    set_clause = ', '.join([f"{k} = ?" for k in keys])
    sql = f"UPDATE tasks SET {set_clause} WHERE id = ?"
    conn.execute(sql, list(data.values()) + [task_id])
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = get_connection()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

# --- Settings API ---
def get_settings(defaults):
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    
    settings = defaults.copy()
    for row in rows:
        key, val = row['key'], row['value']
        # Handle boolean/int types stored as strings
        if val.lower() == 'true': val = True
        elif val.lower() == 'false': val = False
        elif val.isdigit(): val = int(val)
        settings[key] = val
    return settings

def save_settings(settings_dict):
    conn = get_connection()
    for key, val in settings_dict.items():
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(val)))
    conn.commit()
    conn.close()

# --- Logs API ---
def add_log(emails_sent, tasks_checked, leads_checked):
    conn = get_connection()
    conn.execute("INSERT INTO reminder_logs (timestamp, emails_sent, tasks_checked, leads_checked) VALUES (?, ?, ?, ?)",
                 (str(datetime.now()), emails_sent, tasks_checked, leads_checked))
    conn.commit()
    conn.close()

def get_logs(limit=30):
    conn = get_connection()
    logs = [dict(row) for row in conn.execute("SELECT * FROM reminder_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
    conn.close()
    return logs

# --- Email Templates API ---
def get_all_templates():
    conn = get_connection()
    templates = [dict(row) for row in conn.execute("SELECT * FROM email_templates ORDER BY id DESC").fetchall()]
    conn.close()
    return templates

def add_template(data):
    conn = get_connection()
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO email_templates ({columns}) VALUES ({placeholders})"
    cursor = conn.cursor()
    cursor.execute(sql, list(data.values()))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def delete_template(template_id):
    conn = get_connection()
    conn.execute("DELETE FROM email_templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()

def update_template(template_id, data):
    conn = get_connection()
    keys = data.keys()
    set_clause = ', '.join([f"{k} = ?" for k in keys])
    sql = f"UPDATE email_templates SET {set_clause} WHERE id = ?"
    conn.execute(sql, list(data.values()) + [template_id])
    conn.commit()
    conn.close()

# --- Campaigns API ---
def get_all_campaigns():
    conn = get_connection()
    campaigns = [dict(row) for row in conn.execute("SELECT * FROM campaigns ORDER BY id DESC").fetchall()]
    conn.close()
    return campaigns

def add_campaign(data):
    conn = get_connection()
    keys = data.keys()
    columns = ', '.join(keys)
    placeholders = ', '.join(['?' for _ in keys])
    sql = f"INSERT INTO campaigns ({columns}) VALUES ({placeholders})"
    cursor = conn.cursor()
    cursor.execute(sql, list(data.values()))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_campaign_stats(campaign_id, sent, failed):
    conn = get_connection()
    conn.execute("UPDATE campaigns SET stats_sent = ?, stats_failed = ?, status = 'Completed' WHERE id = ?", (sent, failed, campaign_id))
    conn.commit()
    conn.close()

def add_campaign_log(campaign_id, email, status, error_message=""):
    conn = get_connection()
    conn.execute("INSERT INTO campaign_logs (campaign_id, email, status, error_message, sent_at) VALUES (?, ?, ?, ?, ?)",
                 (campaign_id, email, status, error_message, str(datetime.now())))
    conn.commit()
    conn.close()

def get_campaign_logs(campaign_id):
    conn = get_connection()
    logs = [dict(row) for row in conn.execute("SELECT * FROM campaign_logs WHERE campaign_id = ?", (campaign_id,)).fetchall()]
    conn.close()
    return logs
