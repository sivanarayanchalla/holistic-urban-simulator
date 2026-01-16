#!/usr/bin/env python3
"""
Multi-City Comparison Framework: Compare urban metrics across different cities.
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

class MultiCityComparator:
    """Compare urban metrics across multiple cities."""
    
    def __init__(self):
        self.output_dir = Path("data/outputs/visualizations")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_all_runs(self):
        """Get all completed simulation runs."""
        try:
            with db_config.engine.connect() as conn:
                query = text("""
                SELECT 
                    run_id,
                    city_name,
                    created_at
                FROM simulation_run 
                WHERE status = 'completed'
                ORDER BY created_at DESC
                """)
                result = pd.read_sql(query, conn)
            return result
        except Exception as e:
            print(f"[ERROR] Failed to retrieve runs: {e}")
            return pd.DataFrame()
    
    def get_run_metrics(self, run_id):
        """Get aggregated metrics for a run."""
        try:
            with db_config.engine.connect() as conn:
                query = text("""
                SELECT 
                    run_id,
                    COUNT(*) as num_cells,
                    COUNT(DISTINCT timestep) as num_timesteps,
                    ROUND(AVG(population)::numeric, 2) as avg_population,
                    ROUND(AVG(avg_rent_euro)::numeric, 2) as avg_rent,
                    ROUND(AVG(employment)::numeric, 2) as avg_employment,
                    ROUND(AVG(safety)::numeric, 2) as avg_safety,
                    ROUND(AVG(vitality)::numeric, 2) as avg_vitality,
                    ROUND(AVG(transit_access)::numeric, 2) as avg_transit,
                    ROUND(AVG(air_quality)::numeric, 2) as avg_air_quality,
                    ROUND(AVG(green_space)::numeric, 2) as avg_green_space,
                    ROUND(AVG(social_cohesion)::numeric, 2) as avg_social_cohesion
                FROM simulation_state 
                WHERE run_id = :run_id
                GROUP BY run_id
                """)
                result = pd.read_sql(query, conn, params={"run_id": run_id})
            return result
        except Exception as e:
            print(f"[WARN] Could not get metrics for {run_id}: {e}")
            return None
    
    def create_city_comparison(self, runs_df):
        """Create comparison dataframe for all cities."""
        try:
            comparison_data = []
            
            for _, run in runs_df.iterrows():
                metrics = self.get_run_metrics(run['run_id'])
                if metrics is not None and not metrics.empty:
                    metrics['city_name'] = run['city_name']
                    comparison_data.append(metrics)
            
            if not comparison_data:
                print("[ERROR] No metrics available")
                return None
            
            comp_df = pd.concat(comparison_data, ignore_index=True)
            
            # Create radar chart
            metrics_cols = ['avg_population', 'avg_rent', 'avg_employment', 
                          'avg_safety', 'avg_vitality', 'avg_transit']
            
            fig = go.Figure()
            
            for city in comp_df['city_name'].unique():
                city_data = comp_df[comp_df['city_name'] == city]
                
                if city_data.empty:
                    continue
                
                # Normalize metrics to 0-1 range for radar
                normalized = {}
                for col in metrics_cols:
                    val = float(city_data[col].iloc[0]) if pd.notna(city_data[col].iloc[0]) else 0
                    # Handle normalization
                    if col == 'avg_population':
                        normalized[col] = min(val / 4000000, 1.0)
                    elif col == 'avg_rent':
                        normalized[col] = min(val / 2000, 1.0)
                    else:
                        normalized[col] = min(val, 1.0)
                
                fig.add_trace(go.Scatterpolar(
                    r=[normalized.get(col, 0) for col in metrics_cols],
                    theta=['Population', 'Rent', 'Employment', 'Safety', 'Vitality', 'Transit'],
                    fill='toself',
                    name=str(city) if pd.notna(city) else 'Unknown'
                ))
            
            fig.update_layout(
                title='Multi-City Performance Comparison (Normalized Metrics)',
                polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                showlegend=True,
                height=600
            )
            
            output_path = self.output_dir / "multi_city_comparison.html"
            fig.write_html(str(output_path))
            print(f"[OK] Multi-city comparison: {output_path}")
            
            return comp_df
            
        except Exception as e:
            print(f"[ERROR] Error creating comparison: {e}")
            return None
    
    def create_inequality_comparison(self, runs_df):
        """Create inequality metrics comparison."""
        try:
            inequality_data = []
            
            for _, run in runs_df.iterrows():
                metrics = self.get_run_metrics(run['run_id'])
                if metrics is not None and not metrics.empty:
                    # Calculate Gini-like measure from population variance
                    try:
                        with db_config.engine.connect() as conn:
                            query = text("""
                            SELECT 
                                STDDEV(population) as pop_stddev,
                                AVG(population) as pop_avg,
                                STDDEV(avg_rent_euro) as rent_stddev,
                                AVG(avg_rent_euro) as rent_avg
                            FROM simulation_state 
                            WHERE run_id = :run_id AND timestep = 50
                            """)
                            ineq = pd.read_sql(query, conn, params={"run_id": run['run_id']})
                        
                        if not ineq.empty:
                            ineq_row = ineq.iloc[0]
                            gini = (float(ineq_row['pop_stddev'] or 0) / float(ineq_row['pop_avg'] or 1) + 
                                   float(ineq_row['rent_stddev'] or 0) / float(ineq_row['rent_avg'] or 1)) / 2
                            inequality_data.append({
                                'city_name': run['city_name'],
                                'inequality_index': gini
                            })
                    except:
                        pass
            
            if inequality_data:
                ineq_df = pd.DataFrame(inequality_data)
                ineq_df = ineq_df.sort_values('inequality_index', ascending=False)
                
                fig = go.Figure(data=[
                    go.Bar(
                        x=ineq_df['city_name'].astype(str),
                        y=ineq_df['inequality_index'],
                        marker_color='indianred'
                    )
                ])
                
                fig.update_layout(
                    title='Inequality Index by City (Lower is Better)',
                    xaxis_title='City',
                    yaxis_title='Inequality Index',
                    height=500
                )
                
                output_path = self.output_dir / "inequality_comparison.html"
                fig.write_html(str(output_path))
                print(f"[OK] Inequality comparison: {output_path}")
                
                return ineq_df
            
            return None
            
        except Exception as e:
            print(f"[WARN] Could not create inequality comparison: {e}")
            return None
    
    def create_performance_matrix(self, comp_df):
        """Create heatmap of city performance metrics."""
        try:
            metrics_cols = ['avg_population', 'avg_rent', 'avg_employment', 
                          'avg_safety', 'avg_vitality', 'avg_transit']
            
            matrix_data = comp_df[['city_name'] + metrics_cols].copy()
            matrix_data = matrix_data.set_index('city_name')
            
            # Normalize for heatmap
            for col in metrics_cols:
                col_min = matrix_data[col].min()
                col_max = matrix_data[col].max()
                if col_max > col_min:
                    matrix_data[col] = (matrix_data[col] - col_min) / (col_max - col_min)
            
            fig = go.Figure(data=go.Heatmap(
                z=matrix_data.values,
                x=['Population', 'Rent', 'Employment', 'Safety', 'Vitality', 'Transit'],
                y=matrix_data.index.astype(str),
                colorscale='Viridis'
            ))
            
            fig.update_layout(
                title='City Performance Matrix (Normalized Scores)',
                height=400
            )
            
            output_path = self.output_dir / "city_performance_matrix.html"
            fig.write_html(str(output_path))
            print(f"[OK] Performance matrix: {output_path}")
            
        except Exception as e:
            print(f"[WARN] Could not create performance matrix: {e}")
    
    def print_summary(self, comp_df, ineq_df):
        """Print summary of comparison."""
        try:
            print("\n[*] City Comparison Summary:")
            print("-" * 60)
            
            if comp_df is not None and not comp_df.empty:
                for _, city_data in comp_df.iterrows():
                    city_name = str(city_data['city_name']) if pd.notna(city_data['city_name']) else 'Unknown'
                    print(f"\n{city_name}:")
                    print(f"  Population: {city_data['avg_population']:.0f}")
                    print(f"  Rent (EUR): {city_data['avg_rent']:.0f}")
                    print(f"  Employment: {city_data['avg_employment']:.2f}")
                    print(f"  Safety: {city_data['avg_safety']:.2f}")
                    print(f"  Vitality: {city_data['avg_vitality']:.2f}")
                    print(f"  Transit Access: {city_data['avg_transit']:.2f}")
            
            if ineq_df is not None and not ineq_df.empty:
                print("\n[*] Inequality Rankings (lower is better):")
                for _, row in ineq_df.iterrows():
                    print(f"  {row['city_name']}: {row['inequality_index']:.3f}")

        except Exception as e:
            print(f"[WARN] Could not print summary: {e}")

def main():
    """Run multi-city comparison analysis."""
    try:
        print("\n" + "="*60)
        print("[*] MULTI-CITY COMPARISON FRAMEWORK")
        print("="*60)
        
        comparator = MultiCityComparator()
        
        # Get all runs
        runs_df = comparator.get_all_runs()
        
        if len(runs_df) == 0:
            print("\n[ERROR] No simulation runs found")
            print("\nTo use multi-city comparison:")
            print("  1. Run simulations for different cities")
            print("  2. Set city_name in simulation_run table")
            print("  3. Re-run this script")
            return False
        
        print(f"\n[OK] Found {len(runs_df)} simulation runs")
        
        # Detect city names
        cities = runs_df['city_name'].unique()
        print(f"   Cities: {', '.join([str(c) for c in cities if c])}")
        
        # Create comparisons
        print("\n[*] Creating comparison visualizations...")
        
        comp_df = comparator.create_city_comparison(runs_df)
        inequality_df = comparator.create_inequality_comparison(runs_df)
        
        if comp_df is not None:
            comparator.create_performance_matrix(comp_df)
            comparator.print_summary(comp_df, inequality_df)
        
        print("\n" + "="*60)
        print("[OK] MULTI-CITY ANALYSIS COMPLETE")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
