import os
import sqlite3
import streamlit as st
import sys

# Add the project directory to sys.path so we can import modules
sys.path.append(os.getcwd())

from modules import db

def check_postgres_sequences():
    if db.DB_TYPE != "postgres":
        print("Not using Postgres. Skipping sequence check.")
        return

    print("Checking Postgres sequences...")
    tables = ['leads', 'tasks', 'email_templates', 'campaigns', 'campaign_logs', 'sales_report', 'recurring_clients', 'users']
    
    for table in tables:
        try:
            # Get the max ID and the current sequence value
            res = db.db_call(f"SELECT MAX(id) as max_id FROM {table}", fetch="one")
            max_id = res['max_id'] if res and res['max_id'] is not None else 0
            
            # Reset sequence if max_id is greater than or equal to next value
            # Standard sequence name is table_id_seq
            seq_name = f"{table}_id_seq"
            
            print(f"Table: {table}, Max ID: {max_id}, Attempting to reset sequence {seq_name}")
            
            # Fix sequence
            db.db_call(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)")
            print(f"Successfully reset sequence for {table}")
        except Exception as e:
            print(f"Could not reset sequence for {table}: {e}")

if __name__ == "__main__":
    check_postgres_sequences()
