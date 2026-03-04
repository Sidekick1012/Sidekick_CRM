import sqlite3
import hashlib
import os
import streamlit as st
from modules import db

def check_users():
    db.init_db() # Ensure db is initialized
    users = db.get_all_users()
    print(f"Database Type: {db.DB_TYPE}")
    print(f"Active connection URL/Path: {db.DB_URL}")
    print("\nUsers found:")
    for user in users:
        print(f"ID: {user['id']}, Username: {user['username']}, Role: {user['role']}")
        # We don't print the actual hash for security, but we can check if it matches admin123
        stored_pw = user['password']
        salt, h = stored_pw.split(":")
        test_h = hashlib.scrypt("admin123".encode(), salt=salt.encode(), n=16383 if '16383' in stored_pw else 16384, r=8, p=1).hex()
        # Note: I used 16384 in code, let's verify if the stored one matches the current hashing logic
        current_h = db._hash_password("admin123").split(":")[1]
        
        match = (h == current_h) # This is not quite right because salt differs, but we can check if we can verify it
        verified = db.verify_user(user['username'], "admin123")
        print(f"  - Password matches 'admin123' via verify_user: {'YES' if verified else 'NO'}")

if __name__ == "__main__":
    check_users()
