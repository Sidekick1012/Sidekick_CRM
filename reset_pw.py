import sqlite3
import hashlib
import os
import secrets
from datetime import datetime

def _hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f"{salt}:{h}"

def reset_admin():
    new_hashed_password = _hash_password("admin123")
    
    # 1. Reset SQLite
    db_path = "database/crm_database.db"
    if os.path.exists(db_path):
        print(f"Resetting admin in SQLite: {db_path}...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = ? WHERE username = 'admin'", (new_hashed_password,))
        if cursor.rowcount == 0:
            cursor.execute("INSERT INTO users (username, password, role, allowed_pages, created_at) VALUES (?, ?, ?, ?, ?)",
                           ("admin", new_hashed_password, "Admin", "all", str(datetime.now())))
        conn.commit()
        conn.close()
        print("SQLite reset done.")

    # 2. Reset Postgres
    url = "postgresql://postgres.fqxhphafoqcgbdwtannq:p6yaJZg7nhichSLo@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
    print("\nResetting admin in Postgres...")
    try:
        import psycopg2
        conn = psycopg2.connect(url)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = %s WHERE username = 'admin'", (new_hashed_password,))
        if cursor.rowcount == 0:
            cursor.execute("INSERT INTO users (username, password, role, allowed_pages, created_at) VALUES (%s, %s, %s, %s, %s)",
                           ("admin", new_hashed_password, "Admin", "all", str(datetime.now())))
        conn.commit()
        conn.close()
        print("Postgres reset done.")
    except Exception as e:
        print(f"Error resetting Postgres: {e}")

if __name__ == "__main__":
    reset_admin()
