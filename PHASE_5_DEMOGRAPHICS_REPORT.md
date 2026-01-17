# PHASE 5: DEMOGRAPHICS MODULE VALIDATION REPORT

**Date**: 2026-01-17 06:32:53

## Executive Summary

Phase 5 implements the DemographicsModule for income-based displacement
and gentrification tracking in urban neighborhoods.

## Implementation Details

### Income Distribution (30/40/30)
- Low-income (30%): 1,500 EUR/month avg
- Middle-income (40%): 3,000 EUR/month avg
- High-income (30%): 6,000 EUR/month avg

### Affordability Thresholds (30% rule)
- Low-income: 450 EUR/month max
- Middle-income: 900 EUR/month max
- High-income: 1,800 EUR/month max

### Displacement Mechanics
#### Low-Income Displacement
- Threshold: Rent > 450 EUR and displacement_risk > 0.4
- Max outmigration: 20% per timestep
- Mechanism: Rising rents price out vulnerable residents

#### Middle-Income Displacement
- Threshold: Rent > 900 EUR and displacement_risk > 0.6
- Max outmigration: 10% per timestep
- Mechanism: Neighborhood gentrification affects stability

#### High-Income Attraction
- Trigger: Rent > 1,200 EUR and displacement_risk > 0.5
- Max inflow: 5% population increase per timestep
- Mechanism: Upgraded neighborhoods attract wealthy residents

### Key Metrics
- **Gentrification Index**: 0 (none) to 1 (complete)
  * Calculated as: (high_income_share - 0.30) / 0.70
  * 0 = baseline 30% high-income
  * 1 = all residents high-income

- **Income Diversity Index**: 0 (segregated) to 1 (balanced)
  * Perfect balance = 30/40/30 distribution
  * Calculates deviation from target distribution

## Test Results

- TEST 1: Demographic Initialization - PASS
- TEST 2: Low-Income Displacement - PASS
- TEST 3: Gentrification Dynamics - PASS
- TEST 4: Affordability Thresholds - PASS

## Integration with Other Modules

The DemographicsModule integrates with:
- **HousingMarketModule**: Rent changes trigger displacement
- **PopulationModule**: Total population updated after demographics
- **SpatialEffectsModule**: Gentrification spreads to neighbors
- **PolicyModule**: Rent control reduces displacement risk

## Phase 6: Next Steps

- Re-run simulations with calibrated rent ranges and demographics
- Fix employment NULL bug in database
- Test policy scenarios with income-aware population dynamics
- Compare to real 2020-2024 neighborhood changes

