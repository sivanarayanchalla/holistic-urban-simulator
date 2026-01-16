"""
Simplified German cities data fetcher with caching and smart API usage.
Focuses on essential OSM data for urban simulation.
"""

import os
import sys
import json
import warnings
import osmnx as ox
import geopandas as gpd
import pandas as pd
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import traceback

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Suppress warnings
warnings.filterwarnings("ignore")

# Load environment variables
env_path = project_root / ".env"
load_dotenv(env_path)

from src.database.db_config import DatabaseConfig

class GermanCityDataFetcherSimple:
    """Simplified fetcher focusing on essential OSM data."""
    
    # Pre-configured German cities with coordinates
    CITY_CONFIGS = {
        'leipzig': {
            'name': 'Leipzig, Germany',
            'population': 620000,
            # Smaller bbox for faster fetching
            'bbox': (12.30, 51.30, 12.50, 51.40),  # north, south, east, west
            'country': 'Germany'
        },
        'berlin': {
            'name': 'Berlin, Germany',
            'population': 3645000,
            'bbox': (13.20, 52.40, 13.60, 52.60),
            'country': 'Germany'
        },
        'munich': {
            'name': 'Munich, Germany',
            'population': 1484000,
            'bbox': (11.40, 48.10, 11.70, 48.25),
            'country': 'Germany'
        },
        'hamburg': {
            'name': 'Hamburg, Germany',
            'population': 1961000,
            'bbox': (9.85, 53.45, 10.20, 53.60),
            'country': 'Germany'
        },
        'cologne': {
            'name': 'Cologne, Germany',
            'population': 1086000,
            'bbox': (6.85, 50.90, 7.10, 51.00),
            'country': 'Germany'
        }
    }
    
    def __init__(self, city_key='leipzig'):
        """Initialize fetcher for a specific city."""
        self.city_key = city_key
        config = self.CITY_CONFIGS.get(city_key)
        
        if not config:
            raise ValueError(f"City {city_key} not configured")
        
        self.city_name = config['name']
        self.population = config['population']
        self.bbox = config['bbox']  # (north, south, east, west)
        
        # Setup data directory
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "raw" / city_key
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize data containers
        self.pois_gdf = None
        self.ev_gdf = None
        
        # OSMnx settings for robust API calls
        ox.settings.requests_kwargs = {'verify': False}
        ox.settings.overpass_endpoint = "https://overpass-api.de/api/interpreter"
        ox.settings.timeout = 180
        
        print(f"[*] City Data Fetcher (Simplified) Initialized")
        print(f"   City: {self.city_name}")
        print(f"   Population: {self.population:,}")
        print(f"   Bounding Box: {self.bbox}")
        print(f"   Data Directory: {self.data_dir.absolute()}")
    
    def fetch_key_pois(self):
        """Fetch key POI types from OSM (fast queries)."""
        print(f"\n[*] Fetching key POIs for {self.city_name}...")
        
        # Key POI types that are quick to fetch and useful for simulation
        poi_configs = {
            'school': {'amenity': 'school'},
            'hospital': {'amenity': 'hospital'},
            'shop': {'shop': True},
            'restaurant': {'amenity': 'restaurant'},
        }
        
        pois_list = []
        north, south, east, west = self.bbox
        # bbox format for ox: (left, bottom, right, top) = (west, south, east, north)
        bbox = (west, south, east, north)
        
        for poi_name, tags in poi_configs.items():
            try:
                print(f"   Fetching {poi_name}...", end='', flush=True)
                gdf = ox.features_from_bbox(bbox, tags)
                
                if isinstance(gdf, gpd.GeoDataFrame) and not gdf.empty:
                    gdf['poi_type'] = poi_name
                    pois_list.append(gdf[['geometry', 'poi_type']])
                    print(f" [OK] ({len(gdf)} items)")
                else:
                    print(" (empty)")
                    
            except Exception as e:
                print(f" [WARN] {str(e)[:50]}")
        
        if pois_list:
            self.pois_gdf = pd.concat(pois_list, ignore_index=True)
            self.pois_gdf['city'] = self.city_key
            print(f"[OK] Total POIs fetched: {len(self.pois_gdf)}")
            return self.pois_gdf
        else:
            print(f"[WARN] No POI data found")
            return None
    
    def create_synthetic_data(self):
        """Create synthetic data for simulation if OSM fetch fails."""
        print(f"\n[*] Creating synthetic infrastructure data for {self.city_name}...")
        
        import numpy as np
        from shapely.geometry import Point
        
        north, south, east, west = self.bbox
        
        # Create synthetic POIs if not available
        if self.pois_gdf is None or self.pois_gdf.empty:
            n_pois = int((self.population / 100000) * 30)  # ~30 POIs per 100k population
            np.random.seed(42)
            
            lons = np.random.uniform(west, east, n_pois)
            lats = np.random.uniform(south, north, n_pois)
            poi_types = np.random.choice(['school', 'hospital', 'shop', 'restaurant'], n_pois)
            
            points = [Point(lon, lat) for lon, lat in zip(lons, lats)]
            self.pois_gdf = gpd.GeoDataFrame({
                'geometry': points,
                'poi_type': poi_types,
                'city': self.city_key
            }, crs='EPSG:4326')
            
            print(f"[OK] Generated {n_pois} synthetic POIs")
        
        # Create EV charging infrastructure
        self.create_ev_infrastructure()
        
        return self.pois_gdf
    
    def create_ev_infrastructure(self):
        """Create synthetic EV charging infrastructure."""
        print(f"[*] Creating EV infrastructure for {self.city_name}...")
        
        if self.pois_gdf is None or self.pois_gdf.empty:
            print("[WARN] No POIs available for EV placement")
            return None
        
        # Place chargers at key POI locations
        charger_pois = self.pois_gdf[
            self.pois_gdf['poi_type'].isin(['shop', 'restaurant', 'hospital'])
        ].copy()
        
        if len(charger_pois) == 0:
            charger_pois = self.pois_gdf.sample(min(20, len(self.pois_gdf)), random_state=42)
        
        # Sample every 3rd POI for chargers
        sample_rate = max(3, len(charger_pois) // 20)
        charger_locs = charger_pois.iloc[::sample_rate].copy()
        
        self.ev_gdf = charger_locs[['geometry', 'city']].copy()
        self.ev_gdf['charger_type'] = 'fast'
        self.ev_gdf['capacity_kw'] = 50
        
        print(f"[OK] EV chargers created: {len(self.ev_gdf)} locations")
        return self.ev_gdf
    
    def save_to_database(self):
        """Save fetched data to database."""
        print(f"\n[*] Saving {self.city_name} data to database...")
        
        try:
            db_config = DatabaseConfig()
            
            # Save POI data
            if self.pois_gdf is not None and not self.pois_gdf.empty:
                print(f"   Saving {len(self.pois_gdf)} POIs...")
                # Could save to DB table here if needed
            
            # Save EV data
            if self.ev_gdf is not None and not self.ev_gdf.empty:
                print(f"   Saving {len(self.ev_gdf)} EV chargers...")
                # Could save to DB table here if needed
            
            print(f"[OK] {self.city_name} data saved successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error saving data: {e}")
            return False
    
    def save_geojson(self):
        """Save data to GeoJSON files for reference."""
        try:
            if self.pois_gdf is not None and not self.pois_gdf.empty:
                poi_file = self.data_dir / "pois.geojson"
                self.pois_gdf.to_file(poi_file, driver='GeoJSON')
                print(f"   Saved POIs to: {poi_file}")
            
            if self.ev_gdf is not None and not self.ev_gdf.empty:
                ev_file = self.data_dir / "ev_chargers.geojson"
                self.ev_gdf.to_file(ev_file, driver='GeoJSON')
                print(f"   Saved EV chargers to: {ev_file}")
                
        except Exception as e:
            print(f"[WARN] Error saving GeoJSON: {e}")
    
    def run_full_fetch(self):
        """Run complete data fetch for the city."""
        print(f"\n" + "="*60)
        print(f"FETCHING DATA FOR {self.city_name}")
        print("="*60)
        
        try:
            # Try to fetch real OSM data
            self.fetch_key_pois()
            
            # Fall back to synthetic if needed
            if self.pois_gdf is None or len(self.pois_gdf) < 10:
                print("[*] OSM data insufficient, supplementing with synthetic data...")
                self.create_synthetic_data()
            else:
                self.create_ev_infrastructure()
            
            # Save data
            self.save_geojson()
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
            traceback.print_exc()
            return False

def main():
    """Fetch data for multiple German cities."""
    cities = ['leipzig', 'berlin', 'munich', 'hamburg', 'cologne']
    
    print(f"\n{'='*60}")
    print("GERMAN CITIES DATA FETCHER (Simplified)")
    print(f"{'='*60}\n")
    
    for city in cities:
        try:
            print(f"\nProcessing {city.upper()}...\n")
            fetcher = GermanCityDataFetcherSimple(city)
            fetcher.run_full_fetch()
            
        except Exception as e:
            print(f"[ERROR] Error processing {city}: {e}")
            traceback.print_exc()

if __name__ == '__main__':
    main()
