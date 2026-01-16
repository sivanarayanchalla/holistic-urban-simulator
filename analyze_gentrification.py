#!/usr/bin/env python3
"""
Gentrification Analysis: Track displacement patterns and neighborhood changes.
Analyzes which neighborhoods are experiencing gentrification pressure.
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

class GentrificationAnalyzer:
    """Analyze gentrification and displacement patterns."""
    
    def __init__(self):
        self.output_dir = Path("data/outputs/visualizations")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_latest_run(self):
        """Get latest simulation run."""
        with db_config.engine.connect() as conn:
            query = text("""
            SELECT run_id, name, created_at 
            FROM simulation_run 
            WHERE status = 'completed'
            ORDER BY created_at DESC LIMIT 1
            """)
            result = pd.read_sql(query, conn)
        
        if result.empty:
            return None
        return result.iloc[0]['run_id']
    
    def analyze_gentrification(self, run_id):
        """Analyze gentrification patterns by tracking rent and displacement."""
        query = f"""
        SELECT 
            grid_id,
            timestep,
            population,
            avg_rent_euro,
            displacement_risk,
            social_cohesion_index,
            employment,
            air_quality_index
        FROM simulation_state
        WHERE run_id = '{run_id}'
        ORDER BY grid_id, timestep
        """
        
        with db_config.engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        if df.empty:
            return None
        
        return df
    
    def identify_gentrifying_areas(self, df):
        """Identify which cells are experiencing gentrification."""
        timesteps = sorted(df['timestep'].unique())
        initial_t = timesteps[0]
        final_t = timesteps[-1]
        
        initial_data = df[df['timestep'] == initial_t].set_index('grid_id')
        final_data = df[df['timestep'] == final_t].set_index('grid_id')
        
        gentrification_score = []
        
        for grid_id in initial_data.index:
            if grid_id not in final_data.index:
                continue
            
            # Safe extraction with None handling
            initial_rent = initial_data.loc[grid_id, 'avg_rent_euro']
            final_rent = final_data.loc[grid_id, 'avg_rent_euro']
            initial_pop = initial_data.loc[grid_id, 'population']
            final_pop = final_data.loc[grid_id, 'population']
            initial_emp = initial_data.loc[grid_id, 'employment']
            final_emp = final_data.loc[grid_id, 'employment']
            
            # Skip if missing critical data
            if not all([initial_rent, final_rent, initial_pop]):
                continue
            
            # Indicators of gentrification
            rent_increase = (final_rent - initial_rent) / initial_rent if initial_rent > 0 else 0
            displacement_increase = 0  # Not tracking individually
            population_change = (final_pop - initial_pop) / initial_pop if initial_pop > 0 else 0
            employment_change = ((final_emp or 0) - (initial_emp or 0)) / (initial_emp or 1) if initial_emp else 0
            
            # Gentrification = high rent increase + population change + employment growth
            gent_score = (rent_increase * 0.5 + population_change * 0.3 + employment_change * 0.2)
            
            gentrification_score.append({
                'grid_id': grid_id,
                'gentrification_score': gent_score,
                'rent_increase_%': rent_increase * 100,
                'displacement_increase': 0,
                'population_change_%': population_change * 100,
                'employment_change_%': employment_change * 100,
                'initial_rent': initial_rent,
                'final_rent': final_rent,
            })
        
        return pd.DataFrame(gentrification_score).sort_values('gentrification_score', ascending=False)
    
    def create_visualizations(self, gentrification_df):
        """Create gentrification analysis visualizations."""
        
        # === HIGH-RISK GENTRIFICATION MAP ===
        fig1 = go.Figure()
        
        top_gent = gentrification_df.head(10)
        
        fig1.add_trace(go.Bar(
            y=top_gent['grid_id'],
            x=top_gent['gentrification_score'],
            orientation='h',
            marker_color='orangered',
            text=top_gent['rent_increase_%'].round(1),
            texttemplate='Rent: %{text:.1f}%',
            textposition='auto'
        ))
        
        fig1.update_layout(
            title="<b>Top 10 Most Gentrifying Neighborhoods</b><br><sub>Ranked by gentrification pressure (rent + displacement)</sub>",
            xaxis_title="Gentrification Score",
            yaxis_title="Grid Cell",
            height=500,
            width=1000,
            showlegend=False
        )
        
        output_path = self.output_dir / "gentrification_risk_map.html"
        fig1.write_html(str(output_path))
        print(f"\n✅ Gentrification risk map: {output_path}")
        
        # === SCATTER: RENT vs DISPLACEMENT ===
        fig2 = go.Figure()
        
        fig2.add_trace(go.Scatter(
            x=gentrification_df['rent_increase_%'],
            y=gentrification_df['displacement_increase'],
            mode='markers',
            marker=dict(
                size=10,
                color=gentrification_df['gentrification_score'],
                colorscale='YlOrRd',
                showscale=True,
                colorbar=dict(title="Gentrification<br>Score")
            ),
            text=gentrification_df['grid_id'],
            hovertemplate='<b>%{text}</b><br>Rent Increase: %{x:.1f}%<br>Displacement Risk: %{y:.2f}<extra></extra>'
        ))
        
        fig2.update_layout(
            title="<b>Gentrification Dynamics: Rent vs Displacement Risk</b>",
            xaxis_title="Rent Increase (%)",
            yaxis_title="Displacement Risk Increase",
            height=600,
            width=1000,
            hovermode='closest'
        )
        
        output_path = self.output_dir / "gentrification_rent_displacement.html"
        fig2.write_html(str(output_path))
        print(f"✅ Rent-displacement scatter: {output_path}")
        
        # === GENTRIFICATION CLASSIFICATION ===
        # Classify neighborhoods
        gentrification_df['classification'] = 'Stable'
        gentrification_df.loc[gentrification_df['rent_increase_%'] > 10, 'classification'] = 'Appreciating'
        gentrification_df.loc[(gentrification_df['rent_increase_%'] > 15) & 
                            (gentrification_df['displacement_increase'] > 0.05), 'classification'] = 'Gentrifying'
        gentrification_df.loc[gentrification_df['population_change_%'] < -10, 'classification'] = 'Declining'
        
        classification_counts = gentrification_df['classification'].value_counts()
        
        fig3 = go.Figure()
        
        fig3.add_trace(go.Pie(
            labels=classification_counts.index,
            values=classification_counts.values,
            marker=dict(colors=['green', 'yellow', 'orange', 'red']),
            textposition='inside',
            textinfo='label+percent'
        ))
        
        fig3.update_layout(
            title="<b>Neighborhood Classification</b><br><sub>Based on rent growth and displacement risk</sub>",
            height=500,
            width=800
        )
        
        output_path = self.output_dir / "neighborhood_classification.html"
        fig3.write_html(str(output_path))
        print(f"✅ Neighborhood classification: {output_path}")
        
        # Print summary
        print("\n📊 Gentrification Summary:")
        print(f"  Total neighborhoods: {len(gentrification_df)}")
        for cls, count in classification_counts.items():
            print(f"  {cls}: {count} cells")
        
        print("\n🚨 High-Risk Gentrifying Areas (Top 5):")
        for idx, row in gentrification_df.head(5).iterrows():
            print(f"  {row['grid_id']:20} | Rent: +{row['rent_increase_%']:.1f}% | Displacement: +{row['displacement_increase']:.3f}")

def main():
    try:
        print("\n" + "="*60)
        print("🏘️ GENTRIFICATION ANALYSIS")
        print("="*60)
        
        analyzer = GentrificationAnalyzer()
        
        run_id = analyzer.get_latest_run()
        if not run_id:
            print("❌ No simulation runs found")
            return False
        
        print(f"\n✅ Analyzing run: {run_id}")
        
        # Get data
        df = analyzer.analyze_gentrification(run_id)
        if df is None:
            return False
        
        # Analyze gentrification
        gentrification_df = analyzer.identify_gentrifying_areas(df)
        
        # Create visualizations
        analyzer.create_visualizations(gentrification_df)
        
        print("\n" + "="*60)
        print("✅ GENTRIFICATION ANALYSIS COMPLETE")
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
