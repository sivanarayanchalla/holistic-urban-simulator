#!/usr/bin/env python3
"""
Create spatial grid (hexagonal) for urban simulation.
"""
import sys
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Polygon, shape
import json
import h3
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from database.db_config import db_config
from database.models import SpatialGrid
from geoalchemy2.shape import from_shape
from sqlalchemy.orm import Session
from sqlalchemy import text

class SpatialGridGenerator:
    """Generate hexagonal spatial grid for simulation."""
    
    def __init__(self):
        self.city_name = "Leipzig, Germany"
        self.grid_resolutions = [500, 1000]  # meters
        
    def get_city_boundary(self):
        """Get Leipzig boundary from database or file."""
        print("   Getting city boundary...")
        
        try:
            # Try to get boundary from land use data in database
            with db_config.get_session() as session:
                result = session.execute(
                    text("SELECT ST_Union(geometry) as boundary FROM land_use LIMIT 1")
                )
                boundary_wkt = result.scalar()
                
                if boundary_wkt:
                    from shapely import wkt
                    boundary = wkt.loads(boundary_wkt)
                    print(f"   ✅ Got boundary from database ({boundary.area:.2f} sq deg)")
                    return boundary
        except Exception as e:
            print(f"   ⚠️  Could not get boundary from DB: {e}")
        
        # Fallback: Use bounding box from file
        boundary_path = Path("data/raw/leipzig/leipzig_boundary.geojson")
        if boundary_path.exists():
            try:
                boundary_gdf = gpd.read_file(boundary_path)
                if not boundary_gdf.empty:
                    boundary = boundary_gdf.geometry.iloc[0]
                    print(f"   ✅ Got boundary from file ({boundary.area:.2f} sq deg)")
                    return boundary
            except Exception as e:
                print(f"   ⚠️  Could not read boundary file: {e}")
        
        # Final fallback: Use Leipzig bounding box
        from shapely.geometry import box
        boundary = box(12.30, 51.30, 12.50, 51.40)  # Leipzig bbox
        print(f"   ⚠️  Using default bounding box ({boundary.area:.2f} sq deg)")
        return boundary
    
    def create_hexagonal_grid(self, boundary_geometry, resolution=500):
        """Create H3 hexagonal grid covering the boundary."""
        print(f"   Creating H3 grid at resolution {resolution}m...")
        
        try:
            # Convert resolution to H3 level
            resolution_to_h3 = {
                100: 9,   # ~100m
                500: 7,   # ~500m
                1000: 6,  # ~1km
                2000: 5,  # ~2km
                5000: 4   # ~5km
            }
            
            h3_level = resolution_to_h3.get(resolution, 7)
            print(f"     H3 level: {h3_level} (approx {resolution}m)")
            
            # Convert boundary to GeoJSON dict
            boundary_dict = json.loads(gpd.GeoSeries([boundary_geometry]).to_json())
            geo_json = boundary_dict['features'][0]['geometry']
            
            # Get hexagons using the appropriate API for the installed H3 version
            hexagons = None
            
            # Try new API (H3 v4+)
            try:
                # Convert GeoJSON to H3Shape
                h3shape = h3.geo_to_h3shape(geo_json)
                # Get cells using polygon_to_cells (alias for h3shape_to_cells)
                hexagons = h3.polygon_to_cells(h3shape, h3_level)
                print(f"     Using H3 v4+ API (polygon_to_cells)")
            except (AttributeError, KeyError):
                # Fall back to old API (H3 v3)
                try:
                    hexagons = h3.polyfill(geo_json, h3_level, geo_json_conformant=True)
                    print(f"     Using H3 v3 API (polyfill)")
                except AttributeError as e:
                    print(f"     ❌ No compatible H3 API found: {e}")
                    return []
            
            if not hexagons:
                print(f"     ⚠️  No hexagons generated")
                return []
            
            print(f"     Generated {len(hexagons)} hexagons")
            
            # Convert hexagons to geometries
            grid_cells = []
            for hex_id in hexagons:
                try:
                    # Get hexagon boundary using appropriate API
                    hex_boundary = None
                    try:
                        # New API (H3 v4+)
                        boundary_tuples = h3.cell_to_boundary(hex_id)
                        # cell_to_boundary returns (lat, lng) tuples; convert to (lng, lat)
                        hex_boundary = [(lng, lat) for lat, lng in boundary_tuples]
                    except (AttributeError, KeyError):
                        # Old API (H3 v3)
                        hex_boundary = h3.h3_to_geo_boundary(hex_id, geo_json=True)
                    
                    # Ensure polygon is closed
                    if hex_boundary and hex_boundary[0] != hex_boundary[-1]:
                        hex_boundary.append(hex_boundary[0])
                    
                    polygon = Polygon(hex_boundary)
                    
                    grid_cells.append({
                        'grid_id': f"hex_{h3_level}_{hex_id}",
                        'geometry': polygon,
                        'h3_id': hex_id,
                        'resolution': resolution,
                        'grid_type': 'hexagon'
                    })
                    
                except Exception as e:
                    print(f"     ⚠️  Skipping hexagon {hex_id}: {e}")
                    continue
            
            return grid_cells
            
        except Exception as e:
            print(f"   ❌ Error creating hex grid: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def create_simple_test_grid(self, boundary_geometry):
        """Create a simple test grid for demonstration."""
        print("   Creating simple test grid...")
        
        from shapely.geometry import box
        minx, miny, maxx, maxy = boundary_geometry.bounds
        
        # Create a 3x3 grid for testing
        grid_cells = []
        rows = 3
        cols = 3
        
        cell_width = (maxx - minx) / cols
        cell_height = (maxy - miny) / rows
        
        for i in range(cols):
            for j in range(rows):
                cell_box = box(
                    minx + i * cell_width,
                    miny + j * cell_height,
                    minx + (i + 1) * cell_width,
                    miny + (j + 1) * cell_height
                )
                
                # Only include cells that intersect the boundary
                if boundary_geometry.intersects(cell_box):
                    grid_id = f"test_500_{i}_{j}"
                    grid_cells.append({
                        'grid_id': grid_id,
                        'geometry': cell_box,
                        'resolution': 500,
                        'grid_type': 'square'
                    })
        
        print(f"   Created {len(grid_cells)} test grid cells")
        return grid_cells
    
    def save_to_database(self, grid_cells):
        """Save grid cells to database."""
        if not grid_cells:
            print("   ⚠️  No grid cells to save")
            return 0
        
        print(f"   Saving {len(grid_cells)} grid cells to database...")
        
        try:
            with db_config.get_session() as session:
                # Clear existing grid data
                session.execute(text("TRUNCATE TABLE spatial_grid RESTART IDENTITY CASCADE;"))
                
                # Add new grid cells
                for cell in grid_cells:
                    grid = SpatialGrid(
                        grid_id=cell['grid_id'],
                        grid_type=cell['grid_type'],
                        resolution_meters=cell['resolution'],
                        geometry=from_shape(cell['geometry'], srid=4326)
                    )
                    session.add(grid)
                
                session.commit()
                print(f"   ✅ Saved {len(grid_cells)} grid cells")
                return len(grid_cells)
                
        except Exception as e:
            print(f"   ❌ Error saving grid: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def aggregate_ev_to_grid(self):
        """Aggregate EV infrastructure data to grid cells.
        
        Spatially joins EV charging stations to grid cells and calculates:
        - chargers_count: number of chargers in cell
        - ev_capacity_kw: total capacity in kW
        - charger_density_per_sqkm: chargers per square km
        - charger_types: distribution by EV type
        - avg_charger_capacity_kw: mean capacity per charger
        """
        print("\n4. Aggregating EV infrastructure to grid...")
        
        try:
            with db_config.get_session() as session:
                # Load grid cells
                print("   Loading grid cells...")
                grid_gdf = gpd.read_postgis(
                    "SELECT grid_id, geometry, ST_Area(geometry)/1000000.0 as area_sqkm FROM spatial_grid",
                    con=session.connection(),
                    geom_col='geometry'
                )
                
                if grid_gdf.empty:
                    print("   ⚠️  No grid cells found")
                    return {}
                
                # Load EV infrastructure
                print("   Loading EV infrastructure...")
                ev_gdf = gpd.read_postgis(
                    "SELECT id, ev_type, capacity_kw, geometry FROM ev_infrastructure",
                    con=session.connection(),
                    geom_col='geometry'
                )
                
                if ev_gdf.empty:
                    print("   ⚠️  No EV infrastructure data found")
                    return {}
                
                print(f"   Found {len(ev_gdf)} charging stations")
                
                # Spatial join: find which grid cell each charger belongs to
                ev_grid_join = gpd.sjoin(ev_gdf, grid_gdf[['grid_id', 'geometry', 'area_sqkm']], 
                                        how='left', predicate='within')
                
                # Aggregate by grid cell
                ev_metrics = {}
                
                for grid_id in grid_gdf['grid_id']:
                    cell_evs = ev_grid_join[ev_grid_join['grid_id'] == grid_id]
                    
                    if len(cell_evs) == 0:
                        # No chargers in this cell
                        ev_metrics[grid_id] = {
                            'chargers_count': 0,
                            'ev_capacity_kw': 0.0,
                            'charger_density_per_sqkm': 0.0,
                            'charger_types': {},
                            'avg_charger_capacity_kw': 0.0
                        }
                    else:
                        # Calculate metrics for this cell
                        chargers_count = len(cell_evs)
                        total_capacity = cell_evs['capacity_kw'].sum()
                        cell_area = grid_gdf[grid_gdf['grid_id'] == grid_id]['area_sqkm'].iloc[0]
                        charger_density = chargers_count / cell_area if cell_area > 0 else 0
                        avg_capacity = total_capacity / chargers_count if chargers_count > 0 else 0
                        
                        # Count by EV type
                        type_counts = cell_evs['ev_type'].value_counts().to_dict()
                        
                        ev_metrics[grid_id] = {
                            'chargers_count': int(chargers_count),
                            'ev_capacity_kw': float(total_capacity),
                            'charger_density_per_sqkm': float(charger_density),
                            'charger_types': type_counts,
                            'avg_charger_capacity_kw': float(avg_capacity)
                        }
                
                print(f"   ✅ Aggregated EV data for {len([m for m in ev_metrics.values() if m['chargers_count'] > 0])} grid cells")
                return ev_metrics
        
        except Exception as e:
            print(f"   ❌ Error aggregating EV data: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def run(self):
        """Run complete grid generation pipeline."""
        print("=" * 60)
        print("SPATIAL GRID GENERATOR")
        print("=" * 60)
        
        # 1. Get city boundary
        print("\n1. Getting Leipzig boundary...")
        boundary = self.get_city_boundary()
        
        # 2. Try to create H3 grid
        print("\n2. Creating spatial grid...")
        all_grid_cells = []
        
        for resolution in self.grid_resolutions:
            print(f"\n   For resolution {resolution}m:")
            
            try:
                grid_cells = self.create_hexagonal_grid(boundary, resolution)
                if grid_cells:
                    all_grid_cells.extend(grid_cells)
                else:
                    print(f"     ⚠️  No hex grid created for {resolution}m")
            except Exception as e:
                print(f"     ⚠️  H3 grid failed: {e}")
        
        # 3. If H3 failed, create simple test grid
        if not all_grid_cells:
            print("\n   ⚠️  H3 grid generation failed, creating test grid...")
            all_grid_cells = self.create_simple_test_grid(boundary)
        
        # 4. Save to database
        print(f"\n3. Saving grid to database...")
        saved_count = self.save_to_database(all_grid_cells)
        
        # 5. Aggregate EV infrastructure to grid
        ev_metrics = {}
        if saved_count > 0:
            ev_metrics = self.aggregate_ev_to_grid()
        
        # 6. Summary
        print("\n" + "=" * 60)
        if saved_count > 0:
            print(f"✅ GRID GENERATION COMPLETE!")
            print(f"   Created {saved_count} grid cells")
            
            # Show distribution by resolution
            resolutions = {}
            for cell in all_grid_cells:
                res = cell['resolution']
                resolutions[res] = resolutions.get(res, 0) + 1
            
            print(f"   Distribution:")
            for res, count in resolutions.items():
                print(f"      {res}m: {count} cells")
            
            # Show EV aggregation summary
            if ev_metrics:
                cells_with_chargers = len([m for m in ev_metrics.values() if m['chargers_count'] > 0])
                total_chargers = sum(m['chargers_count'] for m in ev_metrics.values())
                total_capacity = sum(m['ev_capacity_kw'] for m in ev_metrics.values())
                print(f"\n   EV Infrastructure Summary:")
                print(f"      Cells with chargers: {cells_with_chargers}/{saved_count}")
                print(f"      Total chargers: {total_chargers}")
                print(f"      Total capacity: {total_capacity:.0f} kW")
            
            return True
        else:
            print(f"❌ GRID GENERATION FAILED")
            return False

def main():
    """Main execution function."""
    print("Spatial Grid Generator for Urban Simulator")
    print("=" * 50)
    
    print("\nThis script will:")
    print("1. Get Leipzig boundary from existing data")
    print("2. Create hexagonal grid cells over the city")
    print("3. Save grid to database for simulation")
    
    response = input("\nContinue? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("Operation cancelled.")
        return False
    
    generator = SpatialGridGenerator()
    success = generator.run()
    
    if success:
        print("\n🎉 Spatial grid created successfully!")
        print("\nNext steps:")
        print("1. Run simulation: python src/core_engine/run_simulation.py")
        print("2. Visualize: python src/visualization/create_dashboard.py")
    else:
        print("\n⚠️  Grid generation failed.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)