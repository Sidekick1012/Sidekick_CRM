
import streamlit as st
from modules import db
import os

# Mock streamlit secrets if needed for local run
if not hasattr(st, "secrets"):
    st.secrets = {}

print("Connecting to database...")
try:
    # Ensure tables exist
    db.init_db()
    
    print("Generating 2 years of dummy data (2025-2026)...")
    success = db.generate_dummy_data()
    
    if success:
        print("SUCCESS: 24 months of operational data injected.")
    else:
        print("FAILED: Data generation routine returned False.")
except Exception as e:
    print(f"ERROR: {e}")
