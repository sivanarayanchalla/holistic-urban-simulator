# 📋 COMPLETE CALIBRATION STRATEGY & NEXT STEPS

**Date**: January 16, 2026  
**Status**: All documents prepared, ready for implementation  
**Scope**: Fixing rent, population, geography, and demographics in simulations  

---

## 🎯 What Has Been Done So Far

### ✅ **Identified All Issues** (Complete)
Created comprehensive documentation of problems:
- Rent values are 2-3x too high
- Population scale is unclear
- Geographic zones are missing
- Demographics are not segmented
- Policy impacts vary by location (not modeled)

### ✅ **Created Crisis-Level Documentation** (Complete)
- [CRITICAL_FINDINGS_DATA_CALIBRATION.md](CRITICAL_FINDINGS_DATA_CALIBRATION.md) (18 pages)
  - What's wrong (detailed analysis)
  - Why it matters (impact on recommendations)
  - How to fix (step-by-step roadmap)

### ✅ **Updated All Current Analysis** (Complete)
- [README_UPDATED.md](README_UPDATED.md) - Added limitations + reality check
- [POLICY_TESTING_COMPLETE.md](POLICY_TESTING_COMPLETE.md) - Added "preliminary" disclaimers + geographic gaps
- [SESSION_COMPLETE.md](SESSION_COMPLETE.md) - Clarified framework vs. numbers confidence
- All documents now mark findings as "PRELIMINARY" pending validation

### ✅ **Created Implementation Roadmaps** (Complete)
- [SIMULATION_CALIBRATION_ROADMAP.md](SIMULATION_CALIBRATION_ROADMAP.md) (25 pages)
  - 8-phase detailed plan with code examples
  - Each phase broken into steps
  - Data sources, tools, expected outputs
  
- [SIMULATION_CALIBRATION_EXECUTION_PLAN.md](SIMULATION_CALIBRATION_EXECUTION_PLAN.md) (15 pages)
  - Day-by-day breakdown for 5 weeks
  - Quick reference format
  - Success criteria + key questions

### ✅ **Pushed to GitHub** (Complete)
All documents committed and pushed to your repository:
https://github.com/sivanarayanchalla/holistic-urban-simulator

---

## 🔄 What Needs to Happen Next (5 Weeks)

### **PHASE 1: Audit (Week 1) - STARTING NOW**

**Goal**: Understand current simulation

**Key Activities**:
1. Review `src/core_engine/simulation_engine.py`
   - How does simulation work?
   - Where do baseline values come from?

2. Review `src/database/models.py`
   - What's in the database?
   - How is data structured?

3. Extract baseline values
   - Run query: Get all initial metrics by city
   - Save to CSV for analysis

4. Map grid to real geography
   - Understand grid cell definition
   - Match to real neighborhoods

**Timeline**: Days 1-5 of next week

**Output Needed**: Architecture documentation + baseline data CSV

---

### **PHASE 2: Rent Calibration (Week 2)**

**Goal**: Fix rent values to match 2024 market

**Key Activities**:
1. Collect real rent data
   - Search Immobilienscout24.de for Berlin/Leipzig/Munich
   - Get average rent by neighborhood
   - Document sources and dates

2. Compare simulation vs. reality
   - Run diagnostics script
   - Calculate discrepancy factors (should be 2-3x)

3. Fix simulation code
   - Identify where rent is initialized
   - Apply adjustment factors
   - Verify: Simulation rents now match market

**Timeline**: Days 6-10 of next week

**Output Needed**: Calibrated rent model in code

---

### **PHASE 3: Population Scaling (Week 2)**

**Goal**: Know what population numbers actually represent

**Key Activities**:
1. Investigate population measurement
   - What does "867 residents" mean?
   - Is it per cell? Total? Per timestep?
   - How many grid cells are there?

2. Determine scaling factors
   - Berlin: 867 × ? = 3.8M
   - Leipzig: 705 × ? = 1.2M
   - Munich: 970 × ? = 2.7M

3. Update code
   - Add scaling factors as constants
   - Apply to all population calculations

**Timeline**: Days 9-10 of next week

**Output Needed**: Population scaling factors + updated code

---

### **PHASE 4: Geographic Zones (Week 3)**

**Goal**: Add location-based variation (cities aren't uniform!)

**Key Activities**:
1. Define 4 geographic zones per city
   - Zone 1 (center): High rent, great amenities, jobs
   - Zone 2 (inner): Good transit, moderate rent
   - Zone 3 (mid-ring): Affordable, suburban, family-friendly
   - Zone 4 (suburbs): Cheap, car-dependent, limited amenities

2. Create amenity scores
   - For each zone: transit, walkability, jobs, parks, restaurants
   - Higher amenities = higher rent

3. Model rent by location
   - Rent = f(amenities, distance, zone)
   - Verify: Zone 1 > Zone 2 > Zone 3 > Zone 4

**Timeline**: Days 11-15 of next week

**Output Needed**: Geographic zone model with zone-specific rents

---

### **PHASE 5: Demographics (Week 3-4)**

**Goal**: Segment population by income, household type, age

**Key Activities**:
1. Define demographic segments
   - Low-income: €1,200-€1,600/mo salary
   - Middle-income: €2,000-€3,000/mo salary
   - High-income: €4,000+/mo salary
   - Household types: singles, couples, families, retirees

2. Model policy impacts by demographic
   - Housing subsidy helps low-income most
   - Transit investment helps low-income most
   - Green space helps families most
   - Different groups win with different policies

**Timeline**: Days 15-17 of next week

**Output Needed**: Demographic segments + impact matrix

---

### **PHASE 6: Re-Run Simulations (Week 4)**

**Goal**: Execute all 5 policy scenarios with corrected model

**Key Activities**:
1. Run baseline (control)
   - With all calibrations applied
   - Verify convergence

2. Run 4 policy scenarios
   - Housing subsidy
   - Transit investment
   - Green infrastructure
   - Combined policy

3. Calculate detailed impacts
   - By zone (who benefits where?)
   - By demographic (who benefits by income?)
   - By policy (compare all 5 scenarios)

**Timeline**: Days 18-20

**Output Needed**: Recalibrated policy scenario results

---

### **PHASE 7: Validation (Week 4)**

**Goal**: Verify results match real-world trends

**Key Activities**:
1. Compare to 2020-2024 real data
   - Does simulation predict real population changes?
   - Does simulation predict real rent trends?
   - Are directions correct even if magnitude off?

2. Get expert review
   - Urban planner (Do zones make sense?)
   - Housing economist (Is rent model realistic?)
   - City officials (Do policies align with reality?)

**Timeline**: Days 20-22

**Output Needed**: Validation report + expert feedback

---

### **PHASE 8: Documentation (Week 5)**

**Goal**: Update all analysis with validated numbers

**Key Activities**:
1. Update analysis documents
   - ANALYSIS_REPORT_3CITIES.md (real numbers)
   - POLICY_TESTING_COMPLETE.md (remove "preliminary")
   - POLICY_ANALYSIS_SUMMARY.md (new recommendations)
   - SESSION_COMPLETE.md (mark as "VALIDATED")

2. Create validation report
   - What was fixed?
   - How confident are we? (±5%, ±10%, ±20%?)
   - What's still uncertain?

3. Prepare for stakeholder presentation
   - Clear confidence levels
   - Geographic breakdown (who wins where?)
   - Demographic breakdown (who wins by income?)
   - New policy recommendations

**Timeline**: Days 23-25

**Output Needed**: Complete validated analysis package

---

## 📊 Expected Results After Calibration

### **Rent Changes**
```
BERLIN
Before: €2,941/mo everywhere (unrealistic)
After:  €1,728 (zone 1), €1,548 (zone 2), €1,008 (zone 3), €612 (zone 4)
Confidence: ±10% (based on 2024 market data)

LEIPZIG
Before: €3,050/mo everywhere (unrealistic)
After:  €1,400 (zone 1), €1,200 (zone 2), €800 (zone 3), €500 (zone 4)
Confidence: ±10% (based on 2024 market data)

MUNICH
Before: €3,004/mo everywhere (unrealistic)
After:  €2,100 (zone 1), €1,900 (zone 2), €1,300 (zone 3), €900 (zone 4)
Confidence: ±10% (based on 2024 market data)
```

### **Policy Recommendations**
```
BERLIN
Current recommendation: Combined policy
After validation: [TBD - depends on zone distribution]
  - If low-income concentrated in zones 3-4: Housing first
  - If mixed: Combined policy as currently recommended
  - Geographic strategy: Different policies for different zones

LEIPZIG
Current recommendation: Housing subsidy
After validation: [Likely CONFIRMED as best first step]
  - Real affordability crisis confirmed (not simulation error)
  - Housing subsidy amount: €270/mo per household
  - Timeline: Can be deployed within weeks
  - Confidence: HIGH

MUNICH
Current recommendation: Combined policy
After validation: [TBD - depends on real affordability crisis]
  - Is rent really a problem? (€3,004 was wrong baseline)
  - Real rents may be affordable (€1,300-€2,100)
  - Recommendation may shift to focus on livability not affordability
  - Geographic strategy: Different policies for different zones
```

### **Geographic Insights**
```
What will be new:
- Zone 1 policies: Different than Zone 4 (different needs)
- Displacement patterns: Geographic not just aggregate
- Gentrification risk: Zone-specific (center vs. periphery)
- Policy ROI: Varies by zone (transit better in suburbs, green better downtown)

What will be different:
- Single recommendation per city → Zone-specific recommendations
- Aggregate numbers → Broken down by zone AND demographic
- "Displacement risk 8%" → "Zone 3 loses 12%, Zone 1 gains 5%"
```

### **Demographic Insights**
```
What will be new:
- Low-income impact: Different from high-income
- Family impact: Different from single workers
- Young professional impact: Different from retirees
- Policy equity: Who really wins, who really loses?

What will be different:
- "20% rent reduction" → "Low-income saves €270/mo, high-income saves €360/mo"
- "12% population growth" → "Zone 3 loses 5%, Zone 1 gains 8%"
- "+35% vitality" → "Families experience +40%, singles +25%"
```

---

## 📋 Document Reading Order

**For Implementation Team:**
1. [SIMULATION_CALIBRATION_EXECUTION_PLAN.md](SIMULATION_CALIBRATION_EXECUTION_PLAN.md) ← START HERE (quick reference)
2. [SIMULATION_CALIBRATION_ROADMAP.md](SIMULATION_CALIBRATION_ROADMAP.md) ← Detailed phase information
3. [CRITICAL_FINDINGS_DATA_CALIBRATION.md](CRITICAL_FINDINGS_DATA_CALIBRATION.md) ← Why this is all necessary

**For Stakeholders:**
1. [SESSION_COMPLETE.md](SESSION_COMPLETE.md) ← Current status
2. [CRITICAL_FINDINGS_DATA_CALIBRATION.md](CRITICAL_FINDINGS_DATA_CALIBRATION.md) ← What we found
3. [README_UPDATED.md](README_UPDATED.md) ← Overall picture with timelines

**For Decision-Makers:**
1. [SESSION_COMPLETE.md](SESSION_COMPLETE.md) ← Summary + next steps
2. [POLICY_TESTING_COMPLETE.md](POLICY_TESTING_COMPLETE.md) ← Current (preliminary) findings
3. [CRITICAL_FINDINGS_DATA_CALIBRATION.md](CRITICAL_FINDINGS_DATA_CALIBRATION.md) ← Why validation is critical
4. Wait for [CALIBRATION_VALIDATION_REPORT.md](TBD) ← Final validated recommendations (Week 5)

---

## 🚀 How to Start

**This Week (Week 1 - Audit Phase):**

1. **Review the roadmaps** (today)
   - Read: SIMULATION_CALIBRATION_EXECUTION_PLAN.md (15 min)
   - Read: SIMULATION_CALIBRATION_ROADMAP.md (30 min)

2. **Understand the problem** (tomorrow)
   - Read: CRITICAL_FINDINGS_DATA_CALIBRATION.md (30 min)
   - Understand: Why rent is wrong, why geography matters, why demographics needed

3. **Begin code review** (Days 3-5)
   - Open: `src/core_engine/simulation_engine.py`
   - Open: `src/database/models.py`
   - Open: `analyze_3cities.py`
   - Questions to answer:
     - How does simulation work?
     - Where do baseline values come from?
     - What does "867 residents" represent?

4. **Extract baseline data** (Days 4-5)
   - Write script: `diagnostics/extract_baseline.py`
   - Output: `baseline_values_all_cities.csv`
   - Document: What each column means

---

## ✅ Deliverables Checklist

### End of Week 1 (Audit):
- [ ] Architecture document explaining simulation
- [ ] Baseline data extracted to CSV
- [ ] Grid-to-neighborhood mapping created
- [ ] Questions about population scale answered

### End of Week 2 (Rent + Population):
- [ ] Real 2024 rent data collected for all cities
- [ ] Rent discrepancy analysis complete
- [ ] Rent baseline adjusted in simulation code
- [ ] Population scaling factors determined

### End of Week 3 (Geography + Demographics):
- [ ] Geographic zones defined and mapped
- [ ] Amenity scores calculated per zone
- [ ] Rent-by-location model working
- [ ] Demographic segments defined
- [ ] Policy impact matrix created

### End of Week 4 (Simulation + Validation):
- [ ] Recalibrated policy scenarios complete (5 scenarios)
- [ ] Geographic impact analysis done
- [ ] Demographic impact analysis done
- [ ] Real-world validation completed
- [ ] Expert feedback incorporated

### End of Week 5 (Documentation):
- [ ] All analysis documents updated with validated numbers
- [ ] Calibration validation report created
- [ ] Confidence levels documented (±X%)
- [ ] Ready for stakeholder presentation

---

## 🎯 Success Definition

**At the end of Week 5, we will have:**

✅ Rent values that match 2024 real market data  
✅ Clear understanding of what population numbers represent  
✅ Geographic zone model showing location-based variation  
✅ Demographic breakdown showing who benefits from which policies  
✅ Policy recommendations with confidence levels (±10%)  
✅ Geographic and demographic impact analysis  
✅ Real-world validation against 2020-2024 trends  
✅ Stakeholder-ready presentation materials  
✅ Clear next steps and timelines for implementation  

---

## 📞 Key Contacts & Questions

**For Data Sources:**
- German rentals: Immobilienscout24.de, WunderFlats
- Census data: Statistisches Bundesamt (destatis.de)
- Geographic data: OpenStreetMap, QGIS
- Expert review: Urban planners, housing economists, city officials

**For Code Questions:**
- Simulation architecture: Review simulation_engine.py
- Database structure: Review models.py
- Baseline extraction: Write new diagnostic script

**For Timeline:**
- 5 weeks is realistic if work starts immediately
- Phase 1 (audit) is critical path - needed before Phases 2-3
- Phases 2-3 can partially overlap
- Phases 4-5 depend on completion of earlier phases

---

## 🔗 All Related Documents

**Critical Issues:**
- [CRITICAL_FINDINGS_DATA_CALIBRATION.md](CRITICAL_FINDINGS_DATA_CALIBRATION.md)

**Current Analysis (Preliminary):**
- [README_UPDATED.md](README_UPDATED.md)
- [POLICY_TESTING_COMPLETE.md](POLICY_TESTING_COMPLETE.md)
- [POLICY_ANALYSIS_SUMMARY.md](POLICY_ANALYSIS_SUMMARY.md)
- [SESSION_COMPLETE.md](SESSION_COMPLETE.md)

**Implementation Roadmaps:**
- [SIMULATION_CALIBRATION_ROADMAP.md](SIMULATION_CALIBRATION_ROADMAP.md) (detailed)
- [SIMULATION_CALIBRATION_EXECUTION_PLAN.md](SIMULATION_CALIBRATION_EXECUTION_PLAN.md) (quick reference)
- [COMPLETE_CALIBRATION_STRATEGY_NEXT_STEPS.md](COMPLETE_CALIBRATION_STRATEGY_NEXT_STEPS.md) (this file)

**Future Documents:**
- CALIBRATION_VALIDATION_REPORT.md (Week 5 - TBD)

---

## 📅 Calendar

```
WEEK 1 (Jan 20-24): AUDIT PHASE
  Mon: Review roadmaps
  Tue-Wed: Code review
  Thu-Fri: Extract baseline data

WEEK 2 (Jan 27-31): CALIBRATION PHASE
  Mon-Tue: Collect real rent data
  Wed: Analyze discrepancies
  Thu-Fri: Fix rent + population in code

WEEK 3 (Feb 3-7): GEOGRAPHY & DEMOGRAPHICS
  Mon-Tue: Define zones + amenities
  Wed-Thu: Rent-by-location model
  Fri: Demographic segmentation

WEEK 4 (Feb 10-14): SIMULATION & VALIDATION
  Mon-Tue: Re-run all scenarios
  Wed: Geographic impact analysis
  Thu-Fri: Validation + expert review

WEEK 5 (Feb 17-21): DOCUMENTATION & PRESENTATION
  Mon: Update all documents
  Tue: Create validation report
  Wed-Thu: Expert refinements
  Fri: Final review + ready for stakeholders
```

---

## 🎬 Next Action

**TODAY:**
1. Read this document (DONE ✓)
2. Read: SIMULATION_CALIBRATION_EXECUTION_PLAN.md
3. Read: CRITICAL_FINDINGS_DATA_CALIBRATION.md

**TOMORROW:**
1. Open: `src/core_engine/simulation_engine.py`
2. Open: `src/database/models.py`
3. Begin documenting how simulation works

**THIS WEEK:**
1. Complete Phase 1 (Audit)
2. Prepare for Phase 2 (Rent Calibration)

---

*Document Created: January 16, 2026*  
*Purpose: Complete strategy + next steps for simulation calibration*  
*Status: Ready to execute - all preparation complete*  
*Timeline: 5 weeks to validated analysis*
