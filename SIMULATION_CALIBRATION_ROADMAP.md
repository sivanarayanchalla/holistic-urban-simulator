# 🔧 SIMULATION CALIBRATION ROADMAP

**Purpose**: Update simulations to fix baseline issues (rent, population scale, geography, demographics)  
**Timeline**: 4-5 weeks  
**Impact**: All policy recommendations depend on these fixes  
**Current Status**: ⚠️ Framework ready, numbers need validation

---

## 📋 Phase 1: Audit & Understanding (Week 1)

### Step 1.1: Understand Current Simulation Architecture
**Goal**: Know what the code does and where baseline values come from

**Files to Review:**
- `src/core_engine/simulation_engine.py` - Main simulation logic
- `src/database/models.py` - Data structure and how it's stored
- `src/database/db_config.py` - Database configuration
- `analyze_3cities.py` - Where baseline metrics are extracted
- `test_policy_scenarios.py` - Where policy impacts are calculated

**Questions to Answer:**
1. What does "population 867" represent?
   - Is it: people? households? grid cells? aggregate units?
   - What's the mapping to real residents?
   - Scaling factor needed?

2. How is rent calculated in the simulation?
   - What variables drive rent? (distance, amenities, jobs, etc.)
   - Where does initial rent come from? (hard-coded? data-driven?)
   - Why is it 2-3x higher than real market?

3. How are grid cells defined?
   - Size: 500m × 500m? 1km × 1km?
   - How many cells per city?
   - How do they map to real neighborhoods?

4. What columns in database represent what?
   - Look at the 30+ columns in `simulation_state` table
   - Which are input? Which are output?
   - How do they get modified during simulation?

**Output**: Architecture document explaining how simulation works

---

### Step 1.2: Extract Simulation Baseline Values
**Goal**: Get exact initial values for all 3 cities

**Code to Write:**
```python
# diagnostics/extract_baseline.py
# Query database for:
# - Population by city, by timestep
# - Average rent by city, by timestep
# - Vitality scores by city, by timestep
# - All 30+ columns by city
# - Geography data (grid cell mapping)
# Output to CSV for analysis
```

**Output**: Baseline values extracted to CSV for validation

---

### Step 1.3: Map Simulation Grid to Real Geography
**Goal**: Connect simulation grid cells to real neighborhoods

**Data Needed:**
- Hexagonal grid definition (coordinates, cell IDs)
- Real neighborhood boundaries (Berlin, Leipzig, Munich)
- Overlay grid on real map

**Tool**: QGIS or Python Shapely for geographic mapping

**Output**: Mapping document showing grid cell ↔ neighborhood correspondence

---

## 🔢 Phase 2: Rent Calibration (Week 2)

### Step 2.1: Collect Real 2024 Rent Data
**Goal**: Get actual market rent prices for each city

**Data Sources:**
- **Germany-wide**: Immobilienscout24.de (1M+ listings)
- **Berlin**: WunderFlats, ImmobilienScout (filter by city)
- **Leipzig**: Local real estate portals
- **Munich**: Local real estate portals
- **Average by neighborhood**: Calculate from listings

**What to Collect:**
- By neighborhood:
  - Average 1-bedroom rent
  - Average 2-bedroom rent
  - Price range (min/max)
  - Sample size (how many listings)

**Output**: `data/calibration/real_rent_2024.csv`
```
city,neighborhood,grid_cell_id,avg_1br_rent,avg_2br_rent,samples
berlin,Mitte,cell_001,1600,2200,150
berlin,Kreuzberg,cell_002,1400,1900,180
...
```

---

### Step 2.2: Compare Simulation vs. Real Rent
**Goal**: Understand the discrepancy

**Analysis Script:**
```python
# diagnostics/compare_rents.py
# Load: simulation baseline rent by cell
# Load: real 2024 rent by neighborhood
# Calculate: discrepancy factor
# Output: comparison table + visualization
```

**Expected Output:**
```
RENT DISCREPANCY ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━
Berlin
  Simulation avg: €2,941
  Real market avg: €1,350
  Discrepancy: 2.18x (simulation TOO HIGH)

Leipzig
  Simulation avg: €3,050
  Real market avg: €1,000
  Discrepancy: 3.05x (simulation TOO HIGH)

Munich
  Simulation avg: €3,004
  Real market avg: €2,000
  Discrepancy: 1.50x (simulation TOO HIGH)

POSSIBLE CAUSES:
- Baseline initialization error
- Missing inflation adjustment
- Different currency or measurement unit
- Data source mismatch
```

---

### Step 2.3: Adjust Rent Baseline in Simulation
**Goal**: Fix simulation rent to match 2024 market

**Code Changes:**
```python
# src/database/models.py or initialization code

# BEFORE:
avg_rent = 2940  # Hard-coded or from wrong source

# AFTER:
# Load real rent data by city/neighborhood
real_rent_2024 = load_calibration_data('real_rent_2024.csv')
adjustment_factor = real_rent / simulation_baseline
avg_rent = baseline_rent * adjustment_factor
```

**For Each City/Neighborhood:**
- Berlin neighborhoods: Scale rent values
- Leipzig neighborhoods: Scale rent values  
- Munich neighborhoods: Scale rent values

**Implementation Steps:**
1. Add calibration data loader
2. Calculate adjustment factors per cell
3. Apply to initialization code
4. Verify adjusted values match real data
5. Document adjustments made

**Output**: Updated simulation with calibrated rents

---

## 👥 Phase 3: Population Scaling (Week 2)

### Step 3.1: Determine Population Measurement Unit
**Goal**: Know what "867 residents" actually represents

**Investigation Steps:**
1. Review simulation documentation
2. Check database field definitions
3. Look at how population is used in calculations
4. Compare to real city populations
5. Determine scaling factor

**Possible Answers:**
- Option A: 867 people total per city (obviously wrong)
- Option B: 867 per grid cell × number of cells = total (more likely)
- Option C: 867 aggregate units = needs conversion table
- Option D: 867 households × household size = total

**Code to Find Truth:**
```python
# diagnostics/understand_population.py
# Count number of grid cells
cells = query_database("SELECT COUNT(DISTINCT grid_cell_id) FROM simulation_state")

# Check population column
pop = query_database("SELECT population FROM simulation_state WHERE city='berlin'")

# Calculate implied residents
implied_residents = pop * cells * household_size_factor

# Compare to real Berlin population
real_berlin = 3_800_000
scaling_factor = real_berlin / implied_residents
```

**Output**: Documentation explaining population measurement

---

### Step 3.2: Establish Population Scaling Factors
**Goal**: Convert simulation units to actual residents

**For Each City:**
```
Berlin
  Real metro population: 3,800,000
  Simulation value: 867 (per timestep? per cell?)
  Scaling factor: 3,800,000 / X = Y
  
Leipzig
  Real metro population: 1,200,000
  Simulation value: 705
  Scaling factor: 1,200,000 / X = Y
  
Munich
  Real metro population: 2,700,000
  Simulation value: 970
  Scaling factor: 2,700,000 / X = Y
```

**Update Code:**
```python
# src/core_engine/simulation_engine.py

POPULATION_SCALING_FACTORS = {
    'berlin': 4386,    # 867 × 4386 = 3.8M (approximate)
    'leipzig': 1702,   # 705 × 1702 = 1.2M
    'munich': 2784,    # 970 × 2784 = 2.7M (approximate)
}

def get_real_population(simulation_pop, city):
    return simulation_pop * POPULATION_SCALING_FACTORS[city]
```

**Output**: Scaling factors applied to all population calculations

---

## 🗺️ Phase 4: Geographic Heterogeneity (Week 3)

### Step 4.1: Define Geographic Zones
**Goal**: Classify neighborhoods into zones with different characteristics

**Zone Definition (Per City):**
```
ZONE 1: CITY CENTER
- Berlin: Mitte, Kreuzberg, Friedrichshain
- Distance to center: 0-3 km
- Characteristics: High density, excellent transit, many jobs, expensive rents
- Population: 200,000-300,000

ZONE 2: INNER CITY
- Berlin: Charlottenburg, Pankow, Neukölln (inner)
- Distance to center: 3-8 km
- Characteristics: Mixed residential/commercial, good transit, moderate rents
- Population: 400,000-500,000

ZONE 3: MID-RING
- Berlin: Charlottenburg (outer), Spandau (inner), Lichtenberg (inner)
- Distance to center: 8-15 km
- Characteristics: Mostly residential, bus/train, moderate-low rents
- Population: 300,000-400,000

ZONE 4: SUBURBS
- Berlin: Spandau, Lichtenberg (outer), Köpenick
- Distance to center: 15+ km
- Characteristics: Car-dependent, limited transit, cheap rents
- Population: 200,000-300,000
```

**Code to Implement:**
```python
# src/data_pipeline/geographic_zones.py

ZONE_DEFINITIONS = {
    'berlin': {
        'zone_1': {
            'neighborhoods': ['Mitte', 'Kreuzberg', 'Friedrichshain'],
            'distance_km': (0, 3),
            'rent_multiplier': 1.0,  # baseline
            'transit_quality': 5,  # 1-5 scale
            'job_density': 'high',
        },
        'zone_2': {
            'neighborhoods': [...],
            'distance_km': (3, 8),
            'rent_multiplier': 0.85,
            'transit_quality': 4,
            'job_density': 'moderate',
        },
        # ... etc
    }
}

# Map grid cells to zones
def assign_zone_to_cell(grid_cell_id, city):
    # Returns: zone_1, zone_2, zone_3, or zone_4
    pass
```

**Output:** Zone assignment for each grid cell

---

### Step 4.2: Add Amenity Scoring by Zone
**Goal**: Quantify what makes locations different

**Amenity Factors:**
```
For each zone, calculate:
- Transit score (0-100): How many subway/bus stops nearby?
- Walk score (0-100): How walkable for shopping/food?
- Job density: How many jobs within commute distance?
- School quality: Average school ratings in zone
- Parks/green space: Hectares per capita
- Restaurant/cafe density: Per 1,000 residents
- Nightlife score: Bars, clubs, entertainment venues
- Safety score: Crime statistics

EXAMPLE (Berlin):
Zone 1 (Mitte):     Transit 95, Walk 92, Jobs high, Parks low, Nightlife 9/10
Zone 2 (Charlottenburg): Transit 75, Walk 70, Jobs moderate, Parks high, Nightlife 5/10
Zone 3 (Lichtenberg inner): Transit 60, Walk 50, Jobs low, Parks moderate, Nightlife 3/10
Zone 4 (Suburbs):   Transit 30, Walk 20, Jobs very low, Parks high, Nightlife 1/10
```

**Code:**
```python
# src/data_pipeline/amenity_scoring.py

def calculate_amenity_score(zone):
    transit_score = count_transit_stops_nearby(zone)
    walk_score = calculate_walkability(zone)
    job_score = count_nearby_jobs(zone)
    park_hectares = calculate_park_area(zone)
    restaurant_count = count_restaurants(zone)
    
    total_amenity = (transit_score * 0.3 + 
                     walk_score * 0.2 + 
                     job_score * 0.2 + 
                     park_hectares * 0.1 + 
                     restaurant_count * 0.2)
    
    return total_amenity
```

**Output**: Amenity scores by zone → affects rent in simulation

---

### Step 4.3: Model Rent as Function of Amenities
**Goal**: Rent = f(amenities, distance, location)

**Mathematical Model:**
```
Rent(zone) = Base_Rent × (1 + Amenity_Premium × Amenity_Score - Distance_Discount × Distance)

Example:
Zone 1 Rent = €1,200 × (1 + 0.5 × 0.95 - 0.01 × 2) = €1,200 × 1.44 = €1,728 ✓
Zone 2 Rent = €1,200 × (1 + 0.5 × 0.70 - 0.01 × 6) = €1,200 × 1.29 = €1,548 ✓
Zone 3 Rent = €1,200 × (1 + 0.5 × 0.50 - 0.01 × 11) = €1,200 × 0.84 = €1,008 ✓
Zone 4 Rent = €1,200 × (1 + 0.5 × 0.25 - 0.01 × 20) = €1,200 × 0.51 = €612 ✓

(Numbers adjusted to match real market data)
```

**Code Implementation:**
```python
# src/core_engine/rent_model.py

def calculate_rent(zone, amenity_score, distance_km, base_rent=1200):
    amenity_premium = 0.5  # 50% of amenity score contributes to rent
    distance_discount = 0.01  # 1% per km from center
    
    rent = base_rent * (1 + 
                        amenity_premium * amenity_score - 
                        distance_discount * distance_km)
    
    return max(min_rent, min(rent, max_rent))  # Keep within bounds
```

**Testing:**
```python
# Verify model produces realistic rents
assert zone_1_rent > zone_2_rent > zone_3_rent > zone_4_rent
assert zone_1_rent ≈ €1,600  # Real market
assert zone_2_rent ≈ €1,200
assert zone_3_rent ≈ €950
assert zone_4_rent ≈ €700
```

**Output**: Rent model that varies by location (fixes "all same rent" problem)

---

## 👥 Phase 5: Demographic Heterogeneity (Week 3)

### Step 5.1: Define Demographic Segments
**Goal**: Break population into groups with different needs

**Income-Based Segments:**
```
Low-income: €1,000-€1,600/mo salary
  - Can afford: €500-€700/mo rent (30-50% rule)
  - Preferred locations: Zone 3-4 (affordable)
  - Risk: Displacement if rent increases
  - Policy sensitivity: High (housing matters most)

Middle-income: €2,000-€3,000/mo salary
  - Can afford: €700-€1,200/mo rent
  - Preferred locations: Zone 2-3
  - Risk: Moderate (can move if needed)
  - Policy sensitivity: Moderate

High-income: €4,000+ /mo salary
  - Can afford: €1,600+/mo rent
  - Preferred locations: Zone 1-2
  - Risk: Low (can afford anywhere)
  - Policy sensitivity: Low (policies don't affect them much)
```

**Household Types:**
```
Single: 30% of population
  - Prefer: Small apartments (1BR), Zone 1-2, near nightlife/jobs
  - Rent budget: €600-€1,200
  
Couples (no kids): 25% of population
  - Prefer: 1-2BR, Zone 1-2, walkable areas
  - Rent budget: €800-€1,400

Families (1-2 kids): 25% of population
  - Prefer: 2-3BR, Zone 2-3, schools nearby, parks
  - Rent budget: €1,000-€1,500

Large families (3+ kids): 5% of population
  - Prefer: 3+ BR, Zone 3-4, affordable
  - Rent budget: €1,200-€1,500

Retirees: 15% of population
  - Prefer: 1-2BR, Zone 2-3, safe, accessible
  - Rent budget: €600-€1,200
```

**Code:**
```python
# src/database/demographic_model.py

DEMOGRAPHIC_SEGMENTS = {
    'low_income': {
        'salary_range': (1000, 1600),
        'rent_budget': 500,
        'preferred_zones': [3, 4],
        'population_share': 0.25,
    },
    'middle_income': {
        'salary_range': (2000, 3000),
        'rent_budget': 900,
        'preferred_zones': [2, 3],
        'population_share': 0.50,
    },
    'high_income': {
        'salary_range': (4000, 10000),
        'rent_budget': 1800,
        'preferred_zones': [1, 2],
        'population_share': 0.25,
    },
}

# Similar structure for household types, age groups, etc.
```

**Output**: Demographic segmentation model

---

### Step 5.2: Model Demographic-Specific Responses
**Goal**: Calculate policy impacts per demographic group

**Logic:**
```python
# src/core_engine/demographic_responses.py

def calculate_demographic_impact(policy, demographic_segment, location):
    """
    Policy impact varies by: demographic + location
    """
    
    # Housing subsidy policy
    if policy == 'housing_subsidy':
        if demographic_segment == 'low_income':
            return 'high_positive'  # Critical benefit
        elif demographic_segment == 'middle_income':
            return 'moderate_positive'  # Some help
        elif demographic_segment == 'high_income':
            return 'neutral'  # Doesn't need it
    
    # Transit investment policy
    if policy == 'transit_investment':
        if location == 'zone_4':
            return 'high_positive'  # Game-changing
        elif location == 'zone_1':
            return 'low_positive'  # Already good transit
    
    # Green space policy
    if policy == 'green_space':
        if household_type == 'family_with_kids':
            return 'high_positive'
        elif household_type == 'single':
            return 'low_positive'
    
    # Returns: high_positive, moderate_positive, low_positive, neutral, etc.
```

**Output**: Policy impact matrix (policy × demographic × location)

---

## 🔄 Phase 6: Re-Run Policy Scenarios (Week 4)

### Step 6.1: Execute Recalibrated Simulations
**Goal**: Run all 5 policy scenarios with corrected model

**Baseline First:**
```python
# run_baseline_calibrated.py
# Parameters: calibrated rent, populations, zones, demographics
# Run simulation for 50 timesteps
# Output: metrics for all 3 cities
# Compare to real-world trends (2020→2024)
```

**Policy Scenarios (5x):**
```python
# Scenario 1: Housing Subsidy (already calibrated)
# Scenario 2: Transit Investment (already calibrated)
# Scenario 3: Green Infrastructure (already calibrated)
# Scenario 4: Combined Policy (already calibrated)
# Scenario 5: Baseline (control, no policy)
```

**Compare Results:**
```
OLD (UNCALIBRATED):
Berlin + Combined Policy: €2,941 → €2,352 (-€588 rent)

NEW (CALIBRATED):
Berlin + Combined Policy: €1,350 → €1,080 (-€270 rent)
  Zone 1 impact: €1,728 → €1,382 (-€346) [high-income affected]
  Zone 2 impact: €1,548 → €1,238 (-€310) [middle-income affected]
  Zone 3 impact: €1,008 → €806 (-€202) [low-income affected]
  Zone 4 impact: €612 → €489 (-€123) [very low-income affected]
```

**Output**: New policy scenario results by city, zone, demographic

---

### Step 6.2: Calculate Geographic & Demographic Impacts
**Goal**: Show who benefits and who loses from each policy

**Example Output:**
```
HOUSING SUBSIDY POLICY IMPACT (Calibrated)

By Income Level:
  Low-income: Saves €270/mo (critical for staying)
  Middle-income: Saves €270/mo (helpful)
  High-income: No impact (doesn't use subsidy)

By Location (Berlin):
  Zone 1 (Center): -€346/mo rent impact
  Zone 2 (Inner): -€310/mo rent impact
  Zone 3 (Mid-ring): -€202/mo rent impact
  Zone 4 (Suburbs): -€123/mo rent impact

By Household Type:
  Families: High benefit (larger apartments cheaper)
  Singles: Moderate benefit
  Retirees: Moderate benefit

Geographic Displacement:
  Zone 1: Some middle-income move to Zone 2
  Zone 2: Some low-income move to Zone 3
  Zone 3: Some very low-income move to Zone 4 or out of city

Result: -8% displacement risk (matches simulation), but now we know WHO and WHERE
```

**Code:**
```python
# analysis/demographic_policy_impact.py

def analyze_policy_by_demographic(policy_scenario, calibrated_results):
    """
    Break down policy impacts by income, household type, location
    """
    
    for demographic_segment in SEGMENTS:
        for location_zone in ZONES:
            impact = calculate_impact(policy_scenario, demographic_segment, location_zone)
            print(f"{policy_scenario} + {demographic_segment} + {location_zone} = {impact}")
```

**Output**: Detailed policy impact matrix

---

## 📊 Phase 7: Validate Against Real Data (Week 4)

### Step 7.1: Compare Simulation to Recent Trends
**Goal**: Does model predict 2020→2024 reality?

**Real Data to Collect:**
- Berlin: Population 2020 vs 2024, rent 2020 vs 2024
- Leipzig: Population 2020 vs 2024, rent 2020 vs 2024
- Munich: Population 2020 vs 2024, rent 2020 vs 2024

**Validation Test:**
```
Berlin Real Trends (2020→2024):
- Population change: +2% (minor growth)
- Rent change: +15% (inflation + demand)

Berlin Simulation (2020→2024 equivalent):
- Population change: +5% (different from reality)
- Rent change: +20% (somewhat matches reality)

Result: Simulation population is off, rent trend is reasonable
Action: Adjust population growth drivers if possible
```

**Code:**
```python
# validation/compare_to_real_trends.py

real_data_2020_2024 = load_real_city_trends()
simulated_2020_2024 = load_simulation_results()

for city in ['berlin', 'leipzig', 'munich']:
    pop_diff = abs(real_data[city]['pop_change'] - simulated[city]['pop_change'])
    rent_diff = abs(real_data[city]['rent_change'] - simulated[city]['rent_change'])
    
    if pop_diff > 5%:
        print(f"⚠️ {city} population trend doesn't match reality")
    if rent_diff > 10%:
        print(f"⚠️ {city} rent trend doesn't match reality")
```

**Output**: Validation report showing accuracy

---

### Step 7.2: Get Expert Review
**Goal**: Have domain experts validate assumptions

**Experts to Consult:**
- Urban planner (Berlin, Leipzig, Munich)
- Real estate economist
- Demographer (population trends)
- Housing policy specialist
- City government representatives

**Questions for Experts:**
1. Do our geographic zones match reality?
2. Are our demographic breakdowns correct?
3. Do rent-amenity relationships make sense?
4. Are policy impacts plausible?
5. What are we missing?

**Output**: Expert feedback + adjustments

---

## 📝 Phase 8: Update Documentation (Week 5)

### Step 8.1: Update Analysis Documents
**Files to Update:**

1. **ANALYSIS_REPORT_3CITIES.md**
   - Old: "Berlin 867 residents, €2,941/mo"
   - New: "Berlin ~3.8M residents, €1,350-€1,728/mo by zone"

2. **POLICY_TESTING_COMPLETE.md**
   - Remove preliminary warnings
   - Add real numbers with confidence levels
   - Show geographic/demographic breakdown

3. **POLICY_ANALYSIS_SUMMARY.md**
   - New policy recommendations based on calibrated data
   - Zone-specific strategies
   - Demographic equity analysis

4. **SESSION_COMPLETE.md**
   - Mark as "VALIDATED" instead of "PRELIMINARY"
   - Explain what changed vs. first analysis

5. **README_UPDATED.md**
   - Updated numbers and confidence levels
   - Remove calibration roadmap (completed)

---

### Step 8.2: Create Validation Report
**New Document:** `CALIBRATION_VALIDATION_REPORT.md`

Contains:
- What was fixed (rent, population, geography, demographics)
- How it was fixed (methodology)
- Confidence levels (±5%, ±10%, ±20%)
- Comparison old vs. new numbers
- Expert review feedback
- Remaining limitations

---

## 🎯 Implementation Order

**Week 1 (Audit):**
- [ ] Day 1-2: Review simulation code
- [ ] Day 3-4: Extract baseline values
- [ ] Day 5: Map grid to real geography

**Week 2 (Rent + Population):**
- [ ] Day 6-7: Collect real rent data
- [ ] Day 8: Compare and calibrate rent
- [ ] Day 9-10: Determine population scaling

**Week 3 (Geography + Demographics):**
- [ ] Day 11-12: Define zones and amenities
- [ ] Day 13-14: Model rent by location
- [ ] Day 15: Define demographic segments

**Week 4 (Simulation):**
- [ ] Day 16-17: Re-run policy scenarios
- [ ] Day 18-19: Calculate demographic impacts
- [ ] Day 20: Validate against real data

**Week 5 (Documentation):**
- [ ] Day 21-22: Update analysis documents
- [ ] Day 23-24: Expert review and adjustments
- [ ] Day 25: Final validation report

---

## 📊 Expected Outcomes

**After Calibration, Policy Recommendations Should Change To:**

### Berlin (from Combined to Maybe Different)
- Real rent baseline: €1,350 not €2,941
- Real population: 3.8M not 867
- Policies impact zones differently
- Geographic strategy needed (invest in expensive zones? Or affordable zones?)

### Leipzig (from Housing-First to Validated)
- Real rent baseline: €1,000 not €3,050
- Real affordability crisis severity changes
- Housing subsidy still likely best first step
- But amount needed is different

### Munich (from Combined to Maybe Different)
- Real rent baseline: €2,000 not €3,004
- Real population: 2.7M not 970
- Already most affordable of 3 cities
- Different policies might be optimal

### Key Changes Expected:
- ✅ Population numbers (actual people instead of mystery units)
- ✅ Rent values (match real 2024 market)
- ✅ Geographic impacts (who benefits by location)
- ✅ Demographic impacts (who benefits by income/household)
- ✅ Policy priorities (maybe different than first analysis)
- ✅ Budget allocation (different for each city/zone)
- ✅ Confidence levels (specified ±X%)

---

## 📅 Timeline Summary

| Week | Phase | Deliverable | Status |
|------|-------|-------------|--------|
| 1 | Audit | Architecture doc | ⏳ TODO |
| 2 | Calibration | Rent + population fixed | ⏳ TODO |
| 3 | Geography + Demographics | Zone model + segments | ⏳ TODO |
| 4 | Simulation | Recalibrated results | ⏳ TODO |
| 5 | Validation | Final reports + expert review | ⏳ TODO |

**After Week 5**: Ready to present VALIDATED findings to stakeholders

---

## 🔗 Related Documents

- [CRITICAL_FINDINGS_DATA_CALIBRATION.md](CRITICAL_FINDINGS_DATA_CALIBRATION.md) - Problem statement
- [README_UPDATED.md](README_UPDATED.md) - High-level overview
- [POLICY_TESTING_COMPLETE.md](POLICY_TESTING_COMPLETE.md) - Current (preliminary) findings
- [SESSION_COMPLETE.md](SESSION_COMPLETE.md) - Session notes

---

*Document Created: January 16, 2026*  
*Purpose: Detailed roadmap for recalibrating simulations*  
*Next Step: Begin Week 1 (Audit phase)*
