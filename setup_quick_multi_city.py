"""
Quick data setup for multi-city simulation.
Generates synthetic data for demonstration of multi-city framework.
"""

import os
import sys
import warnings
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
from shapely.geometry import Point
from dotenv import load_dotenv
import traceback

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

warnings.filterwarnings("ignore")
load_dotenv(project_root / ".env")

from src.database.db_config import DatabaseConfig

class CityDataGenerator:
    """Generate synthetic city data for multi-city simulation."""
    
    CITY_CONFIGS = {
        'leipzig': {'name': 'Leipzig, Germany', 'population': 620000, 'bbox': (12.30, 51.30, 12.50, 51.40)},
        'berlin': {'name': 'Berlin, Germany', 'population': 3645000, 'bbox': (13.20, 52.40, 13.60, 52.60)},
        'munich': {'name': 'Munich, Germany', 'population': 1484000, 'bbox': (11.40, 48.10, 11.70, 48.25)},
        'hamburg': {'name': 'Hamburg, Germany', 'population': 1961000, 'bbox': (9.85, 53.45, 10.20, 53.60)},
        'cologne': {'name': 'Cologne, Germany', 'population': 1086000, 'bbox': (6.85, 50.90, 7.10, 51.00)}
    }
    
    def __init__(self, city_key='leipzig'):
        """Initialize data generator for a city."""
        self.city_key = city_key
        config = self.CITY_CONFIGS[city_key]
        
        self.city_name = config['name']
        self.population = config['population']
        self.bbox = config['bbox']
        
        self.data_dir = project_root / "data" / "raw" / city_key
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[*] Data Generator Initialized")
        print(f"   City: {self.city_name}")
        print(f"   Population: {self.population:,}")
        print(f"   Bounding Box: {self.bbox}")
    
    def generate_synthetic_data(self):
        """Generate synthetic infrastructure data for simulation."""
        print(f"\n[*] Generating synthetic data for {self.city_name}...")
        
        north, south, east, west = self.bbox
        np.random.seed(hash(self.city_key) % 2**32)
        
        # Generate POIs proportional to population
        n_pois = max(100, int((self.population / 1000000) * 400))
        lons = np.random.uniform(west, east, n_pois)
        lats = np.random.uniform(south, north, n_pois)
        poi_types = np.random.choice(['school', 'hospital', 'shop', 'restaurant'], n_pois, p=[0.2, 0.15, 0.35, 0.3])
        
        points = [Point(lon, lat) for lon, lat in zip(lons, lats)]
        pois_gdf = gpd.GeoDataFrame({
            'geometry': points,
            'poi_type': poi_types,
            'city': self.city_key
        }, crs='EPSG:4326')
        
        print(f"   [OK] Generated {n_pois} POIs")
        
        # Generate EV chargers (1 per 5km²)
        area_km2 = ((east - west) * 111) * ((north - south) * 111)  # rough conversion
        n_chargers = max(50, int(area_km2 / 5))
        
        charger_lons = np.random.uniform(west, east, n_chargers)
        charger_lats = np.random.uniform(south, north, n_chargers)
        charger_points = [Point(lon, lat) for lon, lat in zip(charger_lons, charger_lats)]
        
        ev_gdf = gpd.GeoDataFrame({
            'geometry': charger_points,
            'city': self.city_key,
            'charger_type': 'fast',
            'capacity_kw': 50
        }, crs='EPSG:4326')
        
        print(f"   [OK] Generated {n_chargers} EV chargers")
        
        return pois_gdf, ev_gdf
    
    def save_data(self, pois_gdf, ev_gdf):
        """Save generated data to files."""
        try:
            # Save POIs
            poi_file = self.data_dir / "pois.geojson"
            pois_gdf.to_file(poi_file, driver='GeoJSON')
            print(f"   Saved POIs: {poi_file.name}")
            
            # Save EV chargers
            ev_file = self.data_dir / "ev_chargers.geojson"
            ev_gdf.to_file(ev_file, driver='GeoJSON')
            print(f"   Saved EV chargers: {ev_file.name}")
            
            print(f"[OK] {self.city_name} data saved")
            return True
            
        except Exception as e:
            print(f"[ERROR] Save failed: {e}")
            return False

def main():
    """Generate data for all German cities."""
    print(f"\n{'='*60}")
    print("MULTI-CITY DATA GENERATOR")
    print(f"{'='*60}\n")
    
    cities = ['leipzig', 'berlin', 'munich']
    
    for city in cities:
        try:
            print(f"\nProcessing {city.upper()}...")
            gen = CityDataGenerator(city)
            pois_gdf, ev_gdf = gen.generate_synthetic_data()
            gen.save_data(pois_gdf, ev_gdf)
            
        except Exception as e:
            print(f"[ERROR] {city}: {e}")
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("[OK] DATA GENERATION COMPLETE")
    print(f"{'='*60}\n")
    print("Next steps:")
    print("  1. Run multi-city simulations: python run_multi_city_simulation.py")
    print("  2. Generate comparisons: python analyze_multi_city.py")
    print("  3. View dashboards in: data/outputs/visualizations/")

if __name__ == '__main__':
    main()
