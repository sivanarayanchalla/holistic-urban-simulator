#!/usr/bin/env python3
"""Comprehensive analysis of 3-city simulation results."""
import pandas as pd
from src.database.db_config import db_config
from sqlalchemy import text

print('\n' + '='*70)
print('[*] 3-CITY COMPARISON ANALYSIS')
print('='*70)

with db_config.engine.connect() as conn:
    # 1. Simulation runs overview
    print('\n[OK] Simulation Runs by City:')
    query = text('''
        SELECT 
            city_name,
            run_id,
            status,
            created_at
        FROM simulation_run
        WHERE city_name IN ('leipzig', 'berlin', 'munich')
        ORDER BY city_name, created_at DESC
    ''')
    runs = pd.read_sql(query, conn)
    print(runs.to_string(index=False))
    
    # 2. Basic metrics from final timestep
    print('\n\n[OK] Population & Rent Metrics at Timestep 50:')
    query = text('''
        SELECT 
            sr.city_name,
            ROUND(AVG(ss.population)::numeric, 0) as avg_pop,
            MIN(ss.population)::integer as min_pop,
            MAX(ss.population)::integer as max_pop,
            ROUND(AVG(ss.avg_rent_euro)::numeric, 2) as avg_rent_eur,
            COUNT(*) as num_cells
        FROM simulation_state ss
        JOIN simulation_run sr ON ss.run_id = sr.run_id
        WHERE sr.city_name IN ('leipzig', 'berlin', 'munich')
        AND ss.timestep = 50
        GROUP BY sr.city_name
        ORDER BY avg_rent_eur DESC
    ''')
    metrics = pd.read_sql(query, conn)
    print(metrics.to_string(index=False))
    
    # 3. Employment & Commerce
    print('\n\n[OK] Employment & Commerce Metrics:')
    query = text('''
        SELECT 
            sr.city_name,
            ROUND(AVG(ss.employment)::numeric, 3) as avg_employment,
            ROUND(AVG(ss.commercial_activity)::numeric, 3) as avg_commercial,
            ROUND(AVG(ss.business_vitality)::numeric, 3) as avg_vitality
        FROM simulation_state ss
        JOIN simulation_run sr ON ss.run_id = sr.run_id
        WHERE sr.city_name IN ('leipzig', 'berlin', 'munich')
        AND ss.timestep = 50
        GROUP BY sr.city_name
        ORDER BY sr.city_name
    ''')
    try:
        metrics_emp = pd.read_sql(query, conn)
        print(metrics_emp.to_string(index=False))
    except Exception as e:
        print(f'[WARN] Employment columns not available: {str(e)[:80]}')

# New connection for timeline to avoid transaction errors
with db_config.engine.connect() as conn2:
    # 4. Timeline analysis - how metrics evolved
    print('\n\n[OK] Population Evolution Over Time:')
    query = text('''
        SELECT 
            sr.city_name,
            ss.timestep,
            ROUND(AVG(ss.population)::numeric, 0) as avg_pop
        FROM simulation_state ss
        JOIN simulation_run sr ON ss.run_id = sr.run_id
        WHERE sr.city_name IN ('leipzig', 'berlin', 'munich')
        AND ss.timestep IN (0, 10, 20, 30, 40, 50)
        GROUP BY sr.city_name, ss.timestep
        ORDER BY sr.city_name, ss.timestep
    ''')
    try:
        timeline = pd.read_sql(query, conn2)
        for city in ['berlin', 'leipzig', 'munich']:
            city_data = timeline[timeline['city_name'] == city]
            if not city_data.empty:
                print(f'\n  {city.upper()}:')
                for _, row in city_data.iterrows():
                    print(f'    Timestep {int(row["timestep"]):2d}: {int(row["avg_pop"]):7} pop')
    except Exception as e:
        print(f'[WARN] Timeline analysis failed: {str(e)[:80]}')

print('\n' + '='*70)
print('[OK] Analysis complete!')
print('\n[NEXT] View visualizations in: data/outputs/visualizations/')
print('  - multi_city_comparison.html')
print('  - city_performance_matrix.html')  
print('  - inequality_comparison.html')
print('='*70 + '\n')
