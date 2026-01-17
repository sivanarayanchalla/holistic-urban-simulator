#!/usr/bin/env python3
"""
PHASE 5: DEMOGRAPHICS MODULE VALIDATION
========================================

Validates the DemographicsModule implementation for income-based
displacement modeling and gentrification dynamics.

IMPLEMENTATION DETAILS:
- Population segmented into 3 income groups: 30% low, 40% middle, 30% high
- Income-specific displacement thresholds based on affordability
- Gentrification index tracking neighborhood income composition changes

DISPLACEMENT MECHANICS:
1. Low-income (30%): Most vulnerable
   - Affordability threshold: 450 EUR/month (30% of 1500 EUR income)
   - Displacement risk > 0.4: triggers up to 20% outmigration

2. Middle-income (40%): More stable
   - Affordability threshold: 900 EUR/month (30% of 3000 EUR income)
   - Displacement risk > 0.6: triggers up to 10% outmigration

3. High-income (30%): Attracts to premium areas
   - Affordability threshold: 1800 EUR/month (30% of 6000 EUR income)
   - Attracts to areas with rent > 1200 EUR and displacement risk > 0.5

METRICS TRACKED:
- Gentrification Index: 0 (none) to 1 (complete)
- Income Diversity Index: 1 (30/40/30 perfect) to 0 (segregated)
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core_engine.simulation_engine import DemographicsModule, UrbanCell

class MockCell:
    """Mock cell for testing demographics."""
    def __init__(self, rent=750, displacement_risk=0.2):
        self.state = {
            'population': 1000,
            'avg_rent_euro': rent,
            'displacement_risk': displacement_risk
        }
        self.area_sqkm = 1.0

def test_demographic_initialization():
    """Test initial demographic composition."""
    print("\n" + "="*70)
    print("TEST 1: DEMOGRAPHIC INITIALIZATION")
    print("="*70)
    
    # Create mock cells
    cells = {}
    for i in range(3):
        cell = MockCell()
        cells[f"cell_{i}"] = cell
    
    # Initialize demographics
    demo_module = DemographicsModule()
    demo_module.initialize_demographics(cells)
    
    # Check initialization
    test_cell = cells['cell_0']
    low_pop = test_cell.state['low_income_population']
    middle_pop = test_cell.state['middle_income_population']
    high_pop = test_cell.state['high_income_population']
    total = low_pop + middle_pop + high_pop
    
    print(f"\nInitial Population Distribution:")
    print(f"  Low income (30%):    {low_pop} ({low_pop/total*100:.1f}%)")
    print(f"  Middle income (40%): {middle_pop} ({middle_pop/total*100:.1f}%)")
    print(f"  High income (30%):   {high_pop} ({high_pop/total*100:.1f}%)")
    print(f"  Total: {total}")
    
    assert abs(low_pop/total - 0.30) < 0.05, "Low income share incorrect"
    assert abs(middle_pop/total - 0.40) < 0.05, "Middle income share incorrect"
    assert abs(high_pop/total - 0.30) < 0.05, "High income share incorrect"
    
    print("\nStatus: PASS - Income distribution correct")
    
    return cells

def test_low_income_displacement():
    """Test low-income displacement when rent becomes unaffordable."""
    print("\n" + "="*70)
    print("TEST 2: LOW-INCOME DISPLACEMENT")
    print("="*70)
    
    # Create cell with increasing rent
    cell = MockCell(rent=750, displacement_risk=0.2)
    cell.state['low_income_population'] = 300
    cell.state['middle_income_population'] = 400
    cell.state['high_income_population'] = 300
    
    demo_module = DemographicsModule()
    
    print(f"\nInitial state:")
    print(f"  Rent: 750 EUR (affordable for low-income)")
    print(f"  Displacement risk: 0.2 (low)")
    print(f"  Low-income population: 300")
    
    # Apply module
    demo_module.apply_cell_rules(cell, [])
    
    print(f"\nAfter displacement calculation (no change expected):")
    print(f"  Low-income population: {cell.state['low_income_population']} (unchanged)")
    
    # Now increase rent and displacement risk
    cell.state['avg_rent_euro'] = 1000
    cell.state['displacement_risk'] = 0.5
    cell.state['low_income_population'] = 300  # Reset
    
    print(f"\nNew conditions:")
    print(f"  Rent: 1000 EUR (unaffordable for low-income)")
    print(f"  Displacement risk: 0.5 (high)")
    
    demo_module.apply_cell_rules(cell, [])
    
    low_after = cell.state['low_income_population']
    displacement_pct = (300 - low_after) / 300 * 100
    
    print(f"\nAfter displacement calculation:")
    print(f"  Low-income population: {low_after} (displaced {displacement_pct:.1f}%)")
    assert low_after < 300, "Low-income population should decrease"
    assert displacement_pct > 10, "Displacement should be > 10%"
    
    print("\nStatus: PASS - Low-income displacement working")

def test_gentrification_dynamics():
    """Test gentrification index and high-income attraction."""
    print("\n" + "="*70)
    print("TEST 3: GENTRIFICATION DYNAMICS")
    print("="*70)
    
    # Start with balanced income distribution
    cell = MockCell(rent=1500, displacement_risk=0.6)
    cell.state['low_income_population'] = 200
    cell.state['middle_income_population'] = 300
    cell.state['high_income_population'] = 500  # Already skewed high
    
    demo_module = DemographicsModule()
    
    total_before = 200 + 300 + 500
    high_share_before = 500 / total_before
    
    print(f"\nInitial state:")
    print(f"  Low: 200 (20%)")
    print(f"  Middle: 300 (30%)")
    print(f"  High: 500 (50%) - GENTRIFIED")
    print(f"  Rent: 1500 EUR (premium)")
    print(f"  Displacement risk: 0.6 (gentrification pressure)")
    
    # Apply module
    demo_module.apply_cell_rules(cell, [])
    
    gentrification_index = cell.state.get('gentrification_index', 0.0)
    diversity_index = cell.state.get('income_diversity_index', 1.0)
    
    print(f"\nAfter displacement:")
    print(f"  Gentrification Index: {gentrification_index:.2f} (1.0 = fully gentrified)")
    print(f"  Diversity Index: {diversity_index:.2f} (1.0 = balanced, 0 = segregated)")
    
    assert gentrification_index > 0.3, "Gentrification index should show gentrification"
    assert diversity_index < 1.0, "Diversity should decrease with high-income concentration"
    
    print("\nStatus: PASS - Gentrification tracking working")

def test_affordability_calculations():
    """Test affordability threshold enforcement."""
    print("\n" + "="*70)
    print("TEST 4: AFFORDABILITY THRESHOLDS")
    print("="*70)
    
    cell = MockCell()
    demo_module = DemographicsModule()
    demo_module.initialize_demographics({cell.state.get('grid_id', 'test'): cell})
    
    threshold_low = cell.state.get('affordability_threshold_low')
    threshold_middle = cell.state.get('affordability_threshold_middle')
    threshold_high = cell.state.get('affordability_threshold_high')
    
    print(f"\nIncome Groups and Affordability Thresholds:")
    print(f"  Low-income (1,500 EUR/month):    Max {threshold_low} EUR/month (30%)")
    print(f"  Middle-income (3,000 EUR/month): Max {threshold_middle} EUR/month (30%)")
    print(f"  High-income (6,000 EUR/month):   Max {threshold_high} EUR/month (30%)")
    
    # Verify calculations
    assert abs(threshold_low - 450) < 1, "Low income threshold incorrect"
    assert abs(threshold_middle - 900) < 1, "Middle income threshold incorrect"
    assert abs(threshold_high - 1800) < 1, "High income threshold incorrect"
    
    print(f"\nComparison to typical rents:")
    print(f"  Leipzig (750 EUR): Affordable for low (450), middle (900), high (1800)")
    print(f"  Berlin (1150 EUR): Unaffordable for low (450), middle (900), high (1800)")
    print(f"  Munich (1300 EUR): Unaffordable for low (450), middle (900), high (1800)")
    
    print("\nStatus: PASS - Affordability thresholds correct")

def generate_phase5_report():
    """Generate comprehensive Phase 5 report."""
    print("\n" + "="*70)
    print("PHASE 5 DEMOGRAPHICS MODULE - VALIDATION REPORT")
    print("="*70)
    
    # Run tests
    cells = test_demographic_initialization()
    test_low_income_displacement()
    test_gentrification_dynamics()
    test_affordability_calculations()
    
    # Generate report file
    report_file = Path(__file__).parent / "PHASE_5_DEMOGRAPHICS_REPORT.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# PHASE 5: DEMOGRAPHICS MODULE VALIDATION REPORT\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write("Phase 5 implements the DemographicsModule for income-based displacement\n")
        f.write("and gentrification tracking in urban neighborhoods.\n\n")
        
        f.write("## Implementation Details\n\n")
        f.write("### Income Distribution (30/40/30)\n")
        f.write("- Low-income (30%): 1,500 EUR/month avg\n")
        f.write("- Middle-income (40%): 3,000 EUR/month avg\n")
        f.write("- High-income (30%): 6,000 EUR/month avg\n\n")
        
        f.write("### Affordability Thresholds (30% rule)\n")
        f.write("- Low-income: 450 EUR/month max\n")
        f.write("- Middle-income: 900 EUR/month max\n")
        f.write("- High-income: 1,800 EUR/month max\n\n")
        
        f.write("### Displacement Mechanics\n")
        f.write("#### Low-Income Displacement\n")
        f.write("- Threshold: Rent > 450 EUR and displacement_risk > 0.4\n")
        f.write("- Max outmigration: 20% per timestep\n")
        f.write("- Mechanism: Rising rents price out vulnerable residents\n\n")
        
        f.write("#### Middle-Income Displacement\n")
        f.write("- Threshold: Rent > 900 EUR and displacement_risk > 0.6\n")
        f.write("- Max outmigration: 10% per timestep\n")
        f.write("- Mechanism: Neighborhood gentrification affects stability\n\n")
        
        f.write("#### High-Income Attraction\n")
        f.write("- Trigger: Rent > 1,200 EUR and displacement_risk > 0.5\n")
        f.write("- Max inflow: 5% population increase per timestep\n")
        f.write("- Mechanism: Upgraded neighborhoods attract wealthy residents\n\n")
        
        f.write("### Key Metrics\n")
        f.write("- **Gentrification Index**: 0 (none) to 1 (complete)\n")
        f.write("  * Calculated as: (high_income_share - 0.30) / 0.70\n")
        f.write("  * 0 = baseline 30% high-income\n")
        f.write("  * 1 = all residents high-income\n\n")
        
        f.write("- **Income Diversity Index**: 0 (segregated) to 1 (balanced)\n")
        f.write("  * Perfect balance = 30/40/30 distribution\n")
        f.write("  * Calculates deviation from target distribution\n\n")
        
        f.write("## Test Results\n\n")
        f.write("- TEST 1: Demographic Initialization - PASS\n")
        f.write("- TEST 2: Low-Income Displacement - PASS\n")
        f.write("- TEST 3: Gentrification Dynamics - PASS\n")
        f.write("- TEST 4: Affordability Thresholds - PASS\n\n")
        
        f.write("## Integration with Other Modules\n\n")
        f.write("The DemographicsModule integrates with:\n")
        f.write("- **HousingMarketModule**: Rent changes trigger displacement\n")
        f.write("- **PopulationModule**: Total population updated after demographics\n")
        f.write("- **SpatialEffectsModule**: Gentrification spreads to neighbors\n")
        f.write("- **PolicyModule**: Rent control reduces displacement risk\n\n")
        
        f.write("## Phase 6: Next Steps\n\n")
        f.write("- Re-run simulations with calibrated rent ranges and demographics\n")
        f.write("- Fix employment NULL bug in database\n")
        f.write("- Test policy scenarios with income-aware population dynamics\n")
        f.write("- Compare to real 2020-2024 neighborhood changes\n\n")
    
    print(f"\n[OK] Report saved to: {report_file}")

if __name__ == "__main__":
    try:
        generate_phase5_report()
        
        print("\n" + "="*70)
        print("PHASE 5 VALIDATION COMPLETE")
        print("="*70)
        print("\nAll demographics tests passed successfully!")
        print("Demographics module ready for Phase 6 simulation runs.")
        print("\nKey capabilities:")
        print("  - Income segmentation (30/40/30)")
        print("  - Displacement thresholds by income")
        print("  - Gentrification tracking")
        print("  - Diversity index monitoring")
        
    except Exception as e:
        print(f"\nValidation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
