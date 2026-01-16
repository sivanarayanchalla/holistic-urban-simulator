#!/usr/bin/env python3
"""
Load existing Leipzig data files to database.
"""
import sys
from pathlib import Path
import geopandas as gpd
import pandas as pd
import json

sys.path.append(str(Path(__file__).parent))

from src.database.db_config import db_config
from geoalchemy2.shape import from_shape
from sqlalchemy.orm import Session
from sqlalchemy import text

print("=" * 60)
print("LOAD EXISTING LEIPZIG DATA TO DATABASE")
print("=" * 60)

def load_land_use():
    """Load land use data from existing file."""
    print("\n1. Loading land use data...")
    landuse_path = Path("data/raw/leipzig/leipzig_landuse.geojson")
    
    if not landuse_path.exists():
        print("   ❌ Land use file not found")
        return 0
    
    try:
        landuse_gdf = gpd.read_file(landuse_path)
        print(f"   Found {len(landuse_gdf)} land use features")
        
        with db_config.get_session() as session:
            from src.database.models import LandUse
            
            # Clear existing data
            session.execute(text("TRUNCATE TABLE land_use RESTART IDENTITY CASCADE;"))
            
            # Load first 500 features
            sample_size = min(500, len(landuse_gdf))
            print(f"   Loading {sample_size} features...")
            
            loaded = 0
            for idx, row in landuse_gdf.head(sample_size).iterrows():
                try:
                    landuse = LandUse(
                        source=str(row.get('source', 'OSM'))[:50],
                        category=str(row.get('category', 'unknown'))[:100],
                        geometry=from_shape(row.geometry, srid=4326),
                        area_sqkm=float(row.get('area_sqkm', 0)) if 'area_sqkm' in row and pd.notna(row['area_sqkm']) else 0.0,
                        properties={}
                    )
                    session.add(landuse)
                    loaded += 1
                    
                    if loaded % 100 == 0:
                        session.commit()
                        print(f"      ... {loaded}/{sample_size}")
                        
                except Exception as e:
                    print(f"      ⚠️  Skipping feature {idx}: {str(e)[:50]}")
                    continue
            
            session.commit()
            print(f"   ✅ Loaded {loaded} land use features")
            return loaded
            
    except Exception as e:
        print(f"   ❌ Error loading land use: {e}")
        return 0

def load_pois():
    """Load points of interest from existing file."""
    print("\n2. Loading points of interest...")
    pois_path = Path("data/raw/leipzig/leipzig_pois.geojson")
    
    if not pois_path.exists():
        print("   ⚠️  POIs file not found, skipping")
        return 0
    
    try:
        pois_gdf = gpd.read_file(pois_path)
        print(f"   Found {len(pois_gdf)} POIs")
        
        with db_config.get_session() as session:
            from src.database.models import PointsOfInterest
            
            # Clear existing data
            session.execute(text("TRUNCATE TABLE points_of_interest RESTART IDENTITY CASCADE;"))
            
            # Load first 200 POIs
            sample_size = min(200, len(pois_gdf))
            print(f"   Loading {sample_size} POIs...")
            
            loaded = 0
            for idx, row in pois_gdf.head(sample_size).iterrows():
                try:
                    # Handle name
                    name = row.get('name')
                    if pd.isna(name):
                        name = None
                    elif not isinstance(name, str):
                        name = str(name)
                    
                    poi = PointsOfInterest(
                        poi_type=str(row.get('poi_type', 'unknown'))[:100],
                        name=name[:255] if name else None,
                        geometry=from_shape(row.geometry, srid=4326),
                        source='OSM',
                        properties={}
                    )
                    session.add(poi)
                    loaded += 1
                    
                    if loaded % 50 == 0:
                        session.commit()
                        print(f"      ... {loaded}/{sample_size}")
                        
                except Exception as e:
                    print(f"      ⚠️  Skipping POI {idx}: {str(e)[:50]}")
                    continue
            
            session.commit()
            print(f"   ✅ Loaded {loaded} POIs")
            return loaded
            
    except Exception as e:
        print(f"   ❌ Error loading POIs: {e}")
        return 0

def verify_database():
    """Verify database contents - FIXED VERSION."""
    print("\n3. Verifying database contents...")
    
    try:
        with db_config.get_session() as session:
            # FIXED: Remove duplicate SELECT keyword
            landuse_count = session.execute(text("SELECT COUNT(*) FROM land_use")).scalar() or 0
            pois_count = session.execute(text("SELECT COUNT(*) FROM points_of_interest")).scalar() or 0
            transport_count = session.execute(text("SELECT COUNT(*) FROM transport_network")).scalar() or 0
            
            print(f"   📊 Database counts:")
            print(f"      Land use: {landuse_count} features")
            print(f"      POIs: {pois_count} points")
            print(f"      Transport: {transport_count} segments")
            
            total = landuse_count + pois_count + transport_count
            
            if total > 0:
                print(f"\n✅ SUCCESS: {total} data records loaded!")
                return True
            else:
                print(f"\n⚠️  No data loaded.")
                return False
                
    except Exception as e:
        print(f"   ❌ Error verifying: {e}")
        return False
                
    except Exception as e:
        print(f"   ❌ Error verifying: {e}")
        return False

def main():
    """Main execution."""
    print("\nThis script will load existing Leipzig data files to the database.")
    print("Make sure you have data files in data/raw/leipzig/")
    print("=" * 60)
    
    response = input("\nContinue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Operation cancelled.")
        return False
    
    # Load data
    load_land_use()
    load_pois()
    
    # Verify
    success = verify_database()
    
    if success:
        print("\n🎉 You can now proceed to create spatial grids!")
        print("\nNext step: python src/data_pipeline/create_spatial_grid.py")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)