#!/usr/bin/env python3
"""Quick check of simulation_state columns"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn_params = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'urban_sim'),
    'user': os.getenv('DB_USER', 'simulator_user'),
    'password': os.getenv('DB_PASSWORD', 'UrbanSim2026!')
}

try:
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()
    
    # Get all columns from simulation_state
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'simulation_state'
        ORDER BY ordinal_position
    """)
    
    print("\n" + "=" * 60)
    print("COLUMNS IN simulation_state TABLE:")
    print("=" * 60)
    for row in cursor.fetchall():
        print(f"  {row[0]:<30} {row[1]}")
    
    # Sample one row
    print("\n" + "=" * 60)
    print("SAMPLE ROW:")
    print("=" * 60)
    cursor.execute("SELECT * FROM simulation_state LIMIT 1")
    row = cursor.fetchone()
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'simulation_state' ORDER BY ordinal_position")
    cols = [c[0] for c in cursor.fetchall()]
    
    if row:
        for col_name, val in zip(cols, row):
            print(f"  {col_name}: {val}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
