#!/usr/bin/env python3
"""Verify which columns actually exist in simulation_state"""

from src.database.db_config import engine
from sqlalchemy import inspect, text

# Get inspector
inspector = inspect(engine)

print("=" * 60)
print("ALL TABLES IN DATABASE:")
print("=" * 60)
for table in inspector.get_table_names():
    print(f"  - {table}")

print("\n" + "=" * 60)
print("SIMULATION_STATE COLUMNS:")
print("=" * 60)
try:
    cols = inspector.get_columns('simulation_state')
    for col in cols:
        print(f"  {col['name']}: {col['type']}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 60)
print("SAMPLE DATA FROM simulation_state:")
print("=" * 60)
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM simulation_state LIMIT 1"))
        row = result.fetchone()
        if row:
            print("Column names:", list(row.keys()))
            print("Sample values:", dict(row))
        else:
            print("No data found")
except Exception as e:
    print(f"ERROR: {e}")
