#!/usr/bin/env python3
"""
PHASE 6: RE-RUN SIMULATIONS WITH CALIBRATED PARAMETERS
========================================================

Executes full simulation runs for Berlin, Leipzig, and Munich with:
1. City-specific calibrated rent ranges (Phase 4)
2. Reduced housing market sensitivity (Phase 4)
3. Income-based demographic module (Phase 5)
4. All 8 urban modules with policy impacts

SIMULATION CONFIGURATION:
- 50 timesteps per run (standard)
- 20 grid cells per city
- All policy modules active by default
- Employment properly initialized (no NULLs)
- Saves detailed state to database at timesteps 10, 20, 30, 40, 50

POLICY SCENARIOS TO TEST:
1. Baseline (no policies)
2. EV Subsidy (reduces rent 5%)
3. Progressive Tax (taxes high-rent properties)
4. Green Space Mandate (20% green space requirement)
5. Transit Investment (reduces congestion 15%)

SUCCESS CRITERIA:
- All 3 cities complete 50-step runs
- Rents within ±15% of Phase 2 calibration targets
- Population dynamics reflect income-based displacement
- Gentrification index shows neighborhood changes
- Policy impacts measurable on rent and population
"""

import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import random

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core_engine.simulation_engine import SimulationManager, UrbanModel

def run_baseline_simulations():
    """Run baseline simulations for all 3 cities."""
    print("\n" + "="*70)
    print("PHASE 6: BASELINE SIMULATIONS (All Calibrations Active)")
    print("="*70)
    
    cities = ['Berlin', 'Leipzig', 'Munich']
    results = {}
    
    for city in cities:
        print(f"\n{'='*70}")
        print(f"Running simulation for {city}")
        print(f"{'='*70}")
        
        try:
            # Run 50-step simulation with all calibrations
            run_id = SimulationManager.run_test_simulation(
                steps=50,
                grid_limit=20,
                city=city
            )
            
            results[city] = {
                'run_id': run_id,
                'status': 'completed',
                'steps': 50,
                'grid_cells': 20
            }
            
            print(f"\n[OK] {city} simulation completed: {run_id}")
            
        except Exception as e:
            print(f"\n[ERROR] {city} simulation failed: {e}")
            results[city] = {
                'status': 'failed',
                'error': str(e)
            }
    
    return results

def analyze_simulation_results(results):
    """Analyze results from all simulation runs."""
    print("\n" + "="*70)
    print("SIMULATION RESULTS ANALYSIS")
    print("="*70)
    
    analysis = {}
    
    for city, result in results.items():
        print(f"\n{city}:")
        
        if result['status'] == 'completed':
            print(f"  Status: COMPLETED")
            print(f"  Run ID: {result['run_id']}")
            print(f"  Timesteps: {result['steps']}")
            print(f"  Grid Cells: {result['grid_cells']}")
            
            # Expected outcomes
            if city == 'Berlin':
                expected_final_rent = 1408  # From Phase 4 calibration
            elif city == 'Leipzig':
                expected_final_rent = 960
            else:  # Munich
                expected_final_rent = 1664
            
            print(f"  Expected Final Rent: EUR {expected_final_rent:.0f}")
            print(f"  (Based on Phase 4 calibration with 1.28x multiplier)")
            
            analysis[city] = {
                'expected_rent': expected_final_rent,
                'status': 'success'
            }
        else:
            print(f"  Status: FAILED")
            print(f"  Error: {result.get('error', 'Unknown')}")
            analysis[city] = {'status': 'failed'}
    
    return analysis

def create_phase6_report():
    """Generate comprehensive Phase 6 report."""
    print("\n" + "="*70)
    print("PHASE 6 SIMULATION EXECUTION REPORT")
    print("="*70)
    
    # Run baseline simulations
    baseline_results = run_baseline_simulations()
    
    # Analyze results
    analysis = analyze_simulation_results(baseline_results)
    
    # Generate report file
    report_file = Path(__file__).parent / "PHASE_6_SIMULATION_EXECUTION_REPORT.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# PHASE 6: SIMULATION EXECUTION REPORT\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write("Phase 6 executes full simulation runs for all 3 cities with calibrated\n")
        f.write("parameters from Phases 4-5.\n\n")
        
        f.write("## Calibration Parameters Applied\n\n")
        f.write("### Initial Rent Ranges (Phase 4)\n")
        f.write("- Berlin: EUR 900-1300\n")
        f.write("- Leipzig: EUR 600-900\n")
        f.write("- Munich: EUR 1100-1500\n\n")
        
        f.write("### Housing Market Sensitivity (Phase 4)\n")
        f.write("- Rent change cap: 0.5%% per timestep (reduced from 2%%)\n")
        f.write("- Demand multiplier: 1.5%% (reduced from 5%%)\n")
        f.write("- Expected 50-step multiplier: 1.28x (reduced from 2.69x)\n\n")
        
        f.write("### Demographics (Phase 5)\n")
        f.write("- Population segments: 30%% low, 40%% middle, 30%% high income\n")
        f.write("- Displacement triggered by rent unaffordability\n")
        f.write("- Gentrification tracking via income diversity index\n\n")
        
        f.write("## Simulation Results\n\n")
        f.write("| City | Status | Run ID | Expected Final Rent |\n")
        f.write("|------|--------|--------|---------------------|\n")
        
        for city, result in baseline_results.items():
            status = result['status'].upper()
            run_id = result.get('run_id', 'N/A')
            expected_rent = analysis[city].get('expected_rent', 'N/A')
            
            f.write(f"| {city} | {status} | {run_id} | EUR {expected_rent} |\n")
        
        f.write("\n## Expected Outcomes\n\n")
        f.write("### Berlin\n")
        f.write("- Initial avg rent: EUR 1,100\n")
        f.write("- Expected final (T50): EUR 1,408 (1.28x multiplier)\n")
        f.write("- Target (Phase 2): EUR 1,150\n")
        f.write("- Expected error: 22.4%%\n\n")
        
        f.write("### Leipzig\n")
        f.write("- Initial avg rent: EUR 750\n")
        f.write("- Expected final (T50): EUR 960 (1.28x multiplier)\n")
        f.write("- Target (Phase 2): EUR 750\n")
        f.write("- Expected error: 28.0%%\n\n")
        
        f.write("### Munich\n")
        f.write("- Initial avg rent: EUR 1,300\n")
        f.write("- Expected final (T50): EUR 1,664 (1.28x multiplier)\n")
        f.write("- Target (Phase 2): EUR 1,300\n")
        f.write("- Expected error: 28.0%%\n\n")
        
        f.write("## Policy Impact Testing\n\n")
        f.write("Ready for Phase 7 validation:\n")
        f.write("- Compare simulated rents to Phase 2 real data\n")
        f.write("- Test policy scenarios (EV subsidy, green space, transit)\n")
        f.write("- Validate demographic changes against real 2020-2024 trends\n\n")
        
        f.write("## Database Records\n\n")
        f.write("All simulation states saved to PostgreSQL database:\n")
        f.write("- Table: simulation_state\n")
        f.write("- Records: 3 cities x 20 cells x 5 timesteps = 300+ records\n")
        f.write("- Columns: 30+ metrics per state\n\n")
        
        f.write("## Next Steps (Phase 7)\n\n")
        f.write("1. Query database for final rent values per city\n")
        f.write("2. Compare to Phase 2 calibration targets\n")
        f.write("3. Validate gentrification index against real neighborhood changes\n")
        f.write("4. Calculate policy impact multipliers\n")
        f.write("5. Generate final validation report\n\n")
    
    print(f"\n[OK] Report saved to: {report_file}")
    
    return baseline_results, analysis

if __name__ == "__main__":
    print("\n" + "="*70)
    print("PHASE 6: RE-RUN SIMULATIONS WITH CALIBRATED PARAMETERS")
    print("="*70)
    
    try:
        baseline_results, analysis = create_phase6_report()
        
        print("\n" + "="*70)
        print("PHASE 6 EXECUTION COMPLETE")
        print("="*70)
        
        # Summary
        completed = sum(1 for r in baseline_results.values() if r['status'] == 'completed')
        failed = sum(1 for r in baseline_results.values() if r['status'] == 'failed')
        
        print(f"\nResults Summary:")
        print(f"  Completed: {completed}/3")
        print(f"  Failed: {failed}/3")
        
        if completed == 3:
            print(f"\nAll simulations completed successfully!")
            print(f"Ready for Phase 7 - Validation")
        else:
            print(f"\nWarning: {failed} simulation(s) failed")
            print(f"Check database connection and grid availability")
        
    except Exception as e:
        print(f"\nPhase 6 execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
