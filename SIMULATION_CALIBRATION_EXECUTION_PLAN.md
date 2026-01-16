# 🚀 SIMULATION CALIBRATION EXECUTION PLAN

**Status**: Ready to begin  
**Timeline**: 4-5 weeks  
**Phases**: 8 sequential phases  
**Deliverable**: Validated policy recommendations with confidence levels  

---

## 📊 Quick Reference: What Needs to Change

### CURRENT STATE (Preliminary)
```
BERLIN
Population: 867 [unknown units]
Rent: €2,941/mo [2-3x too high]
Vitality: 0.145 [unclear meaning]
Displacement: 0.527 [missing detail]
Policy: Combined is best [pending validation]

LEIPZIG
Population: 705 [unknown units]
Rent: €3,050/mo [2.5-3.8x too high]
Vitality: 0.131 [unclear meaning]
Displacement: 0.552 [missing detail]
Policy: Housing-first is best [pending validation]

MUNICH
Population: 970 [unknown units]
Rent: €3,004/mo [1.4-1.7x too high]
Vitality: 0.155 [unclear meaning]
Displacement: 0.546 [missing detail]
Policy: Combined is best [pending validation]

Missing: Geographic zones, Demographic breakdown
Confidence: ⚠️ LOW
```

### DESIRED STATE (After Calibration)
```
BERLIN
Population: 3.8M actual residents
Rent: €1,350 average [real 2024 market data]
  - Zone 1 (center): €1,728/mo
  - Zone 2 (inner): €1,548/mo
  - Zone 3 (mid-ring): €1,008/mo
  - Zone 4 (suburbs): €612/mo
Vitality: [Same metric, zone-specific values]
Displacement: [Geographic + demographic detail]
Policy: [Different for each zone/demographic]
  - Low-income: Housing subsidy critical
  - Families: Green space + transit
  - Young professionals: Transit + housing
Geographic detail: Zone-specific policy impacts
Demographic detail: Impact by income, household type, age
Confidence: ✅ HIGH (±5-10%)
```

---

## 🗓️ Phase Breakdown

### **Phase 1: Audit (Week 1, Days 1-5)**
**Goal**: Understand current simulation

```
Day 1-2: Code Review
  - simulation_engine.py: How does simulation work?
  - models.py: What's stored in database?
  - db_config.py: How's it configured?
  
Day 3-4: Extract Baseline
  - Write diagnostics/extract_baseline.py
  - Get exact initial values for all cities
  - Output: baseline_values.csv

Day 5: Geography Mapping
  - Map grid cells to real neighborhoods
  - Output: grid_to_neighborhood_mapping.csv

DELIVERABLE: Architecture document + baseline data
```

---

### **Phase 2: Rent Calibration (Week 2, Days 6-10)**
**Goal**: Fix rent to match 2024 market

```
Day 6-7: Data Collection
  - Gather real rent by neighborhood (Immobilienscout24)
  - Berlin: Mitte, Kreuzberg, Charlottenburg, Lichtenberg, Spandau
  - Leipzig: All major neighborhoods
  - Munich: All major neighborhoods
  - Output: real_rent_2024.csv

Day 8: Comparison Analysis
  - Run diagnostics/compare_rents.py
  - Calculate discrepancy factors (2.0-3.0x)
  - Identify rent drivers
  
Day 9-10: Calibration
  - Update simulation initialization code
  - Apply adjustment factors per cell
  - Verify: simulation rents now match market

DELIVERABLE: Calibrated rent model
```

---

### **Phase 3: Population Scaling (Week 2, Days 9-10)**
**Goal**: Know what population numbers mean

```
Day 9: Investigation
  - Run diagnostics/understand_population.py
  - Count grid cells per city
  - Determine what "867 residents" represents
  - Calculate scaling factor

Day 10: Implementation
  - Add POPULATION_SCALING_FACTORS to code
  - Update all population calculations
  - Verify: simulation now matches real metro populations

DELIVERABLE: Population scaling factors + updated code
```

---

### **Phase 4: Geographic Heterogeneity (Week 3, Days 11-15)**
**Goal**: Add location-based variation

```
Day 11-12: Zone Definition
  - Define Zone 1-4 for each city
  - Map neighborhoods to zones
  - Output: zone_definitions.csv
  
Day 13: Amenity Scoring
  - Create amenity_scoring.py
  - Calculate scores per zone (transit, walk, jobs, parks, etc.)
  - Output: amenity_scores.csv

Day 14-15: Rent by Location Model
  - Create rent_model.py
  - Implement: Rent = f(amenities, distance, zone)
  - Verify: Zone 1 > Zone 2 > Zone 3 > Zone 4
  - Test: Realistic values for all zones

DELIVERABLE: Geographic zone model with location-based rents
```

---

### **Phase 5: Demographic Heterogeneity (Week 3, Days 15-17)**
**Goal**: Segment population by needs

```
Day 15: Segment Definition
  - Define income segments (low, middle, high)
  - Define household types (single, couple, family, etc.)
  - Define age groups
  - Output: demographic_segments.csv

Day 16-17: Response Modeling
  - Create demographic_responses.py
  - Model how each segment reacts to policies
  - Calculate impacts: policy × demographic × location
  - Output: impact_matrix.csv

DELIVERABLE: Demographic segmentation + response model
```

---

### **Phase 6: Simulation Execution (Week 4, Days 18-20)**
**Goal**: Re-run policy scenarios with corrected model

```
Day 18: Baseline Run
  - Execute simulation with all calibrations
  - 50 timesteps, all 3 cities
  - Verify: Results match expectations
  - Output: calibrated_baseline.csv

Day 19: Policy Scenarios (5x)
  - Housing subsidy policy
  - Transit investment policy
  - Green infrastructure policy
  - Combined policy
  - Control (no policy)
  - Output: 5 scenario results
  
Day 20: Impact Analysis
  - Calculate impacts by zone
  - Calculate impacts by demographic
  - Generate geographic impact maps
  - Output: detailed impact analysis

DELIVERABLE: Recalibrated policy scenario results
```

---

### **Phase 7: Validation (Week 4, Days 20-22)**
**Goal**: Verify results against real world

```
Day 20-21: Real Data Comparison
  - Compare simulation trends to 2020-2024 real data
  - Berlin: population +2% in reality vs. simulation +5%?
  - Leipzig: rent +15% in reality vs. simulation +20%?
  - Munich: trends match?
  - Output: validation_report.csv

Day 22: Expert Review
  - Present to urban planner
  - Present to housing economist
  - Get feedback on assumptions
  - Make adjustments based on expert input

DELIVERABLE: Validation report + expert feedback
```

---

### **Phase 8: Documentation (Week 5, Days 23-25)**
**Goal**: Update all analysis with new numbers

```
Day 23: Update Analysis Documents
  - ANALYSIS_REPORT_3CITIES.md: Real numbers
  - POLICY_TESTING_COMPLETE.md: Remove "preliminary"
  - POLICY_ANALYSIS_SUMMARY.md: New recommendations
  - SESSION_COMPLETE.md: Mark as VALIDATED

Day 24: Create Validation Report
  - New file: CALIBRATION_VALIDATION_REPORT.md
  - What was fixed?
  - How confident are we? (±X%)
  - What's still unknown?

Day 25: Final Review
  - All documents reviewed
  - Ready for stakeholder presentation
  - Confidence levels documented
  - Timeline for implementation clear

DELIVERABLE: Complete validated analysis package
```

---

## 📈 Expected Number Changes

### Rent (Most Dramatic Change)
```
BERLIN
Before: €2,941/mo everywhere
After:  Zone 1: €1,728, Zone 2: €1,548, Zone 3: €1,008, Zone 4: €612
Change: -41% to -79% depending on zone

LEIPZIG
Before: €3,050/mo everywhere
After:  Zone 1: €1,400, Zone 2: €1,200, Zone 3: €800, Zone 4: €500
Change: -54% to -84% depending on zone

MUNICH
Before: €3,004/mo everywhere
After:  Zone 1: €2,100, Zone 2: €1,900, Zone 3: €1,300, Zone 4: €900
Change: -30% to -70% depending on zone
```

### Population
```
BERLIN
Before: 867 "units" (undefined)
After:  3.8M actual residents (clear)

LEIPZIG
Before: 705 "units" (undefined)
After:  1.2M actual residents (clear)

MUNICH
Before: 970 "units" (undefined)
After:  2.7M actual residents (clear)
```

### Policy Recommendations
```
BERLIN
Before: Combined policy
After:  [Pending validation - may change]
  - Depends on real zone distribution
  - Low-income concentrated where?
  - Which zones need most help?

LEIPZIG
Before: Housing subsidy (good choice, likely confirmed)
After:  [Pending validation]
  - €30M estimate correct?
  - Subsidy amount (€270/mo)?
  - Better to target just low-income or all?

MUNICH
Before: Combined policy
After:  [Pending validation]
  - Real affordability crisis exists?
  - Or just simulation error?
```

---

## ✅ Success Criteria

**Week 1-2:**
- ✅ Rent calibrated to 2024 market data
- ✅ Population scaling factors established
- ✅ Geographic zones defined and mapped

**Week 3:**
- ✅ Location-based rent model working
- ✅ Demographic segments defined
- ✅ Policy impacts calculated by zone and demographic

**Week 4:**
- ✅ Recalibrated policy scenarios complete
- ✅ Results validated against real 2020-2024 trends
- ✅ Expert review feedback incorporated

**Week 5:**
- ✅ All documents updated with validated numbers
- ✅ Confidence levels specified (±X%)
- ✅ Ready for stakeholder presentation

---

## 🎯 Key Questions to Answer During Phases

**Phase 1:**
- What does "population 867" actually represent?
- Where do initial rent values come from?

**Phase 2:**
- Is rent calculation formula documented?
- Can rent adjustments be applied retroactively?

**Phase 3:**
- What's the actual metropolitan population vs. simulation units?
- Is there cell-by-cell population data in database?

**Phase 4:**
- Do grid cells correspond to real neighborhood boundaries?
- Can we overlay simulation grid on real maps?

**Phase 5:**
- Are demographic proportions documented?
- How do residents choose locations based on income?

**Phase 6:**
- Do recalibrated simulations converge?
- Are trend directions (increasing/decreasing) still same?

**Phase 7:**
- Do simulation results match 2024 reality within ±10%?
- Do experts agree with assumptions?

**Phase 8:**
- Can we confidently present numbers to stakeholders?
- What disclaimers are still needed?

---

## 📚 Related Documents

Read In This Order:

1. **[CRITICAL_FINDINGS_DATA_CALIBRATION.md](CRITICAL_FINDINGS_DATA_CALIBRATION.md)** - Why this is needed
2. **[SIMULATION_CALIBRATION_ROADMAP.md](SIMULATION_CALIBRATION_ROADMAP.md)** - Detailed roadmap (this references)
3. **[SIMULATION_CALIBRATION_EXECUTION_PLAN.md](SIMULATION_CALIBRATION_EXECUTION_PLAN.md)** - This file (quick reference)

---

## 🚀 Ready to Start?

**Next Action**: Begin Phase 1 (Week 1)

**First Step**: Review `src/core_engine/simulation_engine.py` to understand architecture

**Time Estimate**: Phase 1 = 1-2 days for code review + documentation

---

*Document Created: January 16, 2026*  
*Purpose: Quick reference execution plan for simulation calibration*  
*Status: Ready to begin*
