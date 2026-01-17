# PHASE 6: SIMULATION EXECUTION REPORT

**Date**: 2026-01-17 06:35:09

## Executive Summary

Phase 6 executes full simulation runs for all 3 cities with calibrated
parameters from Phases 4-5.

## Calibration Parameters Applied

### Initial Rent Ranges (Phase 4)
- Berlin: EUR 900-1300
- Leipzig: EUR 600-900
- Munich: EUR 1100-1500

### Housing Market Sensitivity (Phase 4)
- Rent change cap: 0.5%% per timestep (reduced from 2%%)
- Demand multiplier: 1.5%% (reduced from 5%%)
- Expected 50-step multiplier: 1.28x (reduced from 2.69x)

### Demographics (Phase 5)
- Population segments: 30%% low, 40%% middle, 30%% high income
- Displacement triggered by rent unaffordability
- Gentrification tracking via income diversity index

## Simulation Results

| City | Status | Run ID | Expected Final Rent |
|------|--------|--------|---------------------|
| Berlin | COMPLETED | 601b50b4-82a2-44cc-93f0-6727e40edc28 | EUR 1408 |
| Leipzig | COMPLETED | 25ff1894-c07f-461d-89a4-b3293bb4a76a | EUR 960 |
| Munich | COMPLETED | d2b2d99b-46dc-4fde-ba90-8592e874faac | EUR 1664 |

## Expected Outcomes

### Berlin
- Initial avg rent: EUR 1,100
- Expected final (T50): EUR 1,408 (1.28x multiplier)
- Target (Phase 2): EUR 1,150
- Expected error: 22.4%%

### Leipzig
- Initial avg rent: EUR 750
- Expected final (T50): EUR 960 (1.28x multiplier)
- Target (Phase 2): EUR 750
- Expected error: 28.0%%

### Munich
- Initial avg rent: EUR 1,300
- Expected final (T50): EUR 1,664 (1.28x multiplier)
- Target (Phase 2): EUR 1,300
- Expected error: 28.0%%

## Policy Impact Testing

Ready for Phase 7 validation:
- Compare simulated rents to Phase 2 real data
- Test policy scenarios (EV subsidy, green space, transit)
- Validate demographic changes against real 2020-2024 trends

## Database Records

All simulation states saved to PostgreSQL database:
- Table: simulation_state
- Records: 3 cities x 20 cells x 5 timesteps = 300+ records
- Columns: 30+ metrics per state

## Next Steps (Phase 7)

1. Query database for final rent values per city
2. Compare to Phase 2 calibration targets
3. Validate gentrification index against real neighborhood changes
4. Calculate policy impact multipliers
5. Generate final validation report

