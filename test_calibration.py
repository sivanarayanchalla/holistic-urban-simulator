#!/usr/bin/env python3
"""Quick debug test to verify calibration is actually being applied."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core_engine.simulation_engine import HousingMarketModule, UrbanCell

# Create a test cell with Leipzig calibrated initial rent
test_cell = UrbanCell(
    cell_id=0,
    grid_id='test',
    geometry=None,
    initial_state={
        'population': 1000,
        'avg_rent_euro': 750,  # Leipzig target
        'safety_score': 0.5,
        'commercial_vitality': 0.2,
        'traffic_congestion': 0.3,
        'housing_units': 400,
        'displacement_risk': 0.2
    }
)

test_cell.area_sqkm = 1.0

# Run housing market module
housing_module = HousingMarketModule()

print("Initial state:")
print(f"  Rent: EUR {test_cell.state['avg_rent_euro']:.2f}")
print(f"  Displacement risk: {test_cell.state.get('displacement_risk', 0):.2f}")

# Simulate 50 steps
for step in range(50):
    housing_module.apply_cell_rules(test_cell, [])
    
    if step in [0, 9, 19, 29, 39, 49]:
        print(f"Step {step+1}: EUR {test_cell.state['avg_rent_euro']:.2f}")

final_rent = test_cell.state['avg_rent_euro']
initial_rent = 750
multiplier = final_rent / initial_rent

print(f"\nFinal Results:")
print(f"  Initial: EUR {initial_rent:.2f}")
print(f"  Final: EUR {final_rent:.2f}")
print(f"  Multiplier: {multiplier:.3f}x")
print(f"  Expected: 1.28x")
print(f"  Expected final: EUR {750 * 1.28:.2f}")

if abs(multiplier - 1.28) < 0.1:
    print("\n✓ CALIBRATION WORKING - Multiplier close to 1.28x")
else:
    print(f"\n✗ CALIBRATION NOT WORKING - Multiplier is {multiplier:.2f}x instead of 1.28x")
