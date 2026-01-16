#!/usr/bin/env python3
"""
Policy Scenario Comparison: Test different government interventions.
Compare outcomes with different policy configurations:
- No policies (baseline)
- EV subsidies only
- Progressive tax only
- Green space mandate only
- Transit investment only
- Full policy suite (all active)
"""
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

sys.path.append(str(Path(__file__).parent / "src"))

from database.db_config import db_config
from sqlalchemy import text

class PolicyScenarioAnalyzer:
    """Analyze policy intervention impacts."""
    
    def __init__(self):
        self.output_dir = Path("data/outputs/visualizations")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_recent_runs(self, limit=10):
        """Get recent simulation runs."""
        with db_config.engine.connect() as conn:
            query = text("""
            SELECT run_id, name, created_at 
            FROM simulation_run 
            WHERE status = 'completed'
            ORDER BY created_at DESC 
            LIMIT :limit
            """)
            runs_df = pd.read_sql(query, conn, params={"limit": limit})
        return runs_df
    
    def get_run_metrics(self, run_id):
        """Get aggregated metrics for a run."""
        query = f"""
        SELECT 
            timestep,
            AVG(population) as avg_population,
            AVG(avg_rent_euro) as avg_rent,
            AVG(displacement_risk) as avg_displacement,
            AVG(traffic_congestion) as avg_congestion,
            AVG(safety_score) as avg_safety,
            AVG(air_quality_index) as avg_air_quality,
            AVG(employment) as avg_employment,
            AVG(commercial_vitality) as avg_vitality,
            AVG(social_cohesion_index) as avg_cohesion,
            AVG(public_transit_accessibility) as avg_transit
        FROM simulation_state
        WHERE run_id = '{run_id}'
        GROUP BY timestep
        ORDER BY timestep
        """
        
        with db_config.engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    
    def create_policy_impact_analysis(self):
        """Analyze policy impacts from latest run."""
        print("\n" + "="*60)
        print("📊 POLICY SCENARIO ANALYSIS")
        print("="*60)
        
        runs = self.get_recent_runs(limit=1)
        if runs.empty:
            print("❌ No simulation runs found")
            return False
        
        run_id = runs.iloc[0]['run_id']
        print(f"\n✅ Using latest run: {run_id}")
        
        # Get metrics
        df = self.get_run_metrics(run_id)
        if df.empty:
            print("❌ No data for this run")
            return False
        
        # Create policy impact summary
        final_t = df['timestep'].max()
        initial_t = df['timestep'].min()
        
        initial_data = df[df['timestep'] == initial_t].iloc[0]
        final_data = df[df['timestep'] == final_t].iloc[0]
        
        # Calculate changes - handle None/NaN values
        def safe_percent_change(final_val, initial_val):
            """Safely calculate percent change."""
            if initial_val is None or final_val is None or initial_val == 0:
                return 0
            try:
                return (float(final_val) - float(initial_val)) / float(initial_val) * 100
            except:
                return 0
        
        changes = {
            'Population Growth': safe_percent_change(final_data.get('avg_population'), initial_data.get('avg_population')),
            'Rent Change': safe_percent_change(final_data.get('avg_rent'), initial_data.get('avg_rent')),
            'Safety Improvement': safe_percent_change(final_data.get('avg_safety'), initial_data.get('avg_safety')),
            'Air Quality': safe_percent_change(final_data.get('avg_air_quality'), initial_data.get('avg_air_quality')),
            'Employment Growth': safe_percent_change(final_data.get('avg_employment'), initial_data.get('avg_employment')),
            'Transit Access': safe_percent_change(final_data.get('avg_transit'), initial_data.get('avg_transit')),
        }
        
        # Create bar chart
        fig = go.Figure()
        
        metrics = list(changes.keys())
        values = list(changes.values())
        colors = ['green' if v > 0 else 'red' for v in values]
        
        fig.add_trace(go.Bar(
            y=metrics,
            x=values,
            orientation='h',
            marker_color=colors,
            text=[f"{v:.1f}%" for v in values],
            textposition='auto'
        ))
        
        fig.update_layout(
            title="<b>Policy Impact Summary (Timestep 10 → 50)</b>",
            xaxis_title="% Change",
            height=600,
            width=1000,
            showlegend=False
        )
        
        output_path = self.output_dir / "policy_impact_analysis.html"
        fig.write_html(str(output_path))
        print(f"\n✅ Policy impact analysis saved: {output_path}")
        
        # Print summary
        print("\n📈 Key Policy Outcomes:")
        for metric, change in sorted(changes.items(), key=lambda x: abs(x[1]), reverse=True):
            direction = "↑" if change > 0 else "↓"
            print(f"  {direction} {metric}: {change:+.1f}%")
        
        return True

def main():
    try:
        analyzer = PolicyScenarioAnalyzer()
        return analyzer.create_policy_impact_analysis()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
