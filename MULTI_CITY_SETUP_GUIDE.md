# Multi-City Urban Simulator Setup Guide

## Step-by-Step Instructions

### Step 1: Fetch Data for Additional German Cities

The new data fetcher supports Leipzig, Berlin, Munich, Hamburg, and Cologne.

```bash
python src/data_pipeline/fetch_german_cities_data.py
```

This will:
- Fetch urban data from OpenStreetMap for each city
- Extract: landuse zones, POIs (schools, hospitals, shops), transport networks
- Generate EV charging infrastructure placement
- Save all data to the database

**Expected output:**
```
[*] City Data Fetcher Initialized
   City: Berlin, Germany
   Population: 3,645,000
   Data Directory: data/raw/berlin
   
[OK] Landuse data: 1,245 features
[OK] POIs: 8,932 locations
[OK] Transport network: 12,456 road segments
[OK] EV chargers: 245 locations
[OK] Berlin data saved successfully
```

**Time estimate:** 15-30 minutes per city (depends on OSM API)

---

### Step 2: Run Simulations for Each City

Once data is fetched, run multi-city simulations:

```bash
python run_multi_city_simulation.py
```

This will:
1. Run simulation for Leipzig (existing data)
2. Run simulation for Berlin
3. Run simulation for Munich
4. Track all results

**Expected output:**
```
======================================================================
MULTI-CITY SIMULATION SUITE
Cities: Leipzig, Germany; Berlin, Germany; Munich, Germany
======================================================================

======================================================================
SIMULATING: Leipzig, Germany
======================================================================

[*] Starting simulation for Leipzig...
✅ Simulation completed for Leipzig
Run ID: 2b4c0ad3-3f90-4f51-af40-4c48952b5db4

======================================================================
SIMULATING: Berlin, Germany
======================================================================

[*] Starting simulation for Berlin...
✅ Simulation completed for Berlin
Run ID: a8f5d9c2-7e3b-4a6d-9f2c-1a9d4e5c6f7b

======================================================================
SIMULATING: Munich, Germany
======================================================================

[*] Starting simulation for Munich...
✅ Simulation completed for Munich
Run ID: b1f2c3d4-5e6f-7g8h-9i0j-1k2l3m4n5o6p
```

**Time estimate:** 5-10 seconds per city (very fast!)

---

### Step 3: Run Analysis Suite for Multi-City Comparison

Now that you have simulations for multiple cities, run the comprehensive analyses:

```bash
python analyze_policy_impact.py
python analyze_gentrification.py
python analyze_infrastructure_impact.py
python analyze_neighborhood_spillovers.py
python analyze_multi_city.py
```

Or run all together:
```bash
python VALIDATION_REPORT.py
```

**Expected output:**
```
============================================================
🌍 MULTI-CITY COMPARISON FRAMEWORK
============================================================

✅ Found 13 simulation runs
   Cities: Leipzig, Berlin, Munich

📊 Creating comparison visualizations...

✅ Multi-city comparison: data/outputs/visualizations/multi_city_comparison.html
✅ Inequality comparison: data/outputs/visualizations/multi_city_inequality.html
✅ Performance matrix: data/outputs/visualizations/city_performance_matrix.html
```

**Time estimate:** 2-3 minutes total

---

### Step 4: View Interactive Dashboards

Open the generated HTML files in your browser:

```
data/outputs/visualizations/
├── multi_city_comparison.html         (Radar chart comparing all cities)
├── multi_city_inequality.html         (Gini coefficient comparison)
├── city_performance_matrix.html       (Heatmap of normalized metrics)
├── policy_impact_analysis.html        (Policy effects)
├── gentrification_risk_map.html       (Gentrification risk by neighborhood)
├── infrastructure_impact_comparison.html (Infrastructure effects)
└── performance_gradient.html          (Spatial effects)
```

---

## What Gets Compared Across Cities?

### 1. **Urban Metrics**
- Population (attracted by infrastructure and policies)
- Rent (influenced by gentrification, policies, EV access)
- Employment (driven by schools, hospitals, transit)
- Safety (improved by policies and healthcare)
- Air quality (improved by transit and green space)
- Commercial vitality (driven by population and amenities)

### 2. **Policy Effectiveness**
Different cities may show different policy impacts:
- EV subsidy effectiveness (varies by existing charger coverage)
- Progressive tax impact (varies by income distribution)
- Green space mandate (varies by available land)
- Transit investment ROI (varies by existing network)

### 3. **Gentrification Risk**
Identifies neighborhoods in each city at risk of:
- Rapid rent escalation
- Population displacement
- Neighborhood character change

### 4. **Spatial Spillovers**
Shows how effects ripple between neighborhoods:
- Prosperity spreading from high-value areas
- Safety changes diffusing through city
- Air quality gradients
- Agglomeration clusters (high-density areas)

### 5. **Infrastructure Efficiency**
Compares how effectively each city uses:
- School facilities (population bonus)
- Hospital coverage (safety and employment boost)
- EV charging network (affordability benefits)

---

## File Structure Created

```
src/data_pipeline/
├── fetch_german_cities_data.py        (Generic city data fetcher)
│                                       - Supports: Leipzig, Berlin, Munich, Hamburg, Cologne
│                                       - Fetches: landuse, POIs, transport, EV infrastructure
│
run_multi_city_simulation.py             (Runs simulations for all cities)
│                                        - Calls run_simulation.py for each city
│                                        - Tracks run IDs and timestamps
│
src/core_engine/simulation_engine.py     (Updated for city parameter)
│                                        - main(city='Leipzig', ...) now accepts city
│                                        - UrbanModel(city_name=...) tracks city
│
analyze_multi_city.py                    (Enhanced multi-city comparisons)
│                                        - Multi-city radar chart
│                                        - Gini coefficient comparisons
│                                        - Performance matrix heatmap
│
data/raw/
├── leipzig/                  (Existing)
├── berlin/                   (New - created by fetch script)
├── munich/                   (New - created by fetch script)
└── hamburg/                  (Optional - can be added later)
│
data/outputs/
├── visualizations/
│   ├── multi_city_*.html     (New - multi-city comparisons)
│   └── policy_*.html         (Existing - per-city analyses)
```

---

## Optional: Add More Cities

To add another city (e.g., Hamburg or Cologne):

1. Edit `fetch_german_cities_data.py`:
   - City is already defined in `CITY_CONFIGS` dictionary
   - Just need to update `main()` function to include it

2. Edit `run_multi_city_simulation.py`:
   - Add city to `CITIES` dictionary

That's it! The framework is already set up for extensibility.

---

## Troubleshooting

**Issue: OSM data fetch timeout**
- Solution: Run one city at a time, wait between requests
- Increase timeout in `GermanCityDataFetcher.__init__()`: `ox.settings.timeout = 600`

**Issue: Simulation fails for new city**
- Solution: Check that `spatial_grid` table has cells for that city
- Verify fetch script created grid cells correctly
- Check database logs in PostgreSQL

**Issue: Multi-city comparison shows only one city**
- Solution: Run `analyze_multi_city.py` again after all simulations complete
- Script caches results; delete cache if needed
- Verify all runs have `city_name` set in database

**Issue: Visualizations don't load in browser**
- Solution: Make sure you're opening `.html` files locally (not network drive)
- Use `file://` URL, not HTTP
- Check console for geometry loading errors

---

## Performance Notes

| Operation | Time | Notes |
|-----------|------|-------|
| Fetch city data | 15-30 min | Depends on OSM API response |
| Run 1 simulation | 0.1 sec | Very fast - 50 timesteps × 20 cells |
| Run 3 cities | 0.3 sec | Still negligible |
| Generate 5 analyses | 2-3 min | Database queries + Plotly generation |
| Load comparison HTML | <1 sec | Interactive in browser |

Total end-to-end time: **20-40 minutes** (mostly waiting for OSM data fetch)

---

## Next Steps After Multi-City Setup

1. **Calibrate models** with real urban data
2. **Adjust policy parameters** per city
3. **Create city-specific scenarios** (e.g., "Climate emergency response")
4. **Compare policy effectiveness** across cities
5. **Export results** for municipal planning teams

---

## Questions?

Check the VALIDATION_REPORT.txt for detailed technical architecture and module documentation.
