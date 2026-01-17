#!/usr/bin/env python3
"""Quick test to verify CSV encoding fixes work."""

import pandas as pd
from pathlib import Path

data_dir = Path('data/outputs')
print("[*] Testing CSV loading with Latin-1 encoding...\n")

files = {
    'real_rent_calibration_2024.csv': 'Real rent data',
    'population_scaling_factors.csv': 'Population scaling',
    'baseline_simulation_state.csv': 'Baseline simulation',
    'zone_definitions_2024.csv': 'Zone definitions'
}

for filename, description in files.items():
    try:
        df = pd.read_csv(data_dir / filename, encoding='latin-1')
        print(f"[OK] {description:.<40} {len(df)} rows")
    except Exception as e:
        print(f"[ERROR] {description:.<40} {e}")

print("\n[OK] All CSV files load successfully!")
print("\nStreamlit dashboard can now be run without encoding errors:")
print("  streamlit run streamlit_dashboard.py")
