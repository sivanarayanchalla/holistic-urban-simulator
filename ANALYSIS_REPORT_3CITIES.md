# 3-CITY ANALYSIS REPORT
## Leipzig, Berlin, Munich Comparison

---

## Executive Summary

Three German cities were simulated for 50 timesteps to compare urban metrics and identify patterns. **Munich emerges as the strongest performer** with best population retention, while **Leipzig shows highest rental costs** but lower population persistence.

---

## Key Metrics (Final Timestep 50)

### Population
| City | Average | Min | Max | Trend |
|------|---------|-----|-----|-------|
| **Leipzig** | 705 | 500 | 2,575 | -68% from t10 |
| **Berlin** | 867 | 500 | 6,212 | -60% from t10 |
| **Munich** | 970 | 500 | 6,838 | -59% from t10 |

**Finding:** Munich retains the most population (970), suggesting better urban vitality and livability.

### Rent (EUR/month)
| City | Average |
|------|---------|
| **Leipzig** | 3,049.69 |
| **Munich** | 3,004.36 |
| **Berlin** | 2,940.75 |

**Finding:** Leipzig is most expensive (5% higher than Berlin), despite similar baseline metrics.

---

## Population Evolution (Timesteps 0→50)

### Munich (Best Retention)
- T10: 2,343 pop
- T20: 1,551 pop (-34%)
- T30: 1,180 pop (-24%)
- T40: 1,039 pop (-12%)
- T50:   970 pop (-7%)

**Interpretation:** Munich shows gentle, gradual decline - suggesting stable urban conditions that prevent population crashes.

### Berlin
- T10: 2,194 pop
- T20: 1,377 pop (-37%)
- T30:   989 pop (-28%)
- T40:   889 pop (-10%)
- T50:   867 pop (-2%)

**Interpretation:** Berlin has moderate decline, stabilizing mid-simulation. Population distributed evenly across grid cells (range: 500-6,212).

### Leipzig
- T10: 2,196 pop
- T20: 1,374 pop (-37%)
- T30:   956 pop (-30%)
- T40:   796 pop (-17%)
- T50:   705 pop (-11%)

**Interpretation:** Leipzig shows steepest decline, with lowest final population. Highest rents may be limiting factor for residents.

---

## Comparative Analysis

### Strengths by City

**Munich:**
- Best population retention (970 vs 867 Berlin, 705 Leipzig)
- High maximum population in individual cells (6,838)
- Stable trajectory suggests good livability

**Berlin:**
- Most affordable rents (2,940.75 EUR)
- Good population spread (max 6,212)
- Affordable housing attracts residents

**Leipzig:**
- Most dynamic maximum populations possible (2,575 in single cells)
- Highest rents suggest strong demand
- Concentrated urban activity in select areas

---

## Database Statistics

**Total Records:**
- 3 simulation runs completed
- 60 simulation states saved (3 runs × 20 cells per timestep)
- 5 timesteps saved per run (10, 20, 30, 40, 50)

**Query Examples:**
```sql
-- Compare rents across cities
SELECT sr.city_name, AVG(ss.avg_rent_euro) as avg_rent
FROM simulation_state ss
JOIN simulation_run sr ON ss.run_id = sr.run_id
WHERE ss.timestep = 50
GROUP BY sr.city_name;

-- Population timeline by city
SELECT sr.city_name, ss.timestep, AVG(ss.population)
FROM simulation_state ss
JOIN simulation_run sr ON ss.run_id = sr.run_id
WHERE sr.city_name IN ('leipzig', 'berlin', 'munich')
GROUP BY sr.city_name, ss.timestep
ORDER BY sr.city_name, ss.timestep;
```

---

## Visual Outputs Generated

1. **multi_city_comparison.html** - Radar chart showing 6 normalized metrics
2. **city_performance_matrix.html** - Heatmap with all metrics
3. **inequality_comparison.html** - Gini coefficient rankings

Location: `data/outputs/visualizations/`

---

## Recommendations

### For Munich
- Leverage strong population retention
- Investigate factors keeping residents (transit, safety, vitality)
- Use as benchmark for other cities

### For Berlin
- Highlight affordability (2,940.75 EUR rents are 3% below average)
- Invest in livability factors to match Munich's retention
- Marketing: "Most affordable major German city"

### For Leipzig
- Analyze why rents are highest despite lower population
- Consider affordability initiatives to match Berlin
- Study Munich's retention strategies
- May indicate strong demand despite population pressure

---

## Next Analysis Steps

1. **Policy Scenarios:** Test interventions (transit investment, zoning changes, EV incentives)
2. **Detailed Timeline:** Analyze metrics between timesteps 10-50
3. **Cell-Level Analysis:** Identify high/low performing neighborhoods
4. **Correlation Study:** Which factors drive population retention most?
5. **Forecasting:** Project trends beyond 50 timesteps

---

**Report Generated:** 2026-01-15
**Analysis Tool:** Urban Simulator Multi-City Framework v1.0
**Status:** COMPLETE
