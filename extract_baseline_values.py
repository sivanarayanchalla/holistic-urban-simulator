#!/usr/bin/env python3
"""Extract baseline values and grid metrics for Phase 1 calibration audit."""

import pandas as pd
import csv
from datetime import datetime
from src.database.db_config import db_config
from sqlalchemy import text

print('\n' + '='*80)
print('[PHASE 1 AUDIT] Extract Baseline Values & Grid Metrics')
print('='*80)

# ============================================================================
# SECTION 1: Grid Metrics Overview
# ============================================================================
print('\n[1] GRID METRICS BY CITY')
print('-' * 80)

with db_config.engine.connect() as conn:
    # Get grid dimensions and coverage
    query = text('''
        SELECT 
            'Leipzig' as city,
            COUNT(*) as grid_cells,
            ROUND(AVG(ST_Area(geometry) / 1000000.0)::numeric, 6) as avg_cell_area_sqkm,
            ROUND((SUM(ST_Area(geometry)) / 1000000.0)::numeric, 2) as total_area_sqkm,
            ROUND(AVG(resolution_meters)::numeric, 2) as avg_resolution_m
        FROM spatial_grid
        LIMIT 1
    ''')
    
    try:
        result = pd.read_sql(query, conn)
        print("\nLeipzig Grid:")
        print(result.to_string(index=False))
    except Exception as e:
        print(f"[WARN] Could not query grid metrics: {e}")

# ============================================================================
# SECTION 2: Simulation Runs Overview
# ============================================================================
print('\n\n[2] RECENT SIMULATION RUNS')
print('-' * 80)

with db_config.engine.connect() as conn:
    query = text('''
        SELECT 
            run_id,
            city_name,
            total_timesteps,
            status,
            created_at
        FROM simulation_run
        ORDER BY created_at DESC
        LIMIT 10
    ''')
    
    runs = pd.read_sql(query, conn)
    if not runs.empty:
        print(runs.to_string(index=False))
    else:
        print("[INFO] No simulation runs found in database")

# ============================================================================
# SECTION 3: Initial State (Timestep 0)
# ============================================================================
print('\n\n[3] BASELINE STATE AT TIMESTEP 0')
print('-' * 80)

with db_config.engine.connect() as conn:
    query = text('''
        SELECT 
            sr.city_name,
            COUNT(DISTINCT ss.grid_id) as num_cells,
            ROUND(AVG(ss.population)::numeric, 1) as avg_population,
            ROUND(MIN(ss.population)::numeric, 1) as min_population,
            ROUND(MAX(ss.population)::numeric, 1) as max_population,
            ROUND(STDDEV(ss.population)::numeric, 1) as stddev_population,
            ROUND(AVG(ss.avg_rent_euro)::numeric, 2) as avg_rent_eur,
            ROUND(MIN(ss.avg_rent_euro)::numeric, 2) as min_rent_eur,
            ROUND(MAX(ss.avg_rent_euro)::numeric, 2) as max_rent_eur,
            ROUND(AVG(ss.housing_units)::numeric, 1) as avg_housing_units,
            ROUND(AVG(ss.employment)::numeric, 1) as avg_employment
        FROM simulation_state ss
        JOIN simulation_run sr ON ss.run_id = sr.run_id
        WHERE ss.timestep = 0
        GROUP BY sr.city_name
        ORDER BY sr.city_name
    ''')
    
    try:
        baseline = pd.read_sql(query, conn)
        if not baseline.empty:
            print("\nTimestep 0 Baseline Metrics:")
            print(baseline.to_string(index=False))
        else:
            print("[INFO] No timestep 0 data found (simulations may have started at timestep 1)")
    except Exception as e:
        print(f"[WARN] Could not retrieve timestep 0 data: {e}")

# ============================================================================
# SECTION 4: Final State (Timestep 50)
# ============================================================================
print('\n\n[4] FINAL STATE AT TIMESTEP 50')
print('-' * 80)

with db_config.engine.connect() as conn:
    query = text('''
        SELECT 
            sr.city_name,
            COUNT(DISTINCT ss.grid_id) as num_cells,
            ROUND(AVG(ss.population)::numeric, 1) as avg_population,
            ROUND(MIN(ss.population)::numeric, 1) as min_population,
            ROUND(MAX(ss.population)::numeric, 1) as max_population,
            ROUND(STDDEV(ss.population)::numeric, 1) as stddev_population,
            ROUND(AVG(ss.avg_rent_euro)::numeric, 2) as avg_rent_eur,
            ROUND(MIN(ss.avg_rent_euro)::numeric, 2) as min_rent_eur,
            ROUND(MAX(ss.avg_rent_euro)::numeric, 2) as max_rent_eur,
            ROUND(AVG(ss.housing_units)::numeric, 1) as avg_housing_units,
            ROUND(AVG(ss.employment)::numeric, 1) as avg_employment
        FROM simulation_state ss
        JOIN simulation_run sr ON ss.run_id = sr.run_id
        WHERE ss.timestep = 50
        GROUP BY sr.city_name
        ORDER BY sr.city_name
    ''')
    
    try:
        final = pd.read_sql(query, conn)
        if not final.empty:
            print("\nTimestep 50 Final Metrics:")
            print(final.to_string(index=False))
    except Exception as e:
        print(f"[WARN] Could not retrieve timestep 50 data: {e}")

# ============================================================================
# SECTION 5: Population & Rent Evolution
# ============================================================================
print('\n\n[5] METRIC EVOLUTION (Timesteps 0→10→20→30→40→50)')
print('-' * 80)

with db_config.engine.connect() as conn:
    query = text('''
        SELECT 
            sr.city_name,
            ss.timestep,
            ROUND(AVG(ss.population)::numeric, 1) as avg_pop,
            ROUND(AVG(ss.avg_rent_euro)::numeric, 2) as avg_rent_eur,
            ROUND(AVG(ss.employment)::numeric, 1) as avg_employment,
            ROUND(AVG(ss.traffic_congestion)::numeric, 3) as avg_congestion
        FROM simulation_state ss
        JOIN simulation_run sr ON ss.run_id = sr.run_id
        WHERE ss.timestep IN (0, 10, 20, 30, 40, 50)
        GROUP BY sr.city_name, ss.timestep
        ORDER BY sr.city_name, ss.timestep
    ''')
    
    try:
        evolution = pd.read_sql(query, conn)
        if not evolution.empty:
            for city in evolution['city_name'].unique():
                city_data = evolution[evolution['city_name'] == city]
                print(f"\n{city.upper()}:")
                print(city_data.to_string(index=False))
    except Exception as e:
        print(f"[WARN] Could not retrieve evolution data: {e}")

# ============================================================================
# SECTION 6: Displacement Risk & Green Space
# ============================================================================
print('\n\n[6] SOCIAL & ENVIRONMENTAL METRICS AT TIMESTEP 50')
print('-' * 80)

with db_config.engine.connect() as conn:
    query = text('''
        SELECT 
            sr.city_name,
            ROUND(AVG(ss.displacement_risk)::numeric, 4) as avg_displacement_risk,
            ROUND(MAX(ss.displacement_risk)::numeric, 4) as max_displacement_risk,
            ROUND(AVG(ss.green_space_ratio)::numeric, 4) as avg_green_space,
            ROUND(AVG(ss.air_quality_index)::numeric, 2) as avg_air_quality,
            ROUND(AVG(ss.safety_score)::numeric, 4) as avg_safety,
            ROUND(AVG(ss.traffic_congestion)::numeric, 4) as avg_congestion
        FROM simulation_state ss
        JOIN simulation_run sr ON ss.run_id = sr.run_id
        WHERE ss.timestep = 50
        GROUP BY sr.city_name
    ''')
    
    try:
        social = pd.read_sql(query, conn)
        if not social.empty:
            print("\nSocial & Environmental Metrics (Timestep 50):")
            print(social.to_string(index=False))
    except Exception as e:
        print(f"[WARN] Could not retrieve social metrics: {e}")

# ============================================================================
# SECTION 7: Housing & Affordability
# ============================================================================
print('\n\n[7] HOUSING & AFFORDABILITY AT TIMESTEP 50')
print('-' * 80)

with db_config.engine.connect() as conn:
    query = text('''
        SELECT 
            sr.city_name,
            ROUND(AVG(ss.housing_units)::numeric, 1) as avg_housing_units,
            ROUND(AVG(ss.population / NULLIF(ss.housing_units, 0))::numeric, 2) as persons_per_housing_unit,
            ROUND(COUNT(CASE WHEN ss.avg_rent_euro > 1500 THEN 1 END)::numeric / COUNT(*), 4) as pct_cells_high_rent,
            ROUND(COUNT(CASE WHEN ss.displacement_risk > 0.3 THEN 1 END)::numeric / COUNT(*), 4) as pct_cells_high_displacement
        FROM simulation_state ss
        JOIN simulation_run sr ON ss.run_id = sr.run_id
        WHERE ss.timestep = 50
        GROUP BY sr.city_name
    ''')
    
    try:
        housing = pd.read_sql(query, conn)
        if not housing.empty:
            print("\nHousing & Affordability Metrics (Timestep 50):")
            print(housing.to_string(index=False))
    except Exception as e:
        print(f"[WARN] Could not retrieve housing metrics: {e}")

# ============================================================================
# SECTION 8: Export Baseline CSV for Analysis
# ============================================================================
print('\n\n[8] EXPORTING BASELINE DATA TO CSV')
print('-' * 80)

try:
    with db_config.engine.connect() as conn:
        # Export all states for all cities and timesteps
        query = text('''
            SELECT 
                sr.run_id,
                sr.city_name,
                ss.timestep,
                ss.grid_id,
                ss.population,
                ss.avg_rent_euro,
                ss.housing_units,
                ss.employment,
                ss.traffic_congestion,
                ss.safety_score,
                ss.displacement_risk,
                ss.green_space_ratio,
                ss.air_quality_index,
                ss.public_transit_accessibility,
                ss.commercial_vitality
            FROM simulation_state ss
            JOIN simulation_run sr ON ss.run_id = sr.run_id
            ORDER BY sr.city_name, ss.timestep, ss.grid_id
        ''')
        
        baseline_data = pd.read_sql(query, conn)
        
        if not baseline_data.empty:
            output_file = 'data/outputs/baseline_simulation_state.csv'
            baseline_data.to_csv(output_file, index=False)
            print(f"\n✅ Exported {len(baseline_data)} rows to {output_file}")
            print(f"   Cities: {', '.join(baseline_data['city_name'].unique())}")
            print(f"   Timesteps: 0-50")
            print(f"   Grid cells per city: ~{len(baseline_data[baseline_data['timestep']==0]) // 3}")
        else:
            print("[INFO] No baseline data available to export")
            
except Exception as e:
    print(f"[WARN] Could not export baseline data: {e}")

# ============================================================================
# SECTION 9: Summary & Next Steps
# ============================================================================
print('\n\n' + '='*80)
print('[PHASE 1 AUDIT] Summary & Key Findings')
print('='*80)

print("""
KEY QUESTIONS ANSWERED BY THIS AUDIT:
1. ✓ How many grid cells per city? (See Section 1)
2. ✓ What's initial population and rent per cell? (See Section 3)
3. ✓ How do metrics evolve from timestep 0→50? (See Section 5)
4. ✓ What are current displacement risk and affordability levels? (Sections 6-7)

CRITICAL DISCREPANCIES TO INVESTIGATE:
- Initial rent (€500 in code) vs final rent (€2,940+ in outputs)
  → Possible causes: (a) Different initialization in SimulationManager,
                      (b) Rent inflation formula accumulating,
                      (c) Different scaling per city
  
- Population unit unclear: Does 1,000 per cell = 1 person, 1 household, or aggregate?
  → Need to: (a) Check real census data for cities,
             (b) Divide simulation output by real population,
             (c) Calculate scaling factor

NEXT STEPS (Phase 1 continuation):
1. Review CRITICAL_FINDINGS_DATA_CALIBRATION.md for identified issues
2. Run: python extract_baseline_values.py (this script) to generate baseline_simulation_state.csv
3. Compare simulation output rent with real 2024 data from Immobilienscout24
4. Determine population scaling factor from census data
5. Create mapping of grid cells to real Berlin/Leipzig/Munich neighborhoods
6. Document all findings in PHASE_1_AUDIT_REPORT.md

See: data/outputs/baseline_simulation_state.csv for detailed metrics
""")

print('='*80 + '\n')
