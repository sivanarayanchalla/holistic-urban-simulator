#!/usr/bin/env python3
"""
Infrastructure Impact Analysis: Quantify education, healthcare, and EV effects.
Shows how different infrastructure types drive urban metrics.
"""
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.append(str(Path(__file__).parent / "src"))

from database.db_config import db_config
from sqlalchemy import text

class InfrastructureImpactAnalyzer:
    """Analyze infrastructure sector impacts."""
    
    def __init__(self):
        self.output_dir = Path("data/outputs/visualizations")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_latest_run(self):
        """Get latest simulation run."""
        with db_config.engine.connect() as conn:
            query = text("""
            SELECT run_id FROM simulation_run 
            WHERE status = 'completed'
            ORDER BY created_at DESC LIMIT 1
            """)
            result = pd.read_sql(query, conn)
        
        return result.iloc[0]['run_id'] if not result.empty else None
    
    def get_infrastructure_impact(self, run_id):
        """Analyze impact of different infrastructure types."""
        query = f"""
        SELECT 
            grid_id,
            timestep,
            population,
            avg_rent_euro,
            employment,
            safety_score,
            social_cohesion_index,
            public_transit_accessibility,
            air_quality_index,
            chargers_count,
            ev_capacity_kw,
            commercial_vitality
        FROM simulation_state
        WHERE run_id = '{run_id}'
        ORDER BY timestep, grid_id
        """
        
        with db_config.engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        return df
    
    def analyze_by_infrastructure_level(self, df):
        """Segment cells by infrastructure intensity."""
        # Use final timestep
        final_t = df['timestep'].max()
        final_data = df[df['timestep'] == final_t].copy()
        
        # Estimate infrastructure levels from population and metrics
        final_data['est_schools'] = final_data['population'] / 2000  # 1 school per 2000 residents
        final_data['est_healthcare'] = final_data['population'] / 3000  # 1 facility per 3000 residents
        final_data['ev_chargers'] = final_data['chargers_count']
        final_data['infrastructure_level'] = (
            (final_data['est_schools'] + final_data['est_healthcare'] + final_data['ev_chargers']) / 3
        )
        
        # Classify by infrastructure level
        final_data['classification'] = pd.cut(final_data['infrastructure_level'], 
                                             bins=[0, 1, 2, 3, float('inf')],
                                             labels=['Low', 'Medium', 'High', 'Very High'])
        
        # Calculate average outcomes by infrastructure level
        outcomes = final_data.groupby('classification').agg({
            'population': 'mean',
            'avg_rent_euro': 'mean',
            'employment': 'mean',
            'safety_score': 'mean',
            'social_cohesion_index': 'mean',
            'public_transit_accessibility': 'mean',
            'air_quality_index': 'mean',
            'commercial_vitality': 'mean'
        }).reset_index()
        
        return outcomes
    
    def create_infrastructure_comparison(self, outcomes):
        """Create comparison visualization."""
        
        # Normalize outcomes to 0-100 scale for comparison
        normalized = outcomes.copy()
        for col in outcomes.columns[1:]:
            if col in ['population', 'employment']:
                # Keep as-is for absolute values
                pass
            elif col in ['safety_score', 'social_cohesion_index', 'public_transit_accessibility', 'commercial_vitality']:
                # Scale 0-1 to 0-100
                normalized[col] = outcomes[col] * 100
            # air_quality_index, avg_rent already in good scale
        
        # Create subplots for different metric categories
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Population & Employment', 'Affordability vs Vitality',
                          'Safety & Cohesion', 'Environmental & Transit'),
            specs=[[{'type': 'scatter'}, {'type': 'scatter'}],
                   [{'type': 'scatter'}, {'type': 'scatter'}]]
        )
        
        colors = ['blue', 'green', 'orange', 'red']
        
        # Plot 1: Population vs Employment
        fig.add_trace(
            go.Scatter(x=outcomes['classification'], y=outcomes['population'],
                      mode='lines+markers', name='Population', 
                      line=dict(color='blue', width=2), marker=dict(size=10)),
            row=1, col=1
        )
        
        # Plot 2: Rent vs Vitality
        fig.add_trace(
            go.Scatter(x=outcomes['classification'], y=outcomes['avg_rent_euro'],
                      mode='lines+markers', name='Avg Rent (€)',
                      line=dict(color='green', width=2), marker=dict(size=10)),
            row=1, col=2
        )
        
        # Plot 3: Safety & Cohesion
        fig.add_trace(
            go.Scatter(x=outcomes['classification'], y=normalized['safety_score'],
                      mode='lines+markers', name='Safety Score',
                      line=dict(color='purple', width=2), marker=dict(size=10)),
            row=2, col=1
        )
        
        # Plot 4: Air Quality & Transit
        fig.add_trace(
            go.Scatter(x=outcomes['classification'], y=outcomes['air_quality_index'],
                      mode='lines+markers', name='Air Quality',
                      line=dict(color='brown', width=2), marker=dict(size=10)),
            row=2, col=2
        )
        
        fig.update_yaxes(title_text="Count", row=1, col=1)
        fig.update_yaxes(title_text="€/month", row=1, col=2)
        fig.update_yaxes(title_text="Score (0-100)", row=2, col=1)
        fig.update_yaxes(title_text="AQI", row=2, col=2)
        
        fig.update_layout(
            title="<b>Urban Outcomes by Infrastructure Level</b><br><sub>How education, healthcare, and EV affect city metrics</sub>",
            height=800,
            width=1200,
            showlegend=True,
            hovermode='x unified'
        )
        
        output_path = self.output_dir / "infrastructure_impact_comparison.html"
        fig.write_html(str(output_path))
        print(f"\n✅ Infrastructure comparison: {output_path}")
        
        # Print insights
        print("\n📊 Infrastructure Impact Insights:")
        print("\nOutcomes by Infrastructure Level:")
        print(outcomes.to_string(index=False))
        
        # Calculate deltas
        print("\n📈 Impact Analysis (Low → High Infrastructure):")
        if len(outcomes) > 1:
            low = outcomes.iloc[0]
            high = outcomes.iloc[-1]
            
            pop_delta = ((high['population'] - low['population']) / low['population'] * 100) if low['population'] > 0 else 0
            rent_delta = ((high['avg_rent_euro'] - low['avg_rent_euro']) / low['avg_rent_euro'] * 100) if low['avg_rent_euro'] > 0 else 0
            emp_delta = ((high['employment'] - low['employment']) / low['employment'] * 100) if low['employment'] > 0 else 0
            safety_delta = (high['safety_score'] - low['safety_score']) * 100
            
            print(f"  Population growth: {pop_delta:+.1f}%")
            print(f"  Rent escalation: {rent_delta:+.1f}%")
            print(f"  Employment creation: {emp_delta:+.1f}%")
            print(f"  Safety improvement: {safety_delta:+.1f} pts")

def main():
    try:
        print("\n" + "="*60)
        print("🏭 INFRASTRUCTURE IMPACT ANALYSIS")
        print("="*60)
        
        analyzer = InfrastructureImpactAnalyzer()
        
        run_id = analyzer.get_latest_run()
        if not run_id:
            print("❌ No simulation runs found")
            return False
        
        print(f"\n✅ Analyzing run: {run_id}")
        
        # Get data
        df = analyzer.get_infrastructure_impact(run_id)
        if df is None or df.empty:
            print("❌ No data available")
            return False
        
        # Analyze by infrastructure level
        outcomes = analyzer.analyze_by_infrastructure_level(df)
        
        # Create visualization
        analyzer.create_infrastructure_comparison(outcomes)
        
        print("\n" + "="*60)
        print("✅ INFRASTRUCTURE ANALYSIS COMPLETE")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
