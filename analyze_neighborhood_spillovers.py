#!/usr/bin/env python3
"""
Spatial Spillover Effects Analysis: Visualize how changes ripple through neighborhoods.
Shows agglomeration, gentrification pressure, and performance clustering.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.append(str(Path(__file__).parent / "src"))

from database.db_config import db_config
from sqlalchemy import text

class SpilloverEffectsAnalyzer:
    """Analyze spatial spillover and neighborhood effects."""
    
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
    
    def get_grid_with_geometry(self, run_id):
        """Get grid cells with geometry information."""
        query = f"""
        SELECT DISTINCT
            sg.grid_id,
            ss.population,
            ss.avg_rent_euro,
            ss.safety_score,
            ss.commercial_vitality,
            ss.air_quality_index,
            ss.social_cohesion_index,
            st_x(st_centroid(sg.geometry)) as lon,
            st_y(st_centroid(sg.geometry)) as lat
        FROM simulation_state ss
        JOIN spatial_grid sg ON ss.grid_id = sg.grid_id
        WHERE ss.run_id = '{run_id}' 
            AND ss.timestep = (SELECT MAX(timestep) FROM simulation_state WHERE run_id = '{run_id}')
        ORDER BY sg.grid_id
        """
        
        with db_config.engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        return df
    
    def calculate_spatial_autocorrelation(self, grid_df, metric):
        """Calculate Moran's I for a metric (simplified)."""
        if metric not in grid_df.columns:
            return 0.5
        
        values = grid_df[metric].dropna().values
        if len(values) < 2:
            return 0.5
        
        mean_val = np.mean(values)
        
        # Simple autocorrelation: correlation of each value with spatial neighbors
        n = len(values)
        if n < 3:
            return 0.5
        
        # Assume grid ordering means spatial proximity
        correlations = []
        for i in range(n - 1):
            if not pd.isna(values[i]) and not pd.isna(values[i+1]) and values[i] is not None and values[i+1] is not None:
                try:
                    norm_i = (float(values[i]) - mean_val) / (np.std(values) + 1e-6)
                    norm_next = (float(values[i+1]) - mean_val) / (np.std(values) + 1e-6)
                    correlations.append(norm_i * norm_next)
                except:
                    pass
        
        return np.mean(correlations) if correlations else 0.5
    
    def create_spillover_heatmap(self, grid_df):
        """Create heatmap showing metric clustering."""
        
        metrics = ['population', 'avg_rent_euro', 'safety_score', 'commercial_vitality', 'air_quality_index']
        
        # Calculate spatial autocorrelation for each metric
        autocorr = {}
        for metric in metrics:
            if metric in grid_df.columns:
                autocorr[metric] = self.calculate_spatial_autocorrelation(grid_df, metric)
        
        # Create heatmap of spillover strength
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=list(autocorr.keys()),
            y=list(autocorr.values()),
            marker=dict(
                color=list(autocorr.values()),
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Clustering<br>Strength")
            ),
            text=[f"{v:.3f}" for v in autocorr.values()],
            textposition="auto"
        ))
        
        fig.update_layout(
            title="<b>Spatial Clustering Strength by Metric</b><br><sub>Higher values = stronger neighborhood effects</sub>",
            xaxis_title="Urban Metric",
            yaxis_title="Clustering Strength (Moran's I)",
            height=500,
            width=900,
            hovermode='x'
        )
        
        output_path = self.output_dir / "spillover_clustering.html"
        fig.write_html(str(output_path))
        print(f"\n✅ Spillover clustering: {output_path}")
        
        return autocorr
    
    def create_performance_gradient(self, grid_df):
        """Show how metrics change across space."""
        
        # Create performance composite
        grid_df = grid_df.copy()
        
        # Normalize metrics to 0-1
        for col in ['population', 'safety_score', 'commercial_vitality', 'social_cohesion_index']:
            if col in grid_df.columns and grid_df[col].max() > 0:
                grid_df[f'{col}_norm'] = (grid_df[col] - grid_df[col].min()) / (grid_df[col].max() - grid_df[col].min() + 1e-6)
        
        # Composite score: 40% population, 30% safety, 20% vitality, 10% cohesion
        grid_df['performance_score'] = (
            grid_df.get('population_norm', 0) * 0.4 +
            grid_df.get('safety_score_norm', 0) * 0.3 +
            grid_df.get('commercial_vitality_norm', 0) * 0.2 +
            grid_df.get('social_cohesion_index_norm', 0) * 0.1
        )
        
        # Also track rent pressure
        grid_df['rent_pressure'] = grid_df['avg_rent_euro'] / grid_df['avg_rent_euro'].mean()
        
        # Create scatter: performance vs rent (showing agglomeration)
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Urban Performance Gradient', 'Rent Pressure Distribution'),
            specs=[[{'type': 'scatter'}, {'type': 'scatter'}]]
        )
        
        # Plot 1: Performance across grid
        fig.add_trace(
            go.Scatter(
                x=grid_df['grid_id'],
                y=grid_df['performance_score'],
                mode='lines+markers',
                name='Performance Score',
                line=dict(color='blue', width=2),
                marker=dict(size=8),
                fill='tozeroy',
                fillcolor='rgba(0,100,200,0.2)'
            ),
            row=1, col=1
        )
        
        # Plot 2: Rent pressure
        fig.add_trace(
            go.Scatter(
                x=grid_df['grid_id'],
                y=grid_df['rent_pressure'],
                mode='lines+markers',
                name='Rent Pressure',
                line=dict(color='red', width=2),
                marker=dict(size=8),
                fill='tozeroy',
                fillcolor='rgba(200,0,0,0.2)'
            ),
            row=1, col=2
        )
        
        fig.update_yaxes(title_text="Score (0-1)", row=1, col=1)
        fig.update_yaxes(title_text="Multiplier (1.0 = average)", row=1, col=2)
        fig.update_xaxes(title_text="Grid Cell", row=1, col=1)
        fig.update_xaxes(title_text="Grid Cell", row=1, col=2)
        
        fig.update_layout(
            title="<b>Spatial Performance & Affordability Gradients</b><br><sub>How metrics and costs vary across neighborhoods</sub>",
            height=500,
            width=1200,
            hovermode='x unified'
        )
        
        output_path = self.output_dir / "performance_gradient.html"
        fig.write_html(str(output_path))
        print(f"✅ Performance gradient: {output_path}")
        
        return grid_df
    
    def create_agglomeration_analysis(self, grid_df):
        """Identify agglomeration clusters."""
        
        grid_df = grid_df.copy()
        
        # Identify high-value clusters
        high_performance = grid_df['performance_score'].quantile(0.75) if 'performance_score' in grid_df.columns else 0
        grid_df['is_cluster'] = grid_df.get('performance_score', 0) > high_performance
        
        # Count consecutive clusters
        grid_df['cluster_id'] = (grid_df['is_cluster'] != grid_df['is_cluster'].shift()).cumsum()
        clusters = grid_df[grid_df['is_cluster']].groupby('cluster_id').agg({
            'grid_id': 'count',
            'population': 'sum',
            'avg_rent_euro': 'mean',
            'commercial_vitality': 'mean'
        }).reset_index()
        clusters.columns = ['cluster_id', 'size', 'population', 'avg_rent', 'vitality']
        
        # Filter meaningful clusters (size >= 2)
        clusters = clusters[clusters['size'] >= 2].sort_values('population', ascending=False)
        
        # Create visualization
        if len(clusters) > 0:
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=[f"Cluster {i+1}" for i in range(len(clusters))],
                y=clusters['population'].values,
                marker=dict(
                    color=clusters['vitality'].values,
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Commercial<br>Vitality")
                ),
                text=clusters['avg_rent'].values,
                texttemplate="€%{text:.0f}",
                textposition="outside"
            ))
            
            fig.update_layout(
                title="<b>Agglomeration Clusters</b><br><sub>High-performance neighborhoods with significant spillover effects</sub>",
                xaxis_title="Cluster ID",
                yaxis_title="Total Population",
                height=500,
                width=900
            )
            
            output_path = self.output_dir / "agglomeration_clusters.html"
            fig.write_html(str(output_path))
            print(f"✅ Agglomeration clusters: {output_path}")
        
        return clusters

def main():
    try:
        print("\n" + "="*60)
        print("🌐 SPATIAL SPILLOVER EFFECTS ANALYSIS")
        print("="*60)
        
        analyzer = SpilloverEffectsAnalyzer()
        
        run_id = analyzer.get_latest_run()
        if not run_id:
            print("❌ No simulation runs found")
            return False
        
        print(f"\n✅ Analyzing run: {run_id}")
        
        # Get grid data
        grid_df = analyzer.get_grid_with_geometry(run_id)
        if grid_df is None or grid_df.empty:
            print("❌ No grid data available")
            return False
        
        print(f"✅ Loaded {len(grid_df)} grid cells")
        
        # Analyze spillover effects
        print("\n📊 Analyzing spillover mechanisms...")
        autocorr = analyzer.create_spillover_heatmap(grid_df)
        
        # Show performance gradients
        print("📊 Calculating performance gradients...")
        grid_with_perf = analyzer.create_performance_gradient(grid_df)
        
        # Identify agglomeration
        print("📊 Identifying agglomeration clusters...")
        clusters = analyzer.create_agglomeration_analysis(grid_with_perf)
        
        # Print summary
        print("\n📈 Spillover Summary:")
        print(f"  Strongest clustering: {max(autocorr.items(), key=lambda x: x[1])}")
        print(f"  Number of agglomeration clusters: {len(clusters)}")
        if len(clusters) > 0:
            print(f"  Largest cluster population: {clusters['population'].max():.0f}")
            print(f"  Cluster rent premium: {(clusters['avg_rent'].mean() / grid_df['avg_rent_euro'].mean() - 1) * 100:.1f}%")
        
        print("\n" + "="*60)
        print("✅ SPILLOVER ANALYSIS COMPLETE")
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
