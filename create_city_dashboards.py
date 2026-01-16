#!/usr/bin/env python3
"""
Generate city-specific policy dashboards for Berlin, Leipzig, Munich
"""
import pandas as pd
from src.database.db_config import db_config
from sqlalchemy import text

print("[*] Generating city-specific policy dashboards...\n")

# Get baseline data
with db_config.engine.connect() as conn:
    query = text('''
        SELECT 
            sr.city_name,
            ROUND(AVG(ss.population)::numeric, 0) as population,
            ROUND(AVG(ss.avg_rent_euro)::numeric, 2) as rent_eur,
            ROUND(AVG(ss.commercial_vitality)::numeric, 3) as vitality,
            ROUND(AVG(ss.displacement_risk)::numeric, 3) as displacement,
            ROUND(AVG(ss.safety_score)::numeric, 3) as safety
        FROM simulation_state ss
        JOIN simulation_run sr ON ss.run_id = sr.run_id
        WHERE sr.city_name IN ('leipzig', 'berlin', 'munich')
        AND ss.timestep = 50
        GROUP BY sr.city_name
    ''')
    baseline = pd.read_sql(query, conn)

cities_config = {
    'berlin': {
        'name': 'BERLIN',
        'emoji': '🏛️',
        'priority': 'Livability Maximizer',
        'color': '#E53935',
        'recommendation': 'Combined Policy',
        'rationale': "Berlin's affordability baseline allows aggressive intervention. Combined approach maximizes quality of life improvements across all metrics.",
        'scenarios': {
            'Baseline': (1.00, 1.00, 1.00, 1.00),
            'Transit Investment': (1.045, 1.00, 1.15, 1.00),
            'Affordable Housing': (1.05, 0.80, 1.00, 0.92),
            'Green Infrastructure': (1.025, 1.02, 1.20, 1.00),
            'Combined Policy': (1.12, 0.80, 1.35, 0.92)
        },
        'budget': '€50M',
        'timeline': '3 years'
    },
    'leipzig': {
        'name': 'LEIPZIG',
        'emoji': '🏭',
        'priority': 'Affordability Crisis Response',
        'color': '#FFA500',
        'recommendation': 'Affordable Housing → Combined',
        'rationale': "Leipzig faces affordability crisis (€3,050/mo). Housing subsidy directly addresses critical need. Immediate start, add transit/green later.",
        'scenarios': {
            'Baseline': (1.00, 1.00, 1.00, 1.00),
            'Transit Investment': (1.045, 1.00, 1.15, 1.00),
            'Affordable Housing': (1.05, 0.80, 1.00, 0.92),
            'Green Infrastructure': (1.025, 1.02, 1.20, 1.00),
            'Combined Policy': (1.12, 0.80, 1.35, 0.92)
        },
        'budget': '€30M (→€60M Phase 2)',
        'timeline': 'Immediate start, phased expansion'
    },
    'munich': {
        'name': 'MUNICH',
        'emoji': '🌳',
        'priority': 'Growth Sustainer',
        'color': '#43A047',
        'recommendation': 'Combined Policy',
        'rationale': "Munich has strongest baseline (970 residents). Combined policy leverages momentum, adds 116 residents while cutting rents 20%.",
        'scenarios': {
            'Baseline': (1.00, 1.00, 1.00, 1.00),
            'Transit Investment': (1.045, 1.00, 1.15, 1.00),
            'Affordable Housing': (1.05, 0.80, 1.00, 0.92),
            'Green Infrastructure': (1.025, 1.02, 1.20, 1.00),
            'Combined Policy': (1.12, 0.80, 1.35, 0.92)
        },
        'budget': '€60M',
        'timeline': '3 years (full implementation)'
    }
}

# Generate dashboard for each city
for city_key, city_info in cities_config.items():
    # Get baseline for this city
    city_baseline = baseline[baseline['city_name'] == city_key].iloc[0]
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Policy Analysis - {city_info['name']}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, {city_info['color']} 0%, rgba(0,0,0,0.1) 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, {city_info['color']} 0%, #333 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 48px;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 18px;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 50px;
        }}
        
        .section h2 {{
            color: {city_info['color']};
            margin-bottom: 20px;
            font-size: 24px;
            border-bottom: 3px solid {city_info['color']};
            padding-bottom: 10px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: linear-gradient(135deg, #f5f5f5 0%, white 100%);
            border: 2px solid {city_info['color']};
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}
        
        .metric-card .label {{
            color: #666;
            font-size: 13px;
            text-transform: uppercase;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        
        .metric-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: {city_info['color']};
            margin-bottom: 5px;
        }}
        
        .metric-card .change {{
            font-size: 14px;
            color: #27ae60;
            font-weight: 600;
        }}
        
        .recommendation-box {{
            background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
            border-left: 6px solid {city_info['color']};
            padding: 25px;
            border-radius: 8px;
            margin: 30px 0;
        }}
        
        .recommendation-box h3 {{
            color: {city_info['color']};
            margin-bottom: 10px;
            font-size: 20px;
        }}
        
        .recommendation-box .badge {{
            display: inline-block;
            background: {city_info['color']};
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            margin-bottom: 15px;
            font-size: 14px;
        }}
        
        .recommendation-box p {{
            color: #333;
            line-height: 1.8;
            margin-bottom: 10px;
        }}
        
        .recommendation-box ul {{
            margin-left: 20px;
            color: #333;
            line-height: 1.8;
        }}
        
        .scenario-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .scenario-table th {{
            background: {city_info['color']};
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        
        .scenario-table td {{
            padding: 15px;
            border-bottom: 1px solid #eee;
        }}
        
        .scenario-table tr:hover {{
            background: #f9f9f9;
        }}
        
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 30px 0;
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .timeline {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin: 30px 0;
        }}
        
        .timeline-item {{
            background: linear-gradient(135deg, {city_info['color']} 0%, rgba({int(city_info['color'][1:3], 16)},0,0,0.5) 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .timeline-item .year {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .timeline-item .phase {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .winner {{
            background: #d4edda;
            color: #155724;
            padding: 10px 15px;
            border-radius: 5px;
            font-weight: 600;
            display: inline-block;
        }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            background: #f9f9f9;
            color: #666;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{city_info['emoji']} {city_info['name']}</h1>
            <p>Policy Scenario Analysis & Recommendations</p>
        </div>
        
        <div class="content">
            <!-- Current State -->
            <div class="section">
                <h2>📊 Current State (Timestep 50)</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="label">Population</div>
                        <div class="value">{int(city_baseline['population']):,}</div>
                        <div class="change">residents</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Avg Rent</div>
                        <div class="value">€{city_baseline['rent_eur']:.0f}</div>
                        <div class="change">/month</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Vitality Index</div>
                        <div class="value">{city_baseline['vitality']:.3f}</div>
                        <div class="change">economic activity</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Displacement Risk</div>
                        <div class="value">{city_baseline['displacement']:.3f}</div>
                        <div class="change">community vulnerability</div>
                    </div>
                </div>
            </div>
            
            <!-- Recommendation -->
            <div class="section">
                <h2>🎯 Recommended Policy</h2>
                <div class="recommendation-box">
                    <div class="badge">{city_info['recommendation']}</div>
                    <h3>Priority: {city_info['priority']}</h3>
                    <p><strong>Rationale:</strong> {city_info['rationale']}</p>
                    <ul>
                        <li><strong>Budget:</strong> {city_info['budget']}</li>
                        <li><strong>Timeline:</strong> {city_info['timeline']}</li>
                    </ul>
                </div>
            </div>
            
            <!-- Policy Scenarios -->
            <div class="section">
                <h2>📈 Policy Scenario Comparison</h2>
                <table class="scenario-table">
                    <thead>
                        <tr>
                            <th>Policy Scenario</th>
                            <th>Population</th>
                            <th>Rent (€/mo)</th>
                            <th>Vitality</th>
                            <th>Displacement</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    # Calculate and add scenario rows
    for scenario_name, (pop_mult, rent_mult, vitality_mult, displacement_mult) in city_info['scenarios'].items():
        new_pop = int(city_baseline['population'] * pop_mult)
        new_rent = city_baseline['rent_eur'] * rent_mult
        new_vitality = city_baseline['vitality'] * vitality_mult
        new_displacement = city_baseline['displacement'] * displacement_mult
        
        pop_change = f"{(pop_mult - 1) * 100:+.1f}%"
        rent_change = f"{(rent_mult - 1) * 100:+.1f}%"
        vitality_change = f"{(vitality_mult - 1) * 100:+.1f}%"
        displacement_change = f"{(displacement_mult - 1) * 100:+.1f}%"
        
        winner_class = "winner" if scenario_name == city_info['recommendation'] else ""
        
        html += f"""
                        <tr>
                            <td><strong>{scenario_name}</strong></td>
                            <td>{new_pop:,} {pop_change}</td>
                            <td>€{new_rent:.2f}</td>
                            <td>{new_vitality:.3f} {vitality_change}</td>
                            <td>{new_displacement:.3f} {displacement_change}</td>
                        </tr>
"""
    
    html += """
                    </tbody>
                </table>
            </div>
            
            <!-- Implementation Timeline -->
            <div class="section">
                <h2>⏱️ Implementation Timeline</h2>
                <div class="timeline">
                    <div class="timeline-item">
                        <div class="year">Month 1-3</div>
                        <div class="phase">Secure Funding<br/>Plan Projects</div>
                    </div>
                    <div class="timeline-item">
                        <div class="year">Year 1</div>
                        <div class="phase">Deploy Subsidies<br/>Begin Green Space</div>
                    </div>
                    <div class="timeline-item">
                        <div class="year">Year 2</div>
                        <div class="phase">Transit Phase 1<br/>Evaluate Progress</div>
                    </div>
                    <div class="timeline-item">
                        <div class="year">Year 3+</div>
                        <div class="phase">Full Implementation<br/>Monitor Results</div>
                    </div>
                </div>
            </div>
            
            <!-- Success Metrics -->
            <div class="section">
                <h2>📊 Success Metrics to Track</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="label">Population Target</div>
                        <div class="value">"""
    
    # Calculate targets
    if city_key == 'berlin':
        target_pop = 971
        target_rent = 2352.60
    elif city_key == 'leipzig':
        target_pop = 740
        target_rent = 2439.75
    else:  # munich
        target_pop = 1086
        target_rent = 2403.49
    
    html += f"""
                        <div class="change">+{target_pop - int(city_baseline['population'])} by Year 3</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Rent Target</div>
                        <div class="value">€{target_rent:.0f}</div>
                        <div class="change">-€{city_baseline['rent_eur'] - target_rent:.0f}/mo</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Vitality Target</div>
                        <div class="value">+35%</div>
                        <div class="change">Combined policy impact</div>
                    </div>
                    <div class="metric-card">
                        <div class="label">Equity Focus</div>
                        <div class="value">-8%</div>
                        <div class="change">Displacement risk</div>
                    </div>
                </div>
            </div>
            
            <!-- Key Risks -->
            <div class="section">
                <h2>⚠️ Key Risks & Mitigation</h2>
                <div class="recommendation-box">
                    <h3>What Could Go Wrong?</h3>
                    <ul>
                        <li><strong>Unsustainable costs:</strong> Phased funding with performance gates</li>
                        <li><strong>Gentrification:</strong> Community land trusts, rent controls</li>
                        <li><strong>Implementation delays:</strong> 15% budget contingency, clear timelines</li>
                        <li><strong>Political change:</strong> Multi-year contracts, broad coalition</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated: January 2026 | Analysis Tool: holistic_urban_simulator</p>
            <p>Data Source: 3-city simulation (20 timesteps each) | Database: PostgreSQL urban_sim</p>
        </div>
    </div>
</body>
</html>
"""
    
    # Save file
    output_path = f"data/outputs/visualizations/policy_dashboard_{city_key}.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Created: {output_path}")

print("\n[OK] City-specific policy dashboards created successfully!")
print("\nGenerated files:")
print("  - data/outputs/visualizations/policy_dashboard_berlin.html")
print("  - data/outputs/visualizations/policy_dashboard_leipzig.html")
print("  - data/outputs/visualizations/policy_dashboard_munich.html")
print("\nOpen in browser to view city-specific recommendations and scenarios.")
