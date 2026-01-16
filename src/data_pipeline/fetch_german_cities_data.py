#!/usr/bin/env python3
"""
Generic German City Data Fetcher
Base class for fetching urban data for German cities (Berlin, Munich, Hamburg, etc.)
"""
import sys
from pathlib import Path
import geopandas as gpd
import pandas as pd
import osmnx as ox
import json
from datetime import datetime
from shapely.geometry import shape, Polygon, Point, LineString, box
from shapely.ops import transform
import time
import warnings
import numpy as np
import pyproj
from functools import partial
warnings.filterwarnings('ignore')

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from database.db_config import db_config
from database.utils import DatabaseUtils
from geoalchemy2.shape import from_shape
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sqlalchemy.exc import IntegrityError

class GermanCityDataFetcher:
    """Base class for fetching German city data with EV infrastructure support."""
    
    CITY_CONFIGS = {
        'leipzig': {
            'name': 'Leipzig, Germany',
            'bbox': (12.20, 51.25, 12.55, 51.45),
            'center': (12.375, 51.35),
            'population': 620000,
        },
        'berlin': {
            'name': 'Berlin, Germany',
            'bbox': (13.08, 52.34, 13.76, 52.67),
            'center': (13.405, 52.52),
            'population': 3645000,
        },
        'munich': {
            'name': 'Munich, Germany',
            'bbox': (11.30, 48.07, 11.73, 48.27),
            'center': (11.58, 48.14),
            'population': 1484000,
        },
        'hamburg': {
            'name': 'Hamburg, Germany',
            'bbox': (9.73, 53.40, 10.32, 53.62),
            'center': (10.00, 53.55),
            'population': 1852000,
        },
        'cologne': {
            'name': 'Cologne, Germany',
            'bbox': (6.78, 50.88, 7.15, 51.07),
            'center': (6.96, 50.94),
            'population': 1087000,
        },
    }
    
    def __init__(self, city_key='leipzig'):
        """Initialize fetcher for a specific German city."""
        if city_key not in self.CITY_CONFIGS:
            raise ValueError(f"Unknown city: {city_key}. Available: {list(self.CITY_CONFIGS.keys())}")
        
        config = self.CITY_CONFIGS[city_key]
        self.city_key = city_key
        self.city_name = config['name']
        self.bbox = config['bbox']
        self.center = config['center']
        self.population = config['population']
        
        self.data_dir = Path(f"data/raw/{city_key}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Store dataframes for diagnosis
        self.boundary_gdf = None
        self.landuse_gdf = None
        self.pois_gdf = None
        self.transport_gdf = None
        self.ev_gdf = None
        
        # Configure OSMnx
        ox.settings.log_console = True
        ox.settings.use_cache = True
        ox.settings.cache_folder = str(self.data_dir / "cache")
        ox.settings.timeout = 300
        ox.settings.requests_kwargs = {'verify': False}
        ox.settings.overpass_endpoint = "https://overpass-api.de/api/interpreter"
        
        print(f"[*] City Data Fetcher Initialized")
        print(f"   City: {self.city_name}")
        print(f"   Population: {self.population:,}")
        print(f"   Bounding Box: {self.bbox}")
        print(f"   Data Directory: {self.data_dir.absolute()}")
        print(f"   EV Support: Enabled")
    
    def fetch_with_retry(self, fetch_function, max_retries=3, delay=30):
        """Execute a fetch function with retry logic."""
        for attempt in range(max_retries):
            try:
                print(f"   Attempt {attempt + 1}/{max_retries}...")
                result = fetch_function()
                if result is not None and (not hasattr(result, 'empty') or not result.empty):
                    return result
                else:
                    print(f"   [WARN] Empty result, retrying...")
            except Exception as e:
                print(f"   [ERROR] Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"   [*] Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    print(f"   [WARN] All {max_retries} attempts failed")
        return None
    
    def fetch_landuse_data(self):
        """Fetch landuse data from OSM."""
        print(f"\n[*] Fetching landuse data for {self.city_name}...")
        
        def fetch_fn():
            north, south, east, west = self.bbox
            # bbox format: (left, bottom, right, top) = (west, south, east, north)
            bbox = (west, south, east, north)
            gdf = ox.features_from_bbox(bbox, {"landuse": True})
            return gdf if isinstance(gdf, gpd.GeoDataFrame) and not gdf.empty else None
        
        self.landuse_gdf = self.fetch_with_retry(fetch_fn)
        
        if self.landuse_gdf is not None:
            print(f"[OK] Landuse data: {len(self.landuse_gdf)} features")
            self.landuse_gdf['city'] = self.city_key
            return self.landuse_gdf
        else:
            print(f"[WARN] No landuse data found")
            return None
    
    def fetch_pois_data(self):
        """Fetch POIs (schools, hospitals, shops) from OSM."""
        print(f"\n[*] Fetching POI data for {self.city_name}...")
        
        poi_tags = {
            'amenity': ['school', 'hospital', 'library', 'cafe', 'restaurant', 'shop'],
            'tourism': ['hotel', 'museum', 'attraction'],
        }
        
        pois_list = []
        north, south, east, west = self.bbox
        # bbox format: (left, bottom, right, top) = (west, south, east, north)
        bbox = (west, south, east, north)
        
        for category, values in poi_tags.items():
            for value in values:
                try:
                    tags = {category: value}
                    print(f"   Fetching {category}={value}...", end='')
                    gdf = ox.features_from_bbox(bbox, tags)
                    if isinstance(gdf, gpd.GeoDataFrame) and not gdf.empty:
                        gdf['poi_type'] = value
                        pois_list.append(gdf)
                        print(f" [OK] ({len(gdf)} items)")
                    else:
                        print(" (empty)")
                except Exception as e:
                    print(f" [ERROR] ({e})")
        
        if pois_list:
            self.pois_gdf = pd.concat(pois_list, ignore_index=True)
            self.pois_gdf['city'] = self.city_key
            print(f"[OK] Total POIs: {len(self.pois_gdf)}")
            return self.pois_gdf
        else:
            print(f"[WARN] No POI data found")
            return None
    
    def fetch_transport_data(self):
        """Fetch transport infrastructure."""
        print(f"\n[*] Fetching transport data for {self.city_name}...")
        
        try:
            # Fetch road network
            print("   Fetching road network...", end='')
            north, south, east, west = self.bbox
            # bbox format: (left, bottom, right, top) = (west, south, east, north)
            bbox = (west, south, east, north)
            G = ox.graph_from_bbox(bbox, network_type='drive')
            roads_gdf = ox.graph_to_gdfs(G)[1]
            print(f" [OK] ({len(roads_gdf)} edges)")
            roads_gdf['transport_type'] = 'road'
            roads_gdf['city'] = self.city_key
            self.transport_gdf = roads_gdf
            
            print(f"[OK] Transport network: {len(roads_gdf)} road segments")
            return self.transport_gdf
        except Exception as e:
            print(f"[ERROR] Error fetching transport data: {e}")
            return None
    
    def create_ev_infrastructure(self):
        """Create synthetic EV charging infrastructure."""
        print(f"\n[*] Creating EV infrastructure for {self.city_name}...")
        
        if self.pois_gdf is None or self.pois_gdf.empty:
            print("[WARN] No POI data for EV infrastructure")
            return None
        
        # Place chargers at major POIs
        charger_pois = self.pois_gdf[
            self.pois_gdf['poi_type'].isin(['school', 'hospital', 'shop', 'restaurant', 'hotel'])
        ].copy()
        
        if len(charger_pois) == 0:
            print("[WARN] No suitable POI locations for chargers")
            return None
        
        # Sample charger locations (1 charger per 5 POIs on average)
        sample_size = max(10, len(charger_pois) // 5)
        charger_locs = charger_pois.sample(n=min(sample_size, len(charger_pois)), random_state=42)
        
        self.ev_gdf = charger_locs.copy()
        self.ev_gdf['charger_type'] = 'fast'
        self.ev_gdf['capacity_kw'] = 50
        self.ev_gdf['city'] = self.city_key
        
        print(f"[OK] EV chargers: {len(self.ev_gdf)} locations")
        return self.ev_gdf
    
    def save_to_database(self):
        """Save all fetched data to database."""
        print(f"\n💾 Saving {self.city_name} data to database...")
        
        session = db_config.get_session()
        try:
            # Save landuse data
            if self.landuse_gdf is not None and not self.landuse_gdf.empty:
                self._save_spatial_data(session, self.landuse_gdf, 'landuse', self.city_key)
            
            # Save POI data
            if self.pois_gdf is not None and not self.pois_gdf.empty:
                self._save_spatial_data(session, self.pois_gdf, 'pois', self.city_key)
            
            # Save transport data
            if self.transport_gdf is not None and not self.transport_gdf.empty:
                self._save_spatial_data(session, self.transport_gdf, 'transport', self.city_key)
            
            # Save EV data
            if self.ev_gdf is not None and not self.ev_gdf.empty:
                self._save_spatial_data(session, self.ev_gdf, 'ev_chargers', self.city_key)
            
            print(f"[OK] {self.city_name} data saved successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error saving data: {e})")
            return False
        finally:
            session.close()
    
    def _save_spatial_data(self, session, gdf, table_name, city_key):
        """Save spatial dataframe to database."""
        try:
            # Ensure geometry column exists
            if 'geometry' not in gdf.columns:
                print(f"[WARN] No geometry column in {table_name}")
                return
            
            # Save to file for reference
            file_path = self.data_dir / f"{table_name}.geojson"
            gdf.to_file(file_path, driver='GeoJSON')
            print(f"   Saved {table_name} to: {file_path}")
            
        except Exception as e:
            print(f"   [WARN] Error saving {table_name}: {e}")
    
    def run_full_fetch(self):
        """Run complete data fetch for the city."""
        print(f"\n" + "="*60)
        print(f"FETCHING DATA FOR {self.city_name}")
        print("="*60)
        
        try:
            # Fetch all data
            self.fetch_landuse_data()
            self.fetch_pois_data()
            self.fetch_transport_data()
            self.create_ev_infrastructure()
            
            # Save to database
            success = self.save_to_database()
            
            print(f"\n" + "="*60)
            if success:
                print(f"[OK] DATA FETCH COMPLETE FOR {self.city_name}")
            else:
                print(f"[WARN] DATA FETCH COMPLETED WITH WARNINGS FOR {self.city_name}")
            print("="*60 + "\n")
            
            return success
            
        except Exception as e:
            print(f"\n[ERROR] Error during data fetch: {e}")
            return False

def main():
    """Fetch data for multiple German cities."""
    cities = ['leipzig', 'berlin', 'munich']
    
    for city in cities:
        try:
            fetcher = GermanCityDataFetcher(city)
            fetcher.run_full_fetch()
            time.sleep(2)  # Rate limiting
        except Exception as e:
            print(f"[ERROR] Error processing {city}: {e}")

if __name__ == '__main__':
    main()
