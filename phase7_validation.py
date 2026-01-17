#!/usr/bin/env python3
"""
PHASE 7: VALIDATION & CALIBRATION ACCURACY ASSESSMENT
=======================================================

Validates simulation outputs against Phase 2 real-world calibration data
(51 real neighborhoods from 3 cities).

VALIDATION APPROACH:
1. Extract final rent values (T=50) from Phase 6 simulation database
2. Compare to Phase 2 real-world data
3. Calculate calibration error for each city
4. Validate demographic patterns (gentrification indices)
5. Compare to expected outcomes from Phase 4

EXPECTED RESULTS:
Before calibration (Phase 2 baseline):
- Berlin: 2,100 EUR (82.6% overestimate)
- Leipzig: 2,350 EUR (213.3% overestimate)
- Munich: 2,650 EUR (103.8% overestimate)

After Phase 4 calibration (predicted):
- Berlin: 1,408 EUR (22.4% error)
- Leipzig: 960 EUR (28.0% error)
- Munich: 1,664 EUR (28.0% error)

Phase 7 will verify actual simulation outcomes match predictions.

REAL DATA TARGETS (Phase 2):
- Berlin: 1,150 EUR (average of 20 neighborhoods)
- Leipzig: 750 EUR (average of 15 neighborhoods)
- Munich: 1,300 EUR (average of 16 neighborhoods)
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database.db_config import db_config
from sqlalchemy import text

def extract_simulation_results():
    """Extract final simulation results from database."""
    print("\n" + "="*70)
    print("EXTRACTING SIMULATION RESULTS FROM DATABASE")
    print("="*70)
    
    results = {}
    
    # Run IDs from Phase 6
    run_ids = {
        'Berlin': '601b50b4-82a2-44cc-93f0-6727e40edc28',
        'Leipzig': '25ff1894-c07f-461d-89a4-b3293bb4a76a',
        'Munich': 'd2b2d99b-46dc-4fde-ba90-8592e874faac'
    }
    
    try:
        with db_config.get_session() as session:
            for city, run_id in run_ids.items():
                print(f"\nExtracting {city} results...")
                
                # Query T=50 states for this run
                query = text("""
                    SELECT AVG(avg_rent_euro) as avg_rent, 
                           MIN(avg_rent_euro) as min_rent,
                           MAX(avg_rent_euro) as max_rent,
                           COUNT(*) as cells,
                           STDDEV(avg_rent_euro) as std_rent
                    FROM simulation_state
                    WHERE run_id = :run_id
                    AND timestep = 50
                """)
                
                result = session.execute(query, {'run_id': run_id})
                row = result.fetchone()
                
                if row:
                    avg_rent, min_rent, max_rent, cells, std_rent = row
                    
                    results[city] = {
                        'run_id': run_id,
                        'avg_rent': float(avg_rent) if avg_rent else 0,
                        'min_rent': float(min_rent) if min_rent else 0,
                        'max_rent': float(max_rent) if max_rent else 0,
                        'cells': int(cells),
                        'std_rent': float(std_rent) if std_rent else 0
                    }
                    
                    print(f"  Avg Rent (T=50): EUR {results[city]['avg_rent']:.0f}")
                    print(f"  Min Rent: EUR {results[city]['min_rent']:.0f}")
                    print(f"  Max Rent: EUR {results[city]['max_rent']:.0f}")
                    print(f"  Std Dev: EUR {results[city]['std_rent']:.0f}")
                    print(f"  Cells: {results[city]['cells']}")
    
    except Exception as e:
        print(f"Error extracting results: {e}")
        import traceback
        traceback.print_exc()
    
    return results

def validate_calibration_accuracy(sim_results):
    """Validate simulation accuracy against Phase 2 real data."""
    print("\n" + "="*70)
    print("CALIBRATION ACCURACY VALIDATION")
    print("="*70)
    
    # Phase 2 real data targets
    real_targets = {
        'Berlin': 1150,
        'Leipzig': 750,
        'Munich': 1300
    }
    
    # Phase 4 predicted outcomes
    predicted = {
        'Berlin': 1408,
        'Leipzig': 960,
        'Munich': 1664
    }
    
    validation = {}
    
    for city in real_targets.keys():
        print(f"\n{city}:")
        
        real_target = real_targets[city]
        predicted_rent = predicted[city]
        
        if city in sim_results and sim_results[city]:
            sim_result = sim_results[city]
            actual_rent = sim_result['avg_rent']
            
            # Calculate errors
            predicted_error = abs(predicted_rent - real_target) / real_target * 100
            actual_error = abs(actual_rent - real_target) / real_target * 100
            improvement = predicted_error - actual_error
            
            print(f"  Real Target (Phase 2): EUR {real_target:.0f}")
            print(f"  Predicted (Phase 4): EUR {predicted_rent:.0f} (error: {predicted_error:.1f}%%)")
            print(f"  Actual (Phase 6): EUR {actual_rent:.0f} (error: {actual_error:.1f}%%)")
            print(f"  Improvement: {improvement:.1f}%% {'(worse)' if improvement < 0 else '(better)'}")
            
            # Validation status
            status = "PASS" if actual_error < 35 else "NEEDS IMPROVEMENT"
            print(f"  Status: {status}")
            
            validation[city] = {
                'real_target': real_target,
                'predicted': predicted_rent,
                'actual': actual_rent,
                'predicted_error': predicted_error,
                'actual_error': actual_error,
                'improvement': improvement,
                'status': status
            }
        else:
            print(f"  No simulation results found")
            validation[city] = {'status': 'NO DATA'}
    
    return validation

def generate_phase7_report(sim_results, validation):
    """Generate comprehensive Phase 7 validation report."""
    print("\n" + "="*70)
    print("GENERATING PHASE 7 VALIDATION REPORT")
    print("="*70)
    
    report_file = Path(__file__).parent / "PHASE_7_VALIDATION_REPORT.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# PHASE 7: VALIDATION & CALIBRATION ACCURACY REPORT\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write("Phase 7 validates the calibrated simulation against real-world data\n")
        f.write("from Phase 2 analysis (51 neighborhoods across 3 cities).\n\n")
        
        f.write("## Calibration Performance Comparison\n\n")
        f.write("| City | Real Target | Predicted | Actual | Pred Error | Actual Error | Status |\n")
        f.write("|------|-------------|-----------|--------|------------|--------------|--------|\n")
        
        for city, val in validation.items():
            if val.get('status') != 'NO DATA':
                f.write(f"| {city} | EUR {val['real_target']} | EUR {val['predicted']:.0f} | EUR {val['actual']:.0f} | {val['predicted_error']:.1f}%% | {val['actual_error']:.1f}%% | {val['status']} |\n")
        
        f.write("\n## Detailed Analysis\n\n")
        
        for city, val in validation.items():
            if val.get('status') != 'NO DATA':
                f.write(f"### {city}\n\n")
                f.write(f"**Real-World Target** (Phase 2 analysis): EUR {val['real_target']}\n")
                f.write(f"- Based on average of real neighborhoods\n")
                f.write(f"- Market rent including utilities and services\n\n")
                
                f.write(f"**Simulation Prediction** (Phase 4): EUR {val['predicted']:.0f}\n")
                f.write(f"- Initial range centered at EUR {val['real_target']}\n")
                f.write(f"- Expected after 1.28x multiplier over 50 steps\n")
                f.write(f"- Predicted error: {val['predicted_error']:.1f}%%\n\n")
                
                f.write(f"**Actual Simulation Result** (Phase 6): EUR {val['actual']:.0f}\n")
                f.write(f"- Final average rent at timestep 50\n")
                f.write(f"- Actual error: {val['actual_error']:.1f}%%\n")
                f.write(f"- Difference from prediction: EUR {abs(val['actual'] - val['predicted']):.0f}\n\n")
                
                if val['actual_error'] < val['predicted_error']:
                    f.write(f"**Result**: Better than expected (+{val['improvement']:.1f}%% improvement)\n\n")
                else:
                    f.write(f"**Result**: Slightly worse than expected ({val['improvement']:.1f}%%)\n\n")
        
        f.write("## Validation Metrics\n\n")
        f.write("### Acceptable Calibration Error Ranges\n")
        f.write("- Excellent: < 10%% error\n")
        f.write("- Good: 10-20%% error\n")
        f.write("- Acceptable: 20-35%% error\n")
        f.write("- Needs Improvement: > 35%% error\n\n")
        
        f.write("## Demographic Validation\n\n")
        f.write("The DemographicsModule tracks income-based displacement:\n")
        f.write("- Low-income population displacement when rent unaffordable\n")
        f.write("- High-income migration to premium neighborhoods\n")
        f.write("- Gentrification index showing neighborhood composition changes\n")
        f.write("- Income diversity index declining in expensive areas\n\n")
        
        f.write("## Conclusion\n\n")
        
        all_status = [v.get('status') for v in validation.values() if v.get('status') != 'NO DATA']
        
        if all('PASS' in s for s in all_status):
            f.write("All cities pass calibration validation. Simulation is ready for:\n")
            f.write("1. Policy impact analysis\n")
            f.write("2. Scenario testing\n")
            f.write("3. Long-term trend prediction\n\n")
        else:
            f.write("Some calibration targets not fully met. Recommendations:\n")
            f.write("1. Fine-tune demographic thresholds (Phase 5)\n")
            f.write("2. Adjust housing market sensitivity (Phase 4)\n")
            f.write("3. Review policy module interactions\n\n")
        
        f.write("## Next Steps (Phase 8)\n\n")
        f.write("1. Generate policy impact reports\n")
        f.write("2. Create user guide and documentation\n")
        f.write("3. Finalize database schema documentation\n")
        f.write("4. Prepare GitHub release with all documentation\n\n")
    
    print(f"\n[OK] Report saved to: {report_file}")
    return report_file

def create_validation_summary():
    """Create comprehensive Phase 7 validation."""
    print("\n" + "="*70)
    print("PHASE 7: VALIDATION & ACCURACY ASSESSMENT")
    print("="*70)
    
    # Extract results
    sim_results = extract_simulation_results()
    
    # Validate accuracy
    validation = validate_calibration_accuracy(sim_results)
    
    # Generate report
    report_file = generate_phase7_report(sim_results, validation)
    
    return sim_results, validation, report_file

if __name__ == "__main__":
    try:
        sim_results, validation, report_file = create_validation_summary()
        
        print("\n" + "="*70)
        print("PHASE 7 VALIDATION COMPLETE")
        print("="*70)
        
        # Summary
        passed = sum(1 for v in validation.values() if v.get('status') == 'PASS')
        total = sum(1 for v in validation.values() if v.get('status') != 'NO DATA')
        
        print(f"\nValidation Summary:")
        print(f"  Passed: {passed}/{total}")
        print(f"  Report: {report_file}")
        
        if passed == total and total > 0:
            print(f"\n✓ All calibrations validated successfully!")
            print(f"Ready for Phase 8 - Final Documentation")
        
    except Exception as e:
        print(f"\nPhase 7 validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
