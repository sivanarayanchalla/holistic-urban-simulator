#!/usr/bin/env python3
"""
Create interactive dashboard for simulation results.
"""
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import geopandas as gpd
from shapely import wkt
from shapely.geometry import shape
import json

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from database.db_config import db_config
from database.utils import DatabaseUtils
from sqlalchemy import text

class SimulationVisualizer:
    """Create visualizations for simulation results."""
    
    def __init__(self):
        self.output_dir = Path("data/outputs/visualizations")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_latest_simulation_run(self):
        """Get the latest simulation run from database."""
        print("Fetching latest simulation run...")
        
        query = """
        SELECT run_id, name, created_at, total_timesteps
        FROM simulation_run 
        WHERE status = 'completed'
        ORDER BY created_at DESC 
        LIMIT 1
        """
        
        with db_config.engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        if df.empty:
            print("❌ No completed simulation runs found.")
            return None
        
        run_id = df.iloc[0]['run_id']
        run_name = df.iloc[0]['name']
        
        print(f"✅ Found: {run_name}")
        print(f"   Run ID: {run_id}")
        print(f"   Created: {df.iloc[0]['created_at']}")
        
        return str(run_id)  # Convert UUID to string
    
    def get_simulation_data(self, run_id):
        """Get simulation data for a specific run."""
        run_id_str = str(run_id)  # Ensure it's a string
        print(f"\nFetching simulation data for run {run_id_str[:8]}...")
        
        # Get simulation states with geometry from spatial_grid
        query = f"""
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
            ss.charger_density_per_sqkm,
            ST_AsText(sg.geometry) as geometry
        FROM simulation_state ss
        LEFT JOIN spatial_grid sg ON ss.grid_id = sg.grid_id
        WHERE ss.run_id = '{run_id_str}'
        ORDER BY ss.timestep, ss.grid_id
        """
        
        with db_config.engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        if df.empty:
            print("❌ No simulation data found.")
            return None
        
        print(f"✅ Loaded {len(df)} state records")
        print(f"   Timesteps: {df['timestep'].nunique()}")
        print(f"   Grid cells: {df['grid_id'].nunique()}")
        
        return df
    
    def create_timeline_plot(self, df, run_id):
        """Create timeline plot of simulation metrics."""
        run_id_str = str(run_id)  # Ensure it's a string
        print(f"\nCreating timeline plot for run {run_id_str[:8]}...")
        
        if df is None or df.empty:
            print("❌ No data for timeline plot")
            return None
        
        # Check for required columns
        required_columns = ['timestep', 'population', 'traffic_congestion', 
                          'safety_score', 'avg_rent_euro']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"⚠️  Missing columns for timeline: {missing_columns}")
            
            # Try alternative column names
            if 'commercial_vitality' not in df.columns and 'commercial' in df.columns:
                df = df.rename(columns={'commercial': 'commercial_vitality'})
            
            # Check again
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                print(f"❌ Still missing columns: {missing_columns}")
                return None
        
        # Aggregate by timestep
        agg_dict = {
            'population': 'mean',
            'traffic_congestion': 'mean',
            'safety_score': 'mean',
            'avg_rent_euro': 'mean'
        }
        
        # Add EV metrics if available
        if 'chargers_count' in df.columns:
            agg_dict['chargers_count'] = 'sum'
        if 'ev_capacity_kw' in df.columns:
            agg_dict['ev_capacity_kw'] = 'sum'
        if 'charger_density_per_sqkm' in df.columns:
            agg_dict['charger_density_per_sqkm'] = 'mean'
        if 'air_quality_index' in df.columns:
            agg_dict['air_quality_index'] = 'mean'
        
        timeline_data = df.groupby('timestep').agg(agg_dict).reset_index()
        
        # Create figure with multiple y-axes
        fig = go.Figure()
        
        # Primary y-axis: Population and Congestion
        fig.add_trace(go.Scatter(
            x=timeline_data['timestep'],
            y=timeline_data['population'],
            name="Population",
            line=dict(color='blue', width=2),
            yaxis="y1"
        ))
        
        fig.add_trace(go.Scatter(
            x=timeline_data['timestep'],
            y=timeline_data['traffic_congestion'],
            name="Traffic Congestion",
            line=dict(color='red', width=2),
            yaxis="y1"
        ))
        
        # Secondary y-axis: Safety Score
        fig.add_trace(go.Scatter(
            x=timeline_data['timestep'],
            y=timeline_data['safety_score'],
            name="Safety Score",
            line=dict(color='green', width=2),
            yaxis="y2"
        ))
        
        # Tertiary y-axis: Rent
        fig.add_trace(go.Scatter(
            x=timeline_data['timestep'],
            y=timeline_data['avg_rent_euro'],
            name="Avg Rent (€)",
            line=dict(color='orange', width=2),
            yaxis="y3"
        ))
        
        # Add EV Infrastructure traces if available
        if 'chargers_count' in timeline_data.columns and timeline_data['chargers_count'].sum() > 0:
            fig.add_trace(go.Scatter(
                x=timeline_data['timestep'],
                y=timeline_data['chargers_count'],
                name="Total Chargers",
                line=dict(color='purple', width=2, dash='dash'),
                yaxis="y4"
            ))
        
        if 'ev_capacity_kw' in timeline_data.columns and timeline_data['ev_capacity_kw'].sum() > 0:
            fig.add_trace(go.Scatter(
                x=timeline_data['timestep'],
                y=timeline_data['ev_capacity_kw'],
                name="EV Capacity (kW)",
                line=dict(color='teal', width=2, dash='dot'),
                yaxis="y5"
            ))
        
        if 'air_quality_index' in timeline_data.columns:
            fig.add_trace(go.Scatter(
                x=timeline_data['timestep'],
                y=timeline_data['air_quality_index'],
                name="Air Quality Index",
                line=dict(color='cyan', width=2),
                yaxis="y6"
            ))
        
        # Update layout with multiple y-axes - FIXED: using correct property names
        fig.update_layout(
            title=f"Urban Simulation Metrics Over Time",
            xaxis_title="Timestep",
            yaxis=dict(
                title=dict(
                    text="Population / Congestion",
                    font=dict(color="blue")
                ),
                tickfont=dict(color="blue")
            ),
            yaxis2=dict(
                title=dict(
                    text="Safety Score (0-1)",
                    font=dict(color="green")
                ),
                tickfont=dict(color="green"),
                anchor="x",
                overlaying="y",
                side="right",
                range=[0, 1]
            ),
            yaxis3=dict(
                title=dict(
                    text="Rent (€)",
                    font=dict(color="orange")
                ),
                tickfont=dict(color="orange"),
                anchor="free",
                overlaying="y",
                side="right",
                position=0.95,
                range=[0, timeline_data['avg_rent_euro'].max() * 1.1] if not timeline_data['avg_rent_euro'].empty else [0, 1000]
            ),
            yaxis4=dict(
                title=dict(
                    text="Chargers Count",
                    font=dict(color="purple")
                ),
                tickfont=dict(color="purple"),
                anchor="free",
                overlaying="y",
                side="left",
                position=0.10
            ),
            yaxis5=dict(
                title=dict(
                    text="EV Capacity (kW)",
                    font=dict(color="teal")
                ),
                tickfont=dict(color="teal"),
                anchor="free",
                overlaying="y",
                side="left",
                position=0.15
            ),
            yaxis6=dict(
                title=dict(
                    text="Air Quality",
                    font=dict(color="cyan")
                ),
                tickfont=dict(color="cyan"),
                anchor="free",
                overlaying="y",
                side="right",
                position=0.85
            ),
            hovermode="x unified",
            template="plotly_white",
            height=600,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        # Save figure
        timeline_path = self.output_dir / f"timeline_{run_id_str[:8]}.html"
        fig.write_html(str(timeline_path))
        
        try:
            fig.write_image(str(self.output_dir / f"timeline_{run_id_str[:8]}.png"))
        except:
            print("  ⚠️  Could not save PNG (kaleido package required for static image export)")
        
        print(f"✅ Timeline plot saved: {timeline_path}")
        return fig
    
    def create_spatial_map(self, df, run_id, timestep=0):
        """Create spatial map of simulation metric."""
        run_id_str = str(run_id)
        print(f"\nCreating spatial map for timestep {timestep}...")
        
        # Filter for specific timestep
        timestep_data = df[df['timestep'] == timestep].copy()
        
        if timestep_data.empty:
            print(f"❌ No data for timestep {timestep}")
            return None
        
        # Check if geometry column exists
        if 'geometry' not in timestep_data.columns:
            print("❌ No geometry data found in simulation results")
            
            # Try to get geometry from spatial_grid table
            try:
                with db_config.engine.connect() as conn:
                    # Get all grid cells with geometries - use ST_AsText to get WKT format
                    grid_query = """
                    SELECT grid_id, ST_AsText(geometry) as geometry
                    FROM spatial_grid
                    """
                    grid_df = pd.read_sql(grid_query, conn)
                    
                    # Merge with simulation data
                    if not grid_df.empty:
                        timestep_data = pd.merge(timestep_data, grid_df, on='grid_id', how='left')
                        print(f"✅ Loaded geometries from spatial_grid table")
            except Exception as e:
                print(f"❌ Could not load geometries: {e}")
                return None
        
        if 'geometry' not in timestep_data.columns:
            print("❌ Still no geometry data available")
            return None
        
        # Remove rows with None geometry
        timestep_data = timestep_data[timestep_data['geometry'].notna()].copy()
        
        if timestep_data.empty:
            print("❌ No valid geometry data after cleaning")
            return None
        
        # Convert geometry to shapely objects (handle both WKT and WKB formats)
        def parse_geometry(geom):
            if geom is None:
                return None
            if isinstance(geom, str):
                # Try WKT first
                try:
                    return wkt.loads(geom)
                except:
                    pass
                # Try WKB (hex string)
                try:
                    return shape(json.loads(geom))
                except:
                    return None
            return geom
        
        try:
            timestep_data['geometry'] = timestep_data['geometry'].apply(parse_geometry)
            timestep_data = timestep_data[timestep_data['geometry'].notna()].copy()
            if timestep_data.empty:
                print("❌ Could not parse any valid geometries")
                return None
        except Exception as e:
            print(f"❌ Error parsing geometry: {e}")
            return None
        
        # Convert to GeoDataFrame
        gdf = gpd.GeoDataFrame(timestep_data, geometry='geometry', crs="EPSG:4326")
        
        # Check if we have traffic_congestion data
        if 'traffic_congestion' not in gdf.columns:
            print("❌ No traffic congestion data available")
            return None
        
        # Create choropleth map for traffic congestion
        try:
            fig = px.choropleth_mapbox(
                gdf,
                geojson=gdf.geometry,
                locations=gdf.index,
                color='traffic_congestion',
                color_continuous_scale="Viridis",
                range_color=(0, 1),
                mapbox_style="carto-positron",
                zoom=10,
                center={"lat": gdf.geometry.centroid.y.mean(), 
                       "lon": gdf.geometry.centroid.x.mean()},
                opacity=0.7,
                labels={'traffic_congestion': 'Traffic Congestion'},
                title=f"Traffic Congestion - Timestep {timestep}",
                hover_data=['population', 'safety_score', 'avg_rent_euro'] if all(col in gdf.columns for col in ['population', 'safety_score', 'avg_rent_euro']) else []
            )
            
            fig.update_layout(
                height=700,
                margin={"r":0,"t":40,"l":0,"b":0}
            )
            
            # Save figure
            map_path = self.output_dir / f"map_congestion_t{timestep}_{run_id_str[:8]}.html"
            fig.write_html(str(map_path))
            
            print(f"✅ Spatial map saved: {map_path}")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating spatial map: {e}")
            return None
    
    def create_metric_correlation(self, df, run_id, timestep=None):
        """Create correlation matrix of simulation metrics."""
        run_id_str = str(run_id)
        print(f"\nCreating metric correlation plot for run {run_id_str[:8]}...")
        
        if timestep is None:
            # Use latest timestep
            timestep = df['timestep'].max()
        
        # Filter for specific timestep
        timestep_data = df[df['timestep'] == timestep].copy()
        
        if timestep_data.empty:
            print(f"❌ No data for timestep {timestep}")
            return None
        
        # Select numeric columns for correlation
        numeric_cols = ['population', 'traffic_congestion', 'safety_score', 
                       'avg_rent_euro', 'commercial_vitality', 'displacement_risk']
        
        # Filter to available columns
        available_cols = [col for col in numeric_cols if col in timestep_data.columns]
        
        if len(available_cols) < 2:
            print(f"❌ Not enough numeric columns for correlation. Available: {available_cols}")
            return None
        
        corr_data = timestep_data[available_cols]
        
        # Calculate correlation matrix
        corr_matrix = corr_data.corr()
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu',
            zmid=0,
            text=corr_matrix.round(2).values,
            texttemplate='%{text}',
            textfont={"size": 10}
        ))
        
        fig.update_layout(
            title=f"Metric Correlations - Timestep {timestep}",
            height=600,
            xaxis_title="Metrics",
            yaxis_title="Metrics",
            template="plotly_white"
        )
        
        # Save figure
        corr_path = self.output_dir / f"correlation_t{timestep}_{run_id_str[:8]}.html"
        fig.write_html(str(corr_path))
        
        try:
            fig.write_image(str(self.output_dir / f"correlation_t{timestep}_{run_id_str[:8]}.png"))
        except:
            print("  ⚠️  Could not save PNG (kaleido package required)")
        
        print(f"✅ Correlation plot saved: {corr_path}")
        return fig
    
    def create_ev_comparison_plot(self, df, run_id):
        """Create comparison plot: cells with chargers vs without."""
        run_id_str = str(run_id)
        print(f"\nCreating EV impact comparison plot...")
        
        if 'chargers_count' not in df.columns:
            print("⚠️  No charger data available for comparison")
            return None
        
        # Classify cells
        df['has_chargers'] = df['chargers_count'] > 0
        
        # Get final timestep
        final_timestep = df['timestep'].max()
        final_df = df[df['timestep'] == final_timestep].copy()
        
        # Compare metrics
        comparison_data = []
        metrics = ['population', 'avg_rent_euro', 'safety_score', 'traffic_congestion', 'air_quality_index']
        
        for has_chargers in [True, False]:
            subset = final_df[final_df['has_chargers'] == has_chargers]
            if subset.empty:
                continue
            
            label = "With EV Chargers" if has_chargers else "Without Chargers"
            
            for metric in metrics:
                if metric in subset.columns:
                    comparison_data.append({
                        'Group': label,
                        'Metric': metric,
                        'Value': subset[metric].mean()
                    })
        
        if not comparison_data:
            print("⚠️  No comparison data")
            return None
        
        comp_df = pd.DataFrame(comparison_data)
        
        # Create subplots for each metric
        fig = go.Figure()
        
        for metric in metrics:
            metric_data = comp_df[comp_df['Metric'] == metric]
            for group in metric_data['Group'].unique():
                group_data = metric_data[metric_data['Group'] == group]
                value = group_data['Value'].values[0] if len(group_data) > 0 else 0
                
                fig.add_trace(go.Bar(
                    name=group,
                    x=[metric],
                    y=[value],
                    showlegend=(metric == metrics[0])  # Only show legend for first metric
                ))
        
        fig.update_layout(
            title="EV Infrastructure Impact on Urban Metrics (Final Timestep)",
            xaxis_title="Metrics",
            yaxis_title="Average Value",
            barmode="group",
            hovermode="x unified",
            template="plotly_white",
            height=500
        )
        
        # Save figure
        comp_path = self.output_dir / f"ev_comparison_{run_id_str[:8]}.html"
        fig.write_html(str(comp_path))
        
        try:
            fig.write_image(str(self.output_dir / f"ev_comparison_{run_id_str[:8]}.png"))
        except:
            print("  ⚠️  Could not save PNG")
        
        print(f"✅ EV comparison plot saved: {comp_path}")
        return fig
    
    def create_dashboard_html(self, run_id, run_name):
        """Create comprehensive HTML dashboard."""
        run_id_str = str(run_id)
        print(f"\nCreating HTML dashboard for run {run_id_str[:8]}...")
        
        # Get simulation data
        df = self.get_simulation_data(run_id_str)
        
        if df is None:
            print("❌ Cannot create dashboard without data")
            return None
        
        # Create visualizations
        timeline_fig = self.create_timeline_plot(df, run_id_str)
        first_timestep = df['timestep'].min() if not df.empty else 0
        spatial_fig = self.create_spatial_map(df, run_id_str, timestep=first_timestep)
        corr_fig = self.create_metric_correlation(df, run_id_str, timestep=min(50, df['timestep'].max()))
        
        # Calculate summary statistics
        summary_stats = {}
        if not df.empty:
            numeric_cols = ['population', 'traffic_congestion', 'safety_score', 
                          'avg_rent_euro', 'commercial_vitality', 'displacement_risk']
            
            for col in numeric_cols:
                if col in df.columns:
                    summary_stats[col] = {
                        'mean': df[col].mean(),
                        'min': df[col].min(),
                        'max': df[col].max(),
                        'std': df[col].std()
                    }
        
        # Create HTML dashboard
        dashboard_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Urban Simulation Dashboard</title>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: #333;
                }}
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-bottom: 5px solid #ff6b6b;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 2.5em;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                }}
                .header p {{
                    margin: 10px 0 0;
                    opacity: 0.9;
                    font-size: 1.1em;
                }}
                .run-info {{
                    display: flex;
                    justify-content: space-around;
                    background: #f8f9fa;
                    padding: 20px;
                    border-bottom: 1px solid #dee2e6;
                }}
                .info-box {{
                    text-align: center;
                    padding: 15px;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    min-width: 150px;
                }}
                .info-box h3 {{
                    margin: 0 0 10px;
                    color: #4b6cb7;
                    font-size: 0.9em;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                .info-box p {{
                    margin: 0;
                    font-size: 1.4em;
                    font-weight: bold;
                    color: #182848;
                }}
                .content {{
                    padding: 30px;
                }}
                .section {{
                    margin: 40px 0;
                    padding: 25px;
                    background: #f8f9fa;
                    border-radius: 15px;
                    box-shadow: 0 8px 16px rgba(0,0,0,0.1);
                }}
                .section h2 {{
                    color: #4b6cb7;
                    border-bottom: 3px solid #ff6b6b;
                    padding-bottom: 10px;
                    margin-top: 0;
                }}
                .plot-container {{
                    margin: 20px 0;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                }}
                .summary {{
                    background: #e9ecef;
                    padding: 20px;
                    border-radius: 10px;
                    margin-top: 30px;
                    border-left: 5px solid #4b6cb7;
                }}
                .summary h3 {{
                    color: #4b6cb7;
                    margin-top: 0;
                }}
                .stat-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-top: 20px;
                }}
                .stat-item {{
                    background: white;
                    padding: 15px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .stat-name {{
                    font-weight: bold;
                    color: #4b6cb7;
                    margin-bottom: 5px;
                }}
                .stat-value {{
                    font-size: 1.2em;
                    color: #182848;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    background: #182848;
                    color: white;
                    margin-top: 40px;
                }}
                .footer a {{
                    color: #ff6b6b;
                    text-decoration: none;
                }}
                .footer a:hover {{
                    text-decoration: underline;
                }}
                @media (max-width: 768px) {{
                    .run-info {{
                        flex-wrap: wrap;
                    }}
                    .info-box {{
                        flex: 1 1 150px;
                        margin: 10px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌆 Urban Simulation Dashboard</h1>
                    <p>Holistic Urban Simulator - Visualizing City Dynamics</p>
                </div>
                
                <div class="run-info">
                    <div class="info-box">
                        <h3>Run ID</h3>
                        <p>{run_id_str[:8]}...</p>
                    </div>
                    <div class="info-box">
                        <h3>Simulation Name</h3>
                        <p>{run_name[:50] if len(run_name) > 50 else run_name}</p>
                    </div>
                    <div class="info-box">
                        <h3>Timesteps</h3>
                        <p>{df['timestep'].nunique() if 'timestep' in df.columns else 0}</p>
                    </div>
                    <div class="info-box">
                        <h3>Grid Cells</h3>
                        <p>{df['grid_id'].nunique() if 'grid_id' in df.columns else 0}</p>
                    </div>
                    <div class="info-box">
                        <h3>Total Records</h3>
                        <p>{len(df):,}</p>
                    </div>
                </div>
                
                <div class="content">
        """
        
        # Add timeline section
        if timeline_fig:
            dashboard_html += """
                    <div class="section">
                        <h2>📈 Timeline Analysis</h2>
                        <p>How urban metrics evolve over simulation timesteps. Population growth affects traffic, which influences safety scores and housing prices.</p>
                        <div class="plot-container">
                            <iframe src="timeline_""" + run_id_str[:8] + """.html" width="100%" height="600" frameborder="0"></iframe>
                        </div>
                    </div>
            """
        else:
            dashboard_html += """
                    <div class="section">
                        <h2>📈 Timeline Analysis</h2>
                        <p style="color: #dc3545;">⚠️ Timeline plot could not be generated. This might be due to missing data columns or insufficient data.</p>
                    </div>
            """
        
        # Add spatial section
        if spatial_fig:
            dashboard_html += f"""
                    <div class="section">
                        <h2>🗺️ Spatial Distribution (Timestep {first_timestep})</h2>
                        <p>Geographic distribution of traffic congestion across Leipzig's grid cells.</p>
                        <div class="plot-container">
                            <iframe src="map_congestion_t{first_timestep}_{run_id_str[:8]}.html" width="100%" height="700" frameborder="0"></iframe>
                        </div>
                    </div>
            """
        else:
            dashboard_html += """
                    <div class="section">
                        <h2>🗺️ Spatial Distribution</h2>
                        <p style="color: #dc3545;">⚠️ Spatial map could not be generated. This might be due to missing geometry data or geographic coordinates.</p>
                    </div>
            """
        
        # Add correlation section
        if corr_fig:
            dashboard_html += """
                    <div class="section">
                        <h2>🔗 Metric Correlations</h2>
                        <p>How different urban metrics relate to each other. Positive values (red) indicate positive correlation, negative values (blue) indicate inverse relationships.</p>
                        <div class="plot-container">
                            <iframe src="correlation_t""" + str(min(50, df['timestep'].max() if 'timestep' in df.columns else 0)) + "_" + run_id_str[:8] + """.html" width="100%" height="600" frameborder="0"></iframe>
                        </div>
                    </div>
            """
        else:
            dashboard_html += """
                    <div class="section">
                        <h2>🔗 Metric Correlations</h2>
                        <p style="color: #dc3545;">⚠️ Correlation plot could not be generated. This might be due to insufficient numeric data or only one timestep available.</p>
                    </div>
            """
        
        # Add data summary
        if summary_stats:
            dashboard_html += """
                    <div class="summary">
                        <h3>📊 Simulation Summary Statistics</h3>
                        <div class="stat-grid">
            """
            
            for metric, stats in summary_stats.items():
                metric_display = metric.replace('_', ' ').title()
                dashboard_html += f"""
                            <div class="stat-item">
                                <div class="stat-name">{metric_display}</div>
                                <div class="stat-value">
                                    Mean: {stats['mean']:.2f}<br>
                                    Range: {stats['min']:.2f} - {stats['max']:.2f}
                                </div>
                            </div>
                """
            
            dashboard_html += """
                        </div>
                        <p style="margin-top: 15px; font-style: italic;">This simulation shows how urban systems interact. Areas with higher commercial vitality tend to have better safety scores but higher rents. Traffic congestion increases with population density, affecting overall quality of life.</p>
                    </div>
            """
        else:
            dashboard_html += """
                    <div class="summary">
                        <h3>📊 Simulation Summary</h3>
                        <p style="color: #dc3545;">⚠️ Summary statistics could not be calculated due to insufficient data.</p>
                    </div>
            """
        
        # Add footer and closing
        dashboard_html += """
                </div>
                
                <div class="footer">
                    <p>Generated by Holistic Urban Simulator | Created: """ + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
                    <p>Next steps: 
                        <a href="#" onclick="alert('Run: python run_simulation.py\\nVisualize: python run_visualization.py')">Run New Simulation</a> | 
                        <a href="#" onclick="alert('Check database: SELECT * FROM simulation_state LIMIT 10;')">Analyze Data</a> | 
                        <a href="#" onclick="alert('Edit modules in src/core_engine/simulation_engine.py')">Modify Modules</a>
                    </p>
                </div>
            </div>
            
            <script>
                // Simple interactivity
                document.addEventListener('DOMContentLoaded', function() {
                    console.log('Urban Simulation Dashboard loaded successfully!');
                    
                    // Highlight sections on hover
                    const sections = document.querySelectorAll('.section');
                    sections.forEach(section => {
                        section.addEventListener('mouseenter', function() {
                            this.style.transform = 'translateY(-5px)';
                            this.style.boxShadow = '0 12px 24px rgba(0,0,0,0.2)';
                            this.style.transition = 'transform 0.3s, box-shadow 0.3s';
                        });
                        section.addEventListener('mouseleave', function() {
                            this.style.transform = 'translateY(0)';
                            this.style.boxShadow = '0 8px 16px rgba(0,0,0,0.1)';
                        });
                    });
                    
                    // Make info boxes interactive
                    const infoBoxes = document.querySelectorAll('.info-box');
                    infoBoxes.forEach(box => {
                        box.addEventListener('click', function() {
                            const h3 = this.querySelector('h3');
                            alert('Clicked: ' + h3.textContent);
                        });
                    });
                });
            </script>
        </body>
        </html>
        """
        
        # Save dashboard
        dashboard_path = self.output_dir / f"dashboard_{run_id_str[:8]}.html"
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            f.write(dashboard_html)
        
        print(f"✅ Dashboard created: {dashboard_path}")
        return dashboard_path
    
    def run(self):
        """Run complete visualization pipeline."""
        print("=" * 60)
        print("URBAN SIMULATION VISUALIZATION")
        print("=" * 60)
        
        # Get latest run
        run_id = self.get_latest_simulation_run()
        if run_id is None:
            print("⚠️  No simulation runs found. Please run a simulation first.")
            print("   Command: python run_simulation.py")
            return False
        
        # Get run name
        with db_config.engine.connect() as conn:
            query = f"SELECT name FROM simulation_run WHERE run_id = '{run_id}'"
            result = pd.read_sql(query, conn)
            if not result.empty:
                run_name = result.iloc[0]['name']
            else:
                run_name = "Unknown Simulation"
        
        # Get simulation data
        df = self.get_simulation_data(run_id)
        if df is None:
            print("❌ Failed to get simulation data")
            return False
        
        # Create visualizations
        print("\n📊 Creating visualizations...")
        self.create_timeline_plot(df, run_id)
        
        # Use first and last available timesteps (not 0 which may not exist)
        first_timestep = df['timestep'].min()
        last_timestep = df['timestep'].max()
        
        self.create_spatial_map(df, run_id, timestep=first_timestep)
        self.create_spatial_map(df, run_id, timestep=last_timestep)
        self.create_metric_correlation(df, run_id, timestep=last_timestep)
        
        # Create EV-specific visualization if charger data available
        if 'chargers_count' in df.columns and df['chargers_count'].sum() > 0:
            self.create_ev_comparison_plot(df, run_id)
        
        # Create dashboard
        dashboard_path = self.create_dashboard_html(run_id, run_name)
        
        if dashboard_path:
            print("\n" + "=" * 60)
            print("✅ VISUALIZATION COMPLETE")
            print("=" * 60)
            print(f"\n🌐 Dashboard URL:")
            print(f"   file://{dashboard_path.absolute()}")
            print(f"\n📁 Output files saved to:")
            print(f"   {self.output_dir.absolute()}")
            print(f"\n🚀 Open the dashboard in your browser to see interactive visualizations!")
            return True
        else:
            print("\n❌ Dashboard creation failed")
            return False

def main():
    """Main execution function."""
    print("Urban Simulator - Visualization Engine")
    print("=" * 50)
    
    print("\nThis will create an interactive dashboard showing:")
    print("  📈 Timeline plots of urban metrics over time")
    print("  🗺️  Spatial maps showing geographic distribution")
    print("  🔗 Correlation analysis between different metrics")
    print("  📊 Summary statistics and insights")
    print("  ⚡ EV Infrastructure impact comparison")
    
    response = input("\nCreate dashboard? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("Visualization cancelled.")
        return False
    
    # Run visualization
    visualizer = SimulationVisualizer()
    success = visualizer.run()
    
    if success:
        print("\n🎉 Dashboard created successfully!")
        print("\nNext you can:")
        print("1. Open the HTML dashboard in your browser")
        print("2. Run new simulations with different parameters")
        print("3. Modify the visualization code for custom charts")
    else:
        print("\n⚠️  Dashboard creation failed.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)