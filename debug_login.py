import sqlite3
import hashlib
import os
import secrets

def _hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f"{salt}:{h}"

def verify_password(password, stored_password):
    if ":" not in stored_password:
        return False
    salt, h = stored_password.split(":")
    hashed_input = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return hashed_input == h

def check_sqlite():
    db_path = "database/crm_database.db"
    if not os.path.exists(db_path):
        print("SQLite database not found.")
        return
    
    print(f"--- SQLite: {db_path} ---")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        for row in rows:
            print(f"User: {row['username']}, Role: {row['role']}")
            is_correct = verify_password("admin123", row['password'])
            print(f"  Password matches 'admin123': {is_correct}")
    except Exception as e:
        print(f"Error reading SQLite: {e}")
    finally:
        conn.close()

def check_postgres():
    # Credentials from secrets.toml
    url = "postgresql://postgres.fqxhphafoqcgbdwtannq:p6yaJZg7nhichSLo@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
    print("\n--- Postgres: Supabase ---")
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        for row in rows:
            print(f"User: {row['username']}, Role: {row['role']}")
            is_correct = verify_password("admin123", row['password'])
            print(f"  Password matches 'admin123': {is_correct}")
        conn.close()
    except Exception as e:
        print(f"Error reading Postgres: {e}")

if __name__ == "__main__":
    check_sqlite()
    check_postgres()
