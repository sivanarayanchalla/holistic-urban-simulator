#!/usr/bin/env python3
"""
Fix invalid spatial grid data and create proper hexagonal grid.
"""
import sys
from pathlib import Path
from shapely.geometry import Polygon, box
from geoalchemy2.shape import from_shape
from sqlalchemy import text

sys.path.append(str(Path(__file__).parent))

from src.database.db_config import db_config
from src.database.models import SpatialGrid

def clear_invalid_grids():
    """Clear all invalid grid data."""
    print("Clearing invalid grid data...")
    
    try:
        with db_config.get_session() as session:
            # Count before
            count_before = session.query(SpatialGrid).count()
            print(f"  Grids before: {count_before}")
            
            # Delete all grids using ORM
            session.query(SpatialGrid).delete()
            session.commit()
            
            # Count after
            count_after = session.query(SpatialGrid).count()
            print(f"  Grids after: {count_after}")
            
            return True
            
    except Exception as e:
        print(f"  ❌ Error clearing grids: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_hexagonal_grid():
    """Create a hexagonal grid using manual mathematical approach."""
    print("\nCreating hexagonal grid for Leipzig...")
    
    # Leipzig bounding box
    min_lon, min_lat = 12.35, 51.33
    max_lon, max_lat = 12.40, 51.36
    
    # Hexagon parameters (approximate 500m hexagons)
    # At Leipzig's latitude (~51°), 0.01° ≈ 700m, so 0.007° ≈ 500m
    hex_radius = 0.0035  # Radius in degrees for ~500m
    
    try:
        with db_config.get_session() as session:
            saved_count = 0
            row = 0
            
            # Calculate hexagon geometry
            hex_height = hex_radius * 2  # Height from top to bottom
            hex_width = hex_radius * 1.732  # Width (sqrt(3) * radius)
            vertical_spacing = hex_height * 0.75  # Hexagons overlap
            
            # Create hex grid
            current_lat = min_lat + hex_radius
            
            while current_lat + hex_radius <= max_lat:
                # Offset every other row for honeycomb pattern
                offset = hex_width / 2 if row % 2 == 1 else 0
                current_lon = min_lon + offset + hex_radius
                col = 0
                
                while current_lon + hex_radius <= max_lon:
                    # Create hexagon vertices
                    hex_points = []
                    for i in range(6):
                        angle = 2 * 3.14159 * i / 6  # 60 degree increments (2π/6)
                        # Calculate vertex positions
                        vertex_lon = current_lon + hex_radius * (1 if i == 0 or i == 3 else 0.5) 
                        if i == 2 or i == 3 or i == 4:
                            vertex_lon = current_lon - hex_radius * (1 if i == 3 else 0.5)
                        
                        vertex_lat = current_lat
                        if i == 1 or i == 2:
                            vertex_lat = current_lat + hex_radius * 0.866  # sin(60°) ≈ 0.866
                        elif i == 4 or i == 5:
                            vertex_lat = current_lat - hex_radius * 0.866
                        
                        hex_points.append((vertex_lon, vertex_lat))
                    
                    # Close the polygon
                    hex_points.append(hex_points[0])
                    
                    # Create polygon
                    polygon = Polygon(hex_points)
                    
                    # Create grid
                    grid = SpatialGrid(
                        grid_id=f"hex_{row}_{col}",
                        grid_type="hexagon",
                        resolution_meters=500,
                        geometry=from_shape(polygon, srid=4326)
                    )
                    session.add(grid)
                    saved_count += 1
                    
                    current_lon += hex_width
                    col += 1
                
                current_lat += vertical_spacing
                row += 1
            
            session.commit()
            print(f"  ✅ Created {saved_count} hexagons")
            return True
            
    except Exception as e:
        print(f"  ❌ Error creating hex grid: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_simple_square_grid():
    """Create a simple square grid for testing."""
    print("\nCreating simple square grid for testing...")
    
    # Leipzig bounding box
    min_lon, min_lat = 12.35, 51.33
    max_lon, max_lat = 12.40, 51.36
    
    # Grid parameters
    rows = 10
    cols = 10
    
    try:
        with db_config.get_session() as session:
            cell_count = 0
            
            for i in range(rows):
                for j in range(cols):
                    # Calculate cell bounds
                    cell_min_lon = min_lon + (max_lon - min_lon) * i / rows
                    cell_max_lon = min_lon + (max_lon - min_lon) * (i + 1) / rows
                    cell_min_lat = min_lat + (max_lat - min_lat) * j / cols
                    cell_max_lat = min_lat + (max_lat - min_lat) * (j + 1) / cols
                    
                    # Create square polygon
                    polygon = box(cell_min_lon, cell_min_lat, cell_max_lon, cell_max_lat)
                    
                    # Create grid
                    grid = SpatialGrid(
                        grid_id=f"square_{i}_{j}",
                        grid_type="square",
                        resolution_meters=500,
                        geometry=from_shape(polygon, srid=4326)
                    )
                    session.add(grid)
                    cell_count += 1
            
            session.commit()
        
        print(f"  ✅ Created {cell_count} square grid cells")
        return True
        
    except Exception as e:
        print(f"  ❌ Error creating square grid: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_grids():
    """Verify grid data is valid."""
    print("\nVerifying grid data...")
    
    try:
        with db_config.get_session() as session:
            # Count grids using ORM
            count = session.query(SpatialGrid).count()
            print(f"  Total grids: {count}")
            
            if count == 0:
                print("  ⚠️  No grid data found")
                return False
            
            # Check geometry validity using raw SQL (PostGIS function)
            invalid_count = session.execute(text("""
                SELECT COUNT(*) FROM spatial_grid 
                WHERE NOT ST_IsValid(geometry)
            """)).scalar()
            
            if invalid_count > 0:
                print(f"  ⚠️  Found {invalid_count} invalid geometries")
                return False
            
            # Get grid statistics
            hex_count = session.query(SpatialGrid).filter_by(grid_type="hexagon").count()
            square_count = session.query(SpatialGrid).filter_by(grid_type="square").count()
            
            print(f"  Grid statistics:")
            print(f"    - Hexagons: {hex_count}")
            print(f"    - Squares: {square_count}")
            
            # Sample some grids
            grids = session.query(SpatialGrid).limit(5).all()
            print(f"  Sample grids:")
            for grid in grids:
                print(f"    - {grid.grid_id}: {grid.grid_type}, {grid.resolution_meters}m")
            
            print(f"  ✅ All {count} grids are valid")
            return True
            
    except Exception as e:
        print(f"  ❌ Error verifying grids: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main execution."""
    print("=" * 60)
    print("FIX SPATIAL GRID DATA")
    print("=" * 60)
    
    print("\nThis script will:")
    print("1. Clear invalid grid data")
    print("2. Create proper hexagonal/square grid")
    print("3. Verify the grid data")
    
    response = input("\nContinue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Operation cancelled.")
        return False
    
    # Step 1: Clear invalid data
    if not clear_invalid_grids():
        return False
    
    # Step 2: Create new grid
    print("\nChoose grid type:")
    print("  1. Hexagonal grid (recommended for realistic simulations)")
    print("  2. Square grid (simpler, for testing)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        print("\nCreating hexagonal grid...")
        success = create_hexagonal_grid()
        if not success:
            print("\n⚠️  Failed to create hexagonal grid, falling back to square grid...")
            success = create_simple_square_grid()
    else:
        success = create_simple_square_grid()
    
    if not success:
        return False
    
    # Step 3: Verify
    success = verify_grids()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ GRID DATA FIXED SUCCESSFULLY!")
        print("=" * 60)
        print("\nYou can now run the simulation.")
        print("\nNext: python src/core_engine/run_simulation.py")
        print("\nNote: Your spatial grid is ready with valid geometries.")
        print("      The simulation will now be able to process spatial data correctly.")
    else:
        print("\n❌ Failed to fix grid data")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)