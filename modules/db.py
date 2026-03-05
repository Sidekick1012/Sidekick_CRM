psycopg2.errors.UniqueViolation: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
Traceback:
File "/mount/src/sidekick_crm/app.py", line 1562, in <module>
    db.add_task(task_data)
    ~~~~~~~~~~~^^^^^^^^^^^
File "/mount/src/sidekick_crm/modules/db.py", line 443, in add_task
    db_call(sql, list(data.values()))
    ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/mount/src/sidekick_crm/modules/db.py", line 304, in db_call
    cursor.execute(query, params)
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/psycopg2/extras.py", line 236, in execute
    return super().execute(query, vars)
           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^    # Adjust placeholders for Postgres if needed
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
    db_call("DELETE FROM leads WHERE id = ?", (lead_id,))
    db_call("DELETE FROM tasks WHERE lead_id = ?", (lead_id,))
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

@st.cache_data
def get_campaign_logs(campaign_id):
    return db_call("SELECT * FROM campaign_logs WHERE campaign_id = ?", (campaign_id,))
