#!/usr/bin/env python3
"""
Quick scenario comparison using mathematical modeling of EV impact.
Instead of running 3 full simulations, we model the impact based on the existing run.
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

class QuickScenarioAnalysis:
    """Analyze EV impact using mathematical modeling."""
    
    def __init__(self):
        self.output_dir = Path("data/outputs/visualizations")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # EV impact coefficients (from EVModule)
        self.ev_impacts = {
            'air_quality_per_charger': -5.0,  # -5 AQI pts per charger/km²
            'rent_per_kw': 50.0,  # €50 per kW capacity
            'population_attraction': 0.15,  # 15% increase per charger
            'employment_per_kw': 0.2,  # 1 job per 5 kW
            'cohesion_per_charger': 0.03,  # 3% per charger
        }
    
    def get_current_run_data(self):
        """Get data from the existing simulation run."""
        print("\n🔍 Loading current simulation data...")
        
        query = """
        SELECT 
            ss.timestep,
            ss.grid_id,
            ss.population,
            ss.traffic_congestion,
            ss.safety_score,
            ss.avg_rent_euro,
            ss.displacement_risk,
            ss.commercial_vitality,
            ss.air_quality_index,
            ss.chargers_count,
            ss.ev_capacity_kw,
            ss.charger_density_per_sqkm
        FROM simulation_state ss
        WHERE ss.run_id = (
            SELECT run_id FROM simulation_run 
            WHERE status = 'completed'
            ORDER BY created_at DESC LIMIT 1
        )
        ORDER BY ss.timestep, ss.grid_id
        """
        
        with db_config.engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        if df.empty:
            print("❌ No simulation data found")
            return None
        
        print(f"✅ Loaded {len(df)} records")
        return df
    
    def generate_baseline_scenario(self, current_df):
        """Generate baseline (no EV) scenario from current data."""
        print("\n📊 Generating Baseline scenario (no EV infrastructure)...")
        
        baseline_df = current_df.copy()
        
        # Remove EV effects by subtracting impact
        for idx, row in baseline_df.iterrows():
            chargers = row['chargers_count'] if pd.notna(row['chargers_count']) else 0
            capacity = row['ev_capacity_kw'] if pd.notna(row['ev_capacity_kw']) else 0
            density = row['charger_density_per_sqkm'] if pd.notna(row['charger_density_per_sqkm']) else 0
            
            if chargers > 0:
                # Reverse EV impacts
                baseline_df.loc[idx, 'air_quality_index'] += density * self.ev_impacts['air_quality_per_charger']
                baseline_df.loc[idx, 'avg_rent_euro'] -= capacity * self.ev_impacts['rent_per_kw']
                baseline_df.loc[idx, 'population'] /= (1 + self.ev_impacts['population_attraction'] * chargers)
                baseline_df.loc[idx, 'commercial_vitality'] -= chargers * self.ev_impacts['cohesion_per_charger']
            
            # Remove charger data
            baseline_df.loc[idx, 'chargers_count'] = 0
            baseline_df.loc[idx, 'ev_capacity_kw'] = 0
            baseline_df.loc[idx, 'charger_density_per_sqkm'] = 0
        
        return baseline_df
    
    def generate_2x_growth_scenario(self, current_df):
        """Generate 2x growth scenario (doubled EV infrastructure)."""
        print("📊 Generating 2x Growth scenario (8 EV chargers)...")
        
        growth_df = current_df.copy()
        
        # Scale charger data by 2x
        growth_df['chargers_count'] = growth_df['chargers_count'].fillna(0) * 2
        growth_df['ev_capacity_kw'] = growth_df['ev_capacity_kw'].fillna(0) * 2
        growth_df['charger_density_per_sqkm'] = growth_df['charger_density_per_sqkm'].fillna(0) * 2
        
        # Apply 2x EV impacts
        for idx, row in growth_df.iterrows():
            chargers = row['chargers_count']
            capacity = row['ev_capacity_kw']
            density = row['charger_density_per_sqkm']
            
            if chargers > 0:
                # Apply doubled EV impacts
                growth_df.loc[idx, 'air_quality_index'] += density * self.ev_impacts['air_quality_per_charger']
                growth_df.loc[idx, 'avg_rent_euro'] += capacity * self.ev_impacts['rent_per_kw']
                growth_df.loc[idx, 'population'] *= (1 + self.ev_impacts['population_attraction'] * chargers)
                growth_df.loc[idx, 'commercial_vitality'] += chargers * self.ev_impacts['cohesion_per_charger']
        
        return growth_df
    
    def create_metric_comparison(self, baseline_df, current_df, growth_df):
        """Create comparison chart of metrics across scenarios."""
        print("\n📊 Creating metric comparison...")
        
        # Aggregate to final timestep
        final_t = current_df['timestep'].max()
        
        scenarios_data = {}
        
        for scenario_name, df in [('Baseline', baseline_df), ('Current (4 EV)', current_df), ('2x Growth (8 EV)', growth_df)]:
            final_data = df[df['timestep'] == final_t]
            if final_data.empty:
                continue
            
            scenarios_data[scenario_name] = {
                'Population': final_data['population'].mean(),
                'Safety': final_data['safety_score'].mean() * 100,
                'Air Quality': final_data['air_quality_index'].mean() * 100,
                'Avg Rent': final_data['avg_rent_euro'].mean(),
                'Commercial': final_data['commercial_vitality'].mean() * 100,
            }
        
        metrics_df = pd.DataFrame(scenarios_data).T
        
        # Create comparison figure
        fig = make_subplots(
            rows=1, cols=5,
            subplot_titles=list(metrics_df.columns),
            specs=[[{'type': 'bar'}] * 5]
        )
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Blue, Orange, Green
        
        for i, metric in enumerate(metrics_df.columns, 1):
            fig.add_trace(
                go.Bar(
                    x=metrics_df.index,
                    y=metrics_df[metric],
                    name=metric,
                    marker_color=colors,
                    showlegend=False
                ),
                row=1, col=i
            )
            fig.update_yaxes(title_text=metric, row=1, col=i)
        
        fig.update_layout(
            title="<b>EV Scenario Comparison (Final Timestep)</b>",
            height=500,
            width=1500,
            showlegend=False
        )
        
        output_path = self.output_dir / "scenario_metrics_comparison_quick.html"
        fig.write_html(str(output_path))
        print(f"✅ Saved: {output_path}")
    
    def create_impact_heatmap(self, baseline_df, current_df, growth_df):
        """Create impact quantification heatmap."""
        print("📈 Creating impact quantification...")
        
        final_t = current_df['timestep'].max()
        
        # Get final timestep data
        baseline_final = baseline_df[baseline_df['timestep'] == final_t]
        current_final = current_df[current_df['timestep'] == final_t]
        growth_final = growth_df[growth_df['timestep'] == final_t]
        
        # Calculate % impact vs baseline
        impact_data = []
        
        metrics = ['population', 'safety_score', 'avg_rent_euro', 'air_quality_index', 'commercial_vitality']
        metric_names = ['Population', 'Safety', 'Rent', 'Air Quality', 'Commercial Vitality']
        
        for scenario_name, scenario_final in [('Current (4 EV)', current_final), ('2x Growth (8 EV)', growth_final)]:
            changes = []
            for metric, metric_name in zip(metrics, metric_names):
                baseline_val = baseline_final[metric].mean()
                scenario_val = scenario_final[metric].mean()
                
                if baseline_val != 0:
                    pct_change = ((scenario_val - baseline_val) / abs(baseline_val)) * 100
                else:
                    pct_change = 0
                
                changes.append(pct_change)
            
            impact_data.append(changes)
        
        impact_array = np.array(impact_data)
        
        fig = go.Figure(data=go.Heatmap(
            z=impact_array,
            x=metric_names,
            y=['Current (4 EV)', '2x Growth (8 EV)'],
            colorscale='RdYlGn',
            zmid=0,
            text=np.round(impact_array, 1),
            texttemplate='%{text:.1f}%',
            textfont={'size': 12},
            colorbar=dict(title='% vs Baseline')
        ))
        
        fig.update_layout(
            title="<b>EV Infrastructure Impact vs Baseline</b>",
            height=350,
            width=1000,
            xaxis_title="Metrics",
            yaxis_title="Scenario"
        )
        
        output_path = self.output_dir / "scenario_impact_quantification_quick.html"
        fig.write_html(str(output_path))
        print(f"✅ Saved: {output_path}")
    
    def create_timeline_comparison(self, baseline_df, current_df, growth_df):
        """Create timeline comparison."""
        print("📉 Creating timeline comparison...")
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=['Population Growth', 'Air Quality', 'Safety Trends', 'Rent Escalation']
        )
        
        colors = {'Baseline': '#1f77b4', 'Current (4 EV)': '#ff7f0e', '2x Growth (8 EV)': '#2ca02c'}
        
        for scenario_name, df, color in [
            ('Baseline', baseline_df, colors['Baseline']),
            ('Current (4 EV)', current_df, colors['Current (4 EV)']),
            ('2x Growth (8 EV)', growth_df, colors['2x Growth (8 EV)'])
        ]:
            agg_df = df.groupby('timestep').agg({
                'population': 'mean',
                'air_quality_index': 'mean',
                'safety_score': 'mean',
                'avg_rent_euro': 'mean'
            }).reset_index()
            
            # Population
            fig.add_trace(
                go.Scatter(x=agg_df['timestep'], y=agg_df['population'],
                          name=scenario_name, mode='lines',
                          line=dict(color=color, width=2)),
                row=1, col=1
            )
            
            # Air Quality
            fig.add_trace(
                go.Scatter(x=agg_df['timestep'], y=agg_df['air_quality_index'] * 100,
                          name=scenario_name, mode='lines',
                          line=dict(color=color, width=2), showlegend=False),
                row=1, col=2
            )
            
            # Safety
            fig.add_trace(
                go.Scatter(x=agg_df['timestep'], y=agg_df['safety_score'] * 100,
                          name=scenario_name, mode='lines',
                          line=dict(color=color, width=2), showlegend=False),
                row=2, col=1
            )
            
            # Rent
            fig.add_trace(
                go.Scatter(x=agg_df['timestep'], y=agg_df['avg_rent_euro'],
                          name=scenario_name, mode='lines',
                          line=dict(color=color, width=2), showlegend=False),
                row=2, col=2
            )
        
        fig.update_yaxes(title_text='Population', row=1, col=1)
        fig.update_yaxes(title_text='Air Quality (0-100)', row=1, col=2)
        fig.update_yaxes(title_text='Safety (0-100)', row=2, col=1)
        fig.update_yaxes(title_text='Avg Rent (€)', row=2, col=2)
        fig.update_xaxes(title_text='Timestep', row=2, col=1)
        fig.update_xaxes(title_text='Timestep', row=2, col=2)
        
        fig.update_layout(
            title='<b>Metric Evolution Across Scenarios</b>',
            height=800,
            width=1400,
            hovermode='x unified'
        )
        
        output_path = self.output_dir / "scenario_timeline_comparison_quick.html"
        fig.write_html(str(output_path))
        print(f"✅ Saved: {output_path}")
    
    def run(self):
        """Run complete analysis."""
        print("\n" + "="*60)
        print("⚡ QUICK EV SCENARIO ANALYSIS")
        print("="*60)
        
        # Load data
        current_df = self.get_current_run_data()
        if current_df is None:
            return False
        
        # Generate scenarios
        baseline_df = self.generate_baseline_scenario(current_df)
        growth_df = self.generate_2x_growth_scenario(current_df)
        
        # Create visualizations
        self.create_metric_comparison(baseline_df, current_df, growth_df)
        self.create_impact_heatmap(baseline_df, current_df, growth_df)
        self.create_timeline_comparison(baseline_df, current_df, growth_df)
        
        print("\n" + "="*60)
        print("✅ SCENARIO ANALYSIS COMPLETE")
        print("="*60)
        print(f"\n📁 Results saved to: {self.output_dir}")
        print("\nGenerated files:")
        print("  📊 scenario_metrics_comparison_quick.html")
        print("  📈 scenario_impact_quantification_quick.html")
        print("  📉 scenario_timeline_comparison_quick.html")
        print("\n🎯 Key Findings:")
        print("  • Baseline: Control scenario with no EV infrastructure")
        print("  • Current (4 EV): Existing configuration")
        print("  • 2x Growth (8 EV): Doubled infrastructure expansion")
        print("\nMetrics compared:")
        print("  ✓ Population attraction (+15% per charger)")
        print("  ✓ Air quality improvement (-5 AQI pts per charger/km²)")
        print("  ✓ Rent escalation (+€50 per kW)")
        print("  ✓ Safety and commercial vitality")
        
        return True

def main():
    try:
        analyzer = QuickScenarioAnalysis()
        return analyzer.run()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
