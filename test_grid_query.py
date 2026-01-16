# test_grid_query.py
#!/usr/bin/env python3
"""
Test script to check grid cells in database.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from database.db_config import db_config
from sqlalchemy import text

def test_grid_cells():
    print("Testing grid cells in database...")
    
    try:
        with db_config.get_session() as session:
            # First, let's see what columns are available
            result = session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'spatial_grid'
            """))
            
            print("\nColumns in spatial_grid table:")
            for row in result:
                print(f"  {row.column_name}: {row.data_type}")
            
            # Now let's see some sample data
            result = session.execute(text("""
                SELECT grid_id, grid_type, geometry
                FROM spatial_grid
                LIMIT 3
            """))
            
            print("\nSample grid cells:")
            for row in result:
                print(f"\n  Grid ID: {row.grid_id}")
                print(f"  Grid Type: {row.grid_type}")
                print(f"  Geometry type: {type(row.geometry)}")
                print(f"  Geometry repr: {repr(row.geometry)[:100]}...")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_grid_cells()