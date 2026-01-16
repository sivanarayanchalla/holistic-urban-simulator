#!/usr/bin/env python3
"""
Analyze and compare EV infrastructure scenario results.
Generates comparison visualizations and impact quantification.
"""
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from database.db_config import db_config
from sqlalchemy import text

class ScenarioAnalyzer:
    """Analyze scenario comparison results."""
    
    def __init__(self):
        self.output_dir = Path("data/outputs/visualizations")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scenarios = {
            'baseline': 'Baseline (No EV)',
            'current': 'Current (4 EV)',
            '2x_growth': '2x Growth (8 EV)'
        }
    
    def get_scenario_runs(self):
        """Retrieve the three scenario simulation runs."""
        print("\n🔍 Searching for scenario runs...")
        
        with db_config.engine.connect() as conn:
            query = text("""
            SELECT run_id, name, created_at, total_timesteps
            FROM simulation_run 
            WHERE status = 'completed'
            ORDER BY created_at DESC 
            LIMIT 10
            """)
            
            runs_df = pd.read_sql(query, conn)
        
        if runs_df.empty:
            print("❌ No completed simulation runs found")
            return None
        
        # Try to identify scenario runs by name patterns
        scenario_runs = {}
        
        for scenario_key in ['baseline', 'current', '2x_growth']:
            # Look for runs matching scenario patterns
            for idx, row in runs_df.iterrows():
                run_name = row['name'].lower()
                
                if scenario_key == 'baseline' and ('baseline' in run_name or 'no ev' in run_name):
                    scenario_runs['baseline'] = row['run_id']
                elif scenario_key == 'current' and ('current' in run_name or '4' in run_name):
                    scenario_runs['current'] = row['run_id']
                elif scenario_key == '2x_growth' and ('2x' in run_name or '8' in run_name or 'growth' in run_name):
                    scenario_runs['2x_growth'] = row['run_id']
        
        # If we didn't find all scenarios by pattern, use the last 3 runs
        if len(scenario_runs) < 3:
            print("⚠️  Could not identify all scenarios by name. Using last 3 runs...")
            scenario_runs = {
                'baseline': runs_df.iloc[2]['run_id'] if len(runs_df) > 2 else None,
                'current': runs_df.iloc[1]['run_id'] if len(runs_df) > 1 else None,
                '2x_growth': runs_df.iloc[0]['run_id']
            }
        
        print("✅ Found scenario runs:")
        for scenario_key, run_id in scenario_runs.items():
            if run_id:
                print(f"   {scenario_key:15} : {run_id}")
        
        return scenario_runs
    
    def get_scenario_metrics(self, run_id):
        """Get aggregated metrics for a scenario."""
        query = f"""
        SELECT 
            timestep,
            AVG(population) as avg_population,
            AVG(traffic_congestion) as avg_congestion,
            AVG(safety_score) as avg_safety,
            AVG(avg_rent_euro) as avg_rent,
            AVG(air_quality_index) as avg_air_quality,
            AVG(commercial_vitality) as avg_vitality,
            AVG(displacement_risk) as avg_displacement,
            SUM(chargers_count) as total_chargers,
            AVG(charger_density_per_sqkm) as avg_charger_density,
            AVG(ev_capacity_kw) as avg_ev_capacity
        FROM simulation_state
        WHERE run_id = '{run_id}'
        GROUP BY timestep
        ORDER BY timestep
        """
        
        with db_config.engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        return df
    
    def create_metric_comparison(self, scenario_runs):
        """Create comparison chart of key metrics across scenarios."""
        print("\n📊 Creating metric comparison charts...")
        
        # Collect final timestep metrics for each scenario
        metrics_data = {}
        
        for scenario_key, run_id in scenario_runs.items():
            if run_id is None:
                continue
            
            df = self.get_scenario_metrics(run_id)
            if df.empty:
                print(f"   ⚠️  No data for {scenario_key}")
                continue
            
            # Get final timestep
            final_row = df.iloc[-1]
            
            metrics_data[self.scenarios[scenario_key]] = {
                'Population': final_row['avg_population'],
                'Safety Score': final_row['avg_safety'] * 100,  # Scale to 0-100
                'Avg Rent (€)': final_row['avg_rent'],
                'Air Quality': final_row['avg_air_quality'] * 100,
                'Traffic Congestion': final_row['avg_congestion'] * 100,
                'Commercial Vitality': final_row['avg_vitality'] * 100,
            }
        
        if not metrics_data:
            print("   ❌ No metrics data available")
            return
        
        metrics_df = pd.DataFrame(metrics_data).T
        
        # Create subplot figure with 3 metrics
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=('Population', 'Safety Score', 'Average Rent',
                          'Air Quality', 'Traffic Congestion', 'Commercial Vitality'),
            specs=[[{'type': 'bar'}, {'type': 'bar'}, {'type': 'bar'}],
                   [{'type': 'bar'}, {'type': 'bar'}, {'type': 'bar'}]]
        )
        
        # Color scheme: Baseline=blue, Current=orange, 2x=green
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
        
        metrics_list = list(metrics_df.columns)
        positions = [(1,1), (1,2), (1,3), (2,1), (2,2), (2,3)]
        
        for idx, (metric, pos) in enumerate(zip(metrics_list, positions)):
            values = metrics_df[metric].values
            
            fig.add_trace(
                go.Bar(
                    x=metrics_df.index,
                    y=values,
                    name=metric,
                    marker_color=colors,
                    showlegend=False
                ),
                row=pos[0], col=pos[1]
            )
            
            fig.update_yaxes(title_text=metric, row=pos[0], col=pos[1])
        
        fig.update_layout(
            title_text="<b>EV Scenario Impact Comparison (Final Timestep)</b>",
            height=800,
            width=1400,
            showlegend=False
        )
        
        output_path = self.output_dir / "scenario_metrics_comparison.html"
        fig.write_html(str(output_path))
        print(f"   ✅ Saved: {output_path}")
    
    def create_impact_quantification(self, scenario_runs):
        """Quantify EV impact relative to baseline."""
        print("\n📈 Creating impact quantification...")
        
        # Get baseline metrics
        if scenario_runs.get('baseline') is None:
            print("   ⚠️  Baseline scenario not found, skipping impact quantification")
            return
        
        baseline_df = self.get_scenario_metrics(scenario_runs['baseline'])
        if baseline_df.empty:
            print("   ⚠️  No baseline data available")
            return
        
        baseline_final = baseline_df.iloc[-1]
        
        # Compare other scenarios to baseline
        impact_data = []
        
        for scenario_key in ['current', '2x_growth']:
            if scenario_runs.get(scenario_key) is None:
                continue
            
            scenario_df = self.get_scenario_metrics(scenario_runs[scenario_key])
            if scenario_df.empty:
                continue
            
            scenario_final = scenario_df.iloc[-1]
            
            # Calculate % change from baseline
            changes = {
                'Scenario': self.scenarios[scenario_key],
                'Population Change (%)': ((scenario_final['avg_population'] - baseline_final['avg_population']) / baseline_final['avg_population'] * 100) if baseline_final['avg_population'] > 0 else 0,
                'Safety Change (%)': ((scenario_final['avg_safety'] - baseline_final['avg_safety']) / baseline_final['avg_safety'] * 100) if baseline_final['avg_safety'] > 0 else 0,
                'Rent Change (%)': ((scenario_final['avg_rent'] - baseline_final['avg_rent']) / baseline_final['avg_rent'] * 100) if baseline_final['avg_rent'] > 0 else 0,
                'Air Quality Change (%)': ((scenario_final['avg_air_quality'] - baseline_final['avg_air_quality']) / baseline_final['avg_air_quality'] * 100) if baseline_final['avg_air_quality'] > 0 else 0,
                'Congestion Change (%)': ((scenario_final['avg_congestion'] - baseline_final['avg_congestion']) / baseline_final['avg_congestion'] * 100) if baseline_final['avg_congestion'] > 0 else 0,
            }
            
            impact_data.append(changes)
        
        if not impact_data:
            print("   ⚠️  No impact data generated")
            return
        
        impact_df = pd.DataFrame(impact_data)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=impact_df.iloc[:, 1:].values,
            x=impact_df.columns[1:],
            y=impact_df['Scenario'],
            colorscale='RdYlGn',
            zmid=0,
            text=np.round(impact_df.iloc[:, 1:].values, 1),
            texttemplate='%{text:.1f}%',
            textfont={"size": 12},
            colorbar=dict(title="% Change")
        ))
        
        fig.update_layout(
            title="<b>EV Infrastructure Impact vs Baseline</b><br><sub>Positive values = improvement</sub>",
            height=400,
            width=1000,
            xaxis_title="Metrics",
            yaxis_title="Scenario"
        )
        
        output_path = self.output_dir / "scenario_impact_quantification.html"
        fig.write_html(str(output_path))
        print(f"   ✅ Saved: {output_path}")
        
        # Print summary
        print("\n📊 Impact Summary:")
        print(impact_df.to_string(index=False))
    
    def create_timeline_comparison(self, scenario_runs):
        """Create timeline comparison of key metrics."""
        print("\n📉 Creating timeline comparison...")
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Population Growth', 'Air Quality', 'Safety Trends', 'Rent Escalation'),
            specs=[[{'secondary_y': False}, {'secondary_y': False}],
                   [{'secondary_y': False}, {'secondary_y': False}]]
        )
        
        colors = {'Baseline (No EV)': '#1f77b4', 'Current (4 EV)': '#ff7f0e', '2x Growth (8 EV)': '#2ca02c'}
        positions = [(1,1), (1,2), (2,1), (2,2)]
        metrics = ['avg_population', 'avg_air_quality', 'avg_safety', 'avg_rent']
        
        for scenario_key, run_id in scenario_runs.items():
            if run_id is None:
                continue
            
            df = self.get_scenario_metrics(run_id)
            if df.empty:
                continue
            
            scenario_name = self.scenarios[scenario_key]
            color = colors[scenario_name]
            
            # Population
            fig.add_trace(
                go.Scatter(x=df['timestep'], y=df['avg_population'], 
                          name=scenario_name, mode='lines', 
                          line=dict(color=color, width=2)),
                row=1, col=1
            )
            
            # Air Quality
            fig.add_trace(
                go.Scatter(x=df['timestep'], y=df['avg_air_quality'] * 100, 
                          name=scenario_name, mode='lines', 
                          line=dict(color=color, width=2), showlegend=False),
                row=1, col=2
            )
            
            # Safety
            fig.add_trace(
                go.Scatter(x=df['timestep'], y=df['avg_safety'] * 100, 
                          name=scenario_name, mode='lines', 
                          line=dict(color=color, width=2), showlegend=False),
                row=2, col=1
            )
            
            # Rent
            fig.add_trace(
                go.Scatter(x=df['timestep'], y=df['avg_rent'], 
                          name=scenario_name, mode='lines', 
                          line=dict(color=color, width=2), showlegend=False),
                row=2, col=2
            )
        
        fig.update_yaxes(title_text="Population", row=1, col=1)
        fig.update_yaxes(title_text="Air Quality (0-100)", row=1, col=2)
        fig.update_yaxes(title_text="Safety (0-100)", row=2, col=1)
        fig.update_yaxes(title_text="Avg Rent (€)", row=2, col=2)
        fig.update_xaxes(title_text="Timestep", row=2, col=1)
        fig.update_xaxes(title_text="Timestep", row=2, col=2)
        
        fig.update_layout(
            title="<b>Metric Evolution Across Scenarios</b>",
            height=800,
            width=1400,
            hovermode='x unified'
        )
        
        output_path = self.output_dir / "scenario_timeline_comparison.html"
        fig.write_html(str(output_path))
        print(f"   ✅ Saved: {output_path}")
    
    def run_analysis(self):
        """Run complete scenario analysis."""
        print("\n" + "="*60)
        print("📊 EV SCENARIO ANALYSIS")
        print("="*60)
        
        # Get scenario runs
        scenario_runs = self.get_scenario_runs()
        if not scenario_runs or not any(scenario_runs.values()):
            print("❌ Could not find scenario runs")
            return False
        
        # Create visualizations
        self.create_metric_comparison(scenario_runs)
        self.create_impact_quantification(scenario_runs)
        self.create_timeline_comparison(scenario_runs)
        
        print("\n" + "="*60)
        print("✅ SCENARIO ANALYSIS COMPLETE")
        print("="*60)
        print(f"\n📁 Results saved to: {self.output_dir}")
        print("\nGenerated files:")
        print("  📊 scenario_metrics_comparison.html")
        print("  📈 scenario_impact_quantification.html")
        print("  📉 scenario_timeline_comparison.html")
        print("\n🎯 Key Insights:")
        print("  • Compare metrics across all scenarios")
        print("  • Quantify % impact of EV infrastructure")
        print("  • Track evolution of metrics over time")
        
        return True

def main():
    """Main entry point."""
    try:
        analyzer = ScenarioAnalyzer()
        return analyzer.run_analysis()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
