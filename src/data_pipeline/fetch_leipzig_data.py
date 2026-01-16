#!/usr/bin/env python3
"""
Enhanced Leipzig Data Fetcher with EV Infrastructure Support
Fixed data loading issues and integrated EV catalyst modeling foundation
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
from math import radians, cos, sin, asin, sqrt
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

class LeipzigDataFetcher:
    """Enhanced Leipzig urban data fetcher with EV infrastructure support."""
    
    def __init__(self):
        self.city_name = "Leipzig, Germany"
        self.data_dir = Path("data/raw/leipzig")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Leipzig bounding box (expanded for better coverage)
        self.bbox = (12.20, 51.25, 12.55, 51.45)  # Expanded area
        
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
        
        print(f"📍 Leipzig Data Fetcher Initialized")
        print(f"   City: {self.city_name}")
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
                    print(f"   ⚠️  Empty result, retrying...")
            except Exception as e:
                print(f"   ❌ Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"   ⏳ Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    print(f"   ⚠️  All {max_retries} attempts failed")
        return None
    
    def validate_and_fix_geometry(self, geom):
        """Ensure geometry is valid and has correct orientation."""
        if geom is None or geom.is_empty:
            return None
        
        # Fix invalid geometries
        if not geom.is_valid:
            try:
                geom = geom.buffer(0)
            except:
                return None
        
        # Ensure correct orientation for polygons
        if geom.geom_type == 'Polygon':
            try:
                if not geom.exterior.is_ccw:
                    # Reverse orientation
                    coords = list(geom.exterior.coords)
                    geom = Polygon(coords[::-1])
            except:
                pass
        
        return geom
    
    def calculate_geodesic_length(self, line):
        """Calculate accurate length of LineString in meters."""
        if line is None or line.is_empty:
            return 0.0
        
        if line.geom_type != 'LineString':
            return 0.0
        
        coords = list(line.coords)
        if len(coords) < 2:
            return 0.0
        
        total_length = 0.0
        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[i + 1]
            
            # Convert to radians
            lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
            
            # Haversine formula
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            total_length += 6371000 * c  # Earth radius in meters
        
        return total_length
    
    def fetch_city_boundary(self):
        """Fetch Leipzig city boundary from OSM with fallback."""
        print("\n📐 Fetching city boundary...")
        
        def _fetch_boundary():
            try:
                # Try to get city boundary
                city_gdf = ox.geocode_to_gdf(self.city_name)
                
                if city_gdf.empty:
                    print("   ⚠️  Could not fetch city boundary, using bounding box")
                    city_gdf = gpd.GeoDataFrame(
                        {'name': ['Leipzig'], 'source': ['bbox_fallback']},
                        geometry=[box(*self.bbox)],
                        crs="EPSG:4326"
                    )
                
                return city_gdf
                
            except Exception as e:
                print(f"   ⚠️  Boundary fetch error: {e}")
                # Fallback to bounding box
                city_gdf = gpd.GeoDataFrame(
                    {'name': ['Leipzig'], 'source': ['error_fallback']},
                    geometry=[box(*self.bbox)],
                    crs="EPSG:4326"
                )
                return city_gdf
        
        # Use retry logic
        self.boundary_gdf = self.fetch_with_retry(_fetch_boundary, max_retries=2, delay=10)
        
        if self.boundary_gdf is not None and not self.boundary_gdf.empty:
            # Save to file
            boundary_path = self.data_dir / "leipzig_boundary.geojson"
            self.boundary_gdf.to_file(boundary_path, driver="GeoJSON")
            
            # Calculate area in square kilometers
            self.boundary_gdf = self.boundary_gdf.to_crs(epsg=3857)  # Web Mercator for area
            area_sqkm = self.boundary_gdf.geometry.area.iloc[0] / 1_000_000
            self.boundary_gdf = self.boundary_gdf.to_crs(epsg=4326)  # Back to WGS84
            
            print(f"   ✅ Boundary saved: {boundary_path}")
            print(f"   📏 Area: {area_sqkm:.1f} km²")
            
            return self.boundary_gdf
        else:
            print("   ❌ Failed to fetch boundary")
            return None
    
    def fetch_enhanced_land_use(self):
        """Fetch enhanced land use data with more categories."""
        print("\n🏘️  Fetching enhanced land use data...")
        
        # Expanded land use categories
        landuse_tags = {
            'landuse': [
                'residential', 'commercial', 'industrial', 'retail', 
                'farmland', 'forest', 'meadow', 'recreation_ground',
                'cemetery', 'allotments', 'construction'
            ],
            'leisure': ['park', 'garden', 'playground', 'sports_centre'],
            'amenity': ['school', 'hospital', 'university', 'college'],
            'tourism': ['attraction', 'museum', 'zoo'],
            'building': True  # Include building footprints
        }
        
        def _fetch_land_use():
            try:
                print("   Downloading land use data (this may take a while)...")
                
                # Use features_from_polygon with custom polygon
                boundary_polygon = self.boundary_gdf.geometry.iloc[0] if self.boundary_gdf is not None else box(*self.bbox)
                
                # Fetch in smaller chunks if boundary is large
                gdf = ox.features_from_polygon(boundary_polygon, tags=landuse_tags)
                
                # Filter to polygons only
                polygon_mask = gdf.geometry.type.isin(['Polygon', 'MultiPolygon'])
                landuse_gdf = gdf[polygon_mask].copy()
                
                if landuse_gdf.empty:
                    print("   ⚠️  No polygon land use data found, creating sample data")
                    # Create sample land use
                    sample_geometries = [
                        box(12.37, 51.34, 12.38, 51.35),  # Residential
                        box(12.39, 51.34, 12.40, 51.35),  # Commercial
                        box(12.36, 51.33, 12.37, 51.34),  # Park
                    ]
                    
                    landuse_gdf = gpd.GeoDataFrame(
                        {
                            'category': ['residential', 'commercial', 'park'],
                            'source': ['sample'],
                            'properties': ['{}', '{}', '{}']
                        },
                        geometry=sample_geometries,
                        crs="EPSG:4326"
                    )
                else:
                    # Determine primary category
                    def get_category(row):
                        categories = ['landuse', 'leisure', 'amenity', 'tourism', 'building']
                        for cat in categories:
                            if cat in row and pd.notna(row[cat]):
                                return f"{cat}_{row[cat]}"
                        return 'unknown'
                    
                    landuse_gdf['category'] = landuse_gdf.apply(get_category, axis=1)
                    landuse_gdf['source'] = 'OSM'
                    
                    # Store properties as JSON string
                    def store_properties(row):
                        props = {}
                        for key, value in row.items():
                            if key not in ['geometry', 'category', 'source'] and pd.notna(value):
                                props[key] = value
                        return json.dumps(props, default=str)
                    
                    landuse_gdf['properties'] = landuse_gdf.apply(store_properties, axis=1)
                
                # Calculate area in square kilometers
                landuse_gdf_projected = landuse_gdf.to_crs(epsg=3857)
                landuse_gdf['area_sqkm'] = landuse_gdf_projected.geometry.area / 1_000_000
                landuse_gdf = landuse_gdf.to_crs(epsg=4326)
                
                return landuse_gdf
                
            except Exception as e:
                print(f"   ⚠️  Land use fetch error: {e}")
                # Create minimal sample data
                sample_geom = box(12.37, 51.34, 12.38, 51.35)
                landuse_gdf = gpd.GeoDataFrame(
                    {
                        'category': ['residential'],
                        'source': ['error_fallback'],
                        'properties': ['{}'],
                        'area_sqkm': [0.5]
                    },
                    geometry=[sample_geom],
                    crs="EPSG:4326"
                )
                return landuse_gdf
        
        # Use retry logic
        self.landuse_gdf = self.fetch_with_retry(_fetch_land_use, max_retries=2, delay=20)
        
        if self.landuse_gdf is not None:
            # Save to file
            landuse_path = self.data_dir / "leipzig_landuse.geojson"
            self.landuse_gdf.to_file(landuse_path, driver="GeoJSON")
            
            print(f"   ✅ Land use data saved: {landuse_path}")
            print(f"   📊 Total features: {len(self.landuse_gdf)}")
            
            # Show category distribution
            if 'category' in self.landuse_gdf.columns:
                category_counts = self.landuse_gdf['category'].value_counts()
                print(f"   📈 Top categories:")
                for category, count in category_counts.head(8).items():
                    print(f"      {category}: {count}")
            
            total_area = self.landuse_gdf['area_sqkm'].sum() if 'area_sqkm' in self.landuse_gdf.columns else 0
            print(f"   📏 Total mapped area: {total_area:.1f} km²")
            
            return self.landuse_gdf
        else:
            print("   ❌ Failed to fetch land use data")
            return None
    
    def fetch_enhanced_pois(self):
        """Fetch enhanced points of interest with more categories."""
        print("\n📍 Fetching enhanced points of interest...")
        
        # Expanded POI categories
        poi_tags = {
            'amenity': [
                'school', 'hospital', 'university', 'college', 'library',
                'restaurant', 'cafe', 'fast_food', 'bar', 'pub',
                'bank', 'atm', 'pharmacy', 'clinic', 'doctors',
                'police', 'fire_station', 'post_office', 'townhall',
                'charging_station', 'fuel'  # EV-related
            ],
            'shop': [
                'supermarket', 'bakery', 'butcher', 'convenience',
                'clothes', 'shoes', 'electronics', 'hardware',
                'florist', 'chemist', 'books', 'stationery'
            ],
            'tourism': ['hotel', 'hostel', 'museum', 'attraction'],
            'leisure': ['park', 'sports_centre', 'fitness_centre'],
            'office': ['company', 'coworking']
        }
        
        def _fetch_pois():
            try:
                print("   Downloading POIs...")
                
                boundary_polygon = self.boundary_gdf.geometry.iloc[0] if self.boundary_gdf is not None else box(*self.bbox)
                gdf = ox.features_from_polygon(boundary_polygon, tags=poi_tags)
                
                # Filter to points only
                point_mask = gdf.geometry.type == 'Point'
                pois_gdf = gdf[point_mask].copy()
                
                if pois_gdf.empty:
                    print("   ⚠️  No POI data found, creating sample data")
                    # Create sample POIs
                    sample_points = [
                        Point(12.373, 51.336),  # Center
                        Point(12.378, 51.339),  # East
                        Point(12.368, 51.339),  # West
                        Point(12.373, 51.345),  # North
                        Point(12.373, 51.330),  # South
                    ]
                    
                    pois_gdf = gpd.GeoDataFrame(
                        {
                            'poi_type': ['restaurant', 'school', 'shop', 'park', 'charging_station'],
                            'name': ['Sample Restaurant', 'Sample School', 'Sample Shop', 'Sample Park', 'Sample Charger'],
                            'source': ['sample']
                        },
                        geometry=sample_points,
                        crs="EPSG:4326"
                    )
                else:
                    # Determine POI type
                    def get_poi_type(row):
                        for tag in ['amenity', 'shop', 'tourism', 'leisure', 'office']:
                            if tag in row and pd.notna(row[tag]):
                                return row[tag]
                        return 'unknown'
                    
                    def get_poi_name(row):
                        if 'name' in row and pd.notna(row['name']):
                            return row['name']
                        if 'brand' in row and pd.notna(row['brand']):
                            return row['brand']
                        return None
                    
                    pois_gdf['poi_type'] = pois_gdf.apply(get_poi_type, axis=1)
                    pois_gdf['name'] = pois_gdf.apply(get_poi_name, axis=1)
                    pois_gdf['source'] = 'OSM'
                    
                    # Store properties
                    def store_properties(row):
                        props = {}
                        for key, value in row.items():
                            if key not in ['geometry', 'poi_type', 'name', 'source'] and pd.notna(value):
                                props[key] = value
                        return json.dumps(props, default=str)
                    
                    pois_gdf['properties'] = pois_gdf.apply(store_properties, axis=1)
                
                return pois_gdf
                
            except Exception as e:
                print(f"   ⚠️  POI fetch error: {e}")
                # Create minimal sample data
                sample_point = Point(12.373, 51.336)
                pois_gdf = gpd.GeoDataFrame(
                    {
                        'poi_type': ['restaurant'],
                        'name': ['Sample POI'],
                        'source': ['error_fallback'],
                        'properties': ['{}']
                    },
                    geometry=[sample_point],
                    crs="EPSG:4326"
                )
                return pois_gdf
        
        # Use retry logic
        self.pois_gdf = self.fetch_with_retry(_fetch_pois, max_retries=2, delay=15)
        
        if self.pois_gdf is not None:
            # Save to file
            pois_path = self.data_dir / "leipzig_pois.geojson"
            self.pois_gdf.to_file(pois_path, driver="GeoJSON")
            
            print(f"   ✅ POIs saved: {pois_path}")
            print(f"   📊 Total POIs: {len(self.pois_gdf)}")
            
            # Show type distribution
            if 'poi_type' in self.pois_gdf.columns:
                type_counts = self.pois_gdf['poi_type'].value_counts()
                print(f"   📈 Top POI types:")
                for poi_type, count in type_counts.head(6).items():
                    print(f"      {poi_type}: {count}")
            
            return self.pois_gdf
        else:
            print("   ❌ Failed to fetch POIs")
            return None
    
    def fetch_enhanced_transport(self):
        """Fetch enhanced transport network with multiple network types."""
        print("\n🛣️  Fetching enhanced transport network...")
        
        def _fetch_transport():
            try:
                print("   Downloading transport networks...")
                
                boundary_polygon = self.boundary_gdf.geometry.iloc[0] if self.boundary_gdf is not None else box(*self.bbox)
                
                # Fetch different network types
                transport_data = []
                
                # Road network
                print("     Fetching road network...")
                try:
                    G_road = ox.graph_from_polygon(boundary_polygon, network_type='drive', simplify=True)
                    nodes_road, edges_road = ox.graph_to_gdfs(G_road)
                    edges_road['network_type'] = 'road'
                    transport_data.append(edges_road)
                except Exception as e:
                    print(f"       ⚠️  Road network error: {e}")
                
                # Bike network
                print("     Fetching bike network...")
                try:
                    G_bike = ox.graph_from_polygon(boundary_polygon, network_type='bike', simplify=True)
                    nodes_bike, edges_bike = ox.graph_to_gdfs(G_bike)
                    edges_bike['network_type'] = 'bike'
                    transport_data.append(edges_bike)
                except Exception as e:
                    print(f"       ⚠️  Bike network error: {e}")
                
                # Walk network
                print("     Fetching walk network...")
                try:
                    G_walk = ox.graph_from_polygon(boundary_polygon, network_type='walk', simplify=True)
                    nodes_walk, edges_walk = ox.graph_to_gdfs(G_walk)
                    edges_walk['network_type'] = 'walk'
                    transport_data.append(edges_walk)
                except Exception as e:
                    print(f"       ⚠️  Walk network error: {e}")
                
                if not transport_data:
                    print("   ⚠️  No transport data found, creating sample data")
                    # Create sample transport data
                    lines = [
                        LineString([(12.37, 51.34), (12.38, 51.34)]),
                        LineString([(12.38, 51.34), (12.38, 51.35)]),
                        LineString([(12.37, 51.34), (12.37, 51.35)]),
                    ]
                    
                    transport_gdf = gpd.GeoDataFrame(
                        {
                            'network_type': ['road', 'road', 'bike'],
                            'length_meters': [1000, 1000, 500],
                            'source': ['sample']
                        },
                        geometry=lines,
                        crs="EPSG:4326"
                    )
                else:
                    # Combine all network types
                    transport_gdf = gpd.GeoDataFrame(pd.concat(transport_data, ignore_index=True))
                    transport_gdf['source'] = 'OSM'
                    
                    # Calculate length in meters
                    print("     Calculating lengths...")
                    transport_gdf['length_meters'] = transport_gdf.geometry.apply(self.calculate_geodesic_length)
                    
                    # Store properties
                    def store_properties(row):
                        props = {}
                        for key, value in row.items():
                            if key not in ['geometry', 'network_type', 'length_meters', 'source'] and pd.notna(value):
                                props[key] = value
                        return json.dumps(props, default=str)
                    
                    transport_gdf['properties'] = transport_gdf.apply(store_properties, axis=1)
                
                return transport_gdf
                
            except Exception as e:
                print(f"   ⚠️  Transport fetch error: {e}")
                # Create minimal transport data
                sample_line = LineString([(12.37, 51.34), (12.38, 51.34)])
                transport_gdf = gpd.GeoDataFrame(
                    {
                        'network_type': ['road'],
                        'length_meters': [1000],
                        'source': ['error_fallback'],
                        'properties': ['{}']
                    },
                    geometry=[sample_line],
                    crs="EPSG:4326"
                )
                return transport_gdf
        
        # Use retry logic
        self.transport_gdf = self.fetch_with_retry(_fetch_transport, max_retries=2, delay=15)
        
        if self.transport_gdf is not None:
            # Save to file
            transport_path = self.data_dir / "leipzig_transport.geojson"
            self.transport_gdf.to_file(transport_path, driver="GeoJSON")
            
            total_length_km = self.transport_gdf['length_meters'].sum() / 1000
            network_types = self.transport_gdf['network_type'].unique()
            
            print(f"   ✅ Transport network saved: {transport_path}")
            print(f"   📏 Total length: {total_length_km:.1f} km")
            print(f"   📊 Segments: {len(self.transport_gdf)}")
            print(f"   🔗 Network types: {', '.join(network_types)}")
            
            # Show breakdown by network type
            for net_type in network_types:
                type_length = self.transport_gdf[self.transport_gdf['network_type'] == net_type]['length_meters'].sum() / 1000
                print(f"      {net_type}: {type_length:.1f} km")
            
            return self.transport_gdf
        else:
            print("   ❌ Failed to fetch transport network")
            return None
    
    def fetch_ev_infrastructure(self):
        """Fetch EV charging infrastructure data."""
        print("\n⚡ Fetching EV infrastructure data...")
        
        # EV-specific tags
        ev_tags = {
            'amenity': ['charging_station', 'fuel'],
            'authentication': True,
            'capacity': True,
            'socket': True,
            'fee': True,
            'operator': True,
            'opening_hours': True,
            'parking': True
        }
        
        def _fetch_ev_data():
            try:
                print("   Downloading EV charging stations...")
                
                boundary_polygon = self.boundary_gdf.geometry.iloc[0] if self.boundary_gdf is not None else box(*self.bbox)
                gdf = ox.features_from_polygon(boundary_polygon, tags=ev_tags)
                
                # Filter to EV-related features
                ev_mask = (
                    (gdf['amenity'] == 'charging_station') |
                    (gdf.get('fuel:charging', 'no') == 'yes') |
                    (gdf.get('vehicle', '') == 'electric')
                )
                
                ev_gdf = gdf[ev_mask].copy()
                
                if ev_gdf.empty:
                    print("   ⚠️  No EV chargers found, creating sample data")
                    # Create realistic Leipzig EV charger locations
                    leipzig_chargers = [
                        {
                            'location': Point(12.373, 51.336),  # Hauptbahnhof
                            'type': 'fast_charger',
                            'capacity': 150,
                            'operator': 'Stadtwerke Leipzig'
                        },
                        {
                            'location': Point(12.378, 51.339),  # Augustusplatz
                            'type': 'fast_charger', 
                            'capacity': 150,
                            'operator': 'EnBW'
                        },
                        {
                            'location': Point(12.387, 51.328),  # Connewitz
                            'type': 'standard',
                            'capacity': 22,
                            'operator': 'Tesla'
                        },
                        {
                            'location': Point(12.341, 51.323),  # Grünau
                            'type': 'standard',
                            'capacity': 22,
                            'operator': 'ChargePoint'
                        },
                        {
                            'location': Point(12.391, 51.343),  # Gohlis
                            'type': 'fast_charger',
                            'capacity': 50,
                            'operator': 'Innogy'
                        }
                    ]
                    
                    ev_data = []
                    for charger in leipzig_chargers:
                        ev_data.append({
                            'ev_type': charger['type'],
                            'capacity_kw': charger['capacity'],
                            'operator': charger['operator'],
                            'authentication': 'app',
                            'fee': 'yes',
                            'source': 'sample'
                        })
                    
                    ev_gdf = gpd.GeoDataFrame(
                        ev_data,
                        geometry=[c['location'] for c in leipzig_chargers],
                        crs="EPSG:4326"
                    )
                else:
                    # Extract EV-specific properties
                    def get_ev_type(row):
                        capacity = None
                        if 'capacity' in row and pd.notna(row['capacity']):
                            try:
                                capacity = int(str(row['capacity']).split()[0])
                            except:
                                pass
                        
                        if capacity is not None and capacity >= 50:
                            return 'fast_charger'
                        return 'standard'
                    
                    def get_capacity(row):
                        if 'capacity' in row and pd.notna(row['capacity']):
                            try:
                                return int(str(row['capacity']).split()[0])
                            except:
                                pass
                        return 22  # Default standard charger
                    
                    def get_authentication(row):
                        auth_methods = []
                        if 'authentication' in row and pd.notna(row['authentication']):
                            auth_methods.append(str(row['authentication']))
                        if 'payment:app' in row and pd.notna(row['payment:app']):
                            auth_methods.append('app')
                        return ', '.join(auth_methods) if auth_methods else 'unknown'
                    
                    ev_gdf['ev_type'] = ev_gdf.apply(get_ev_type, axis=1)
                    ev_gdf['capacity_kw'] = ev_gdf.apply(get_capacity, axis=1)
                    ev_gdf['operator'] = ev_gdf.get('operator', 'unknown')
                    ev_gdf['authentication'] = ev_gdf.apply(get_authentication, axis=1)
                    ev_gdf['fee'] = ev_gdf.get('fee', 'unknown')
                    ev_gdf['source'] = 'OSM'
                    
                    # Store properties
                    def store_properties(row):
                        props = {}
                        for key, value in row.items():
                            if key not in ['geometry', 'ev_type', 'capacity_kw', 'operator', 
                                         'authentication', 'fee', 'source'] and pd.notna(value):
                                props[key] = value
                        return json.dumps(props, default=str)
                    
                    ev_gdf['properties'] = ev_gdf.apply(store_properties, axis=1)
                
                return ev_gdf
                
            except Exception as e:
                print(f"   ⚠️  EV data fetch error: {e}")
                # Create minimal sample data
                sample_point = Point(12.373, 51.336)
                ev_gdf = gpd.GeoDataFrame(
                    {
                        'ev_type': ['fast_charger'],
                        'capacity_kw': [150],
                        'operator': ['Stadtwerke Leipzig'],
                        'authentication': ['app'],
                        'fee': ['yes'],
                        'source': ['error_fallback'],
                        'properties': ['{}']
                    },
                    geometry=[sample_point],
                    crs="EPSG:4326"
                )
                return ev_gdf
        
        # Use retry logic
        self.ev_gdf = self.fetch_with_retry(_fetch_ev_data, max_retries=2, delay=15)
        
        if self.ev_gdf is not None:
            # Save to file
            ev_path = self.data_dir / "leipzig_ev_chargers.geojson"
            self.ev_gdf.to_file(ev_path, driver="GeoJSON")
            
            print(f"   ✅ EV chargers saved: {ev_path}")
            print(f"   📊 Total EV chargers: {len(self.ev_gdf)}")
            
            # Statistics
            if 'ev_type' in self.ev_gdf.columns:
                fast_chargers = (self.ev_gdf['ev_type'] == 'fast_charger').sum()
                total_capacity = self.ev_gdf['capacity_kw'].sum() if 'capacity_kw' in self.ev_gdf.columns else 0
                
                print(f"   ⚡ Fast chargers: {fast_chargers}")
                print(f"   🔌 Standard chargers: {len(self.ev_gdf) - fast_chargers}")
                print(f"   🔋 Total capacity: {total_capacity} kW")
            
            if 'operator' in self.ev_gdf.columns:
                operators = self.ev_gdf['operator'].value_counts()
                print(f"   🏢 Top operators:")
                for operator, count in operators.head(3).items():
                    print(f"      {operator}: {count}")
            
            return self.ev_gdf
        else:
            print("   ❌ Failed to fetch EV data")
            return None
    
    def create_ev_density_layer(self):
        """Create EV charger density heatmap layer."""
        if self.ev_gdf is None or len(self.ev_gdf) == 0:
            print("   ⚠️  No EV data available for density calculation")
            return None
        
        print("\n🗺️  Creating EV density layer...")
        
        try:
            # Create grid for density calculation
            bounds = self.boundary_gdf.total_bounds if self.boundary_gdf is not None else self.bbox
            grid_size = 500  # meters
            
            # Project to UTM for accurate grid creation
            utm_crs = 'EPSG:25833'  # UTM zone 33N for Leipzig
            boundary_proj = self.boundary_gdf.to_crs(utm_crs).geometry.iloc[0] if self.boundary_gdf is not None else None
            ev_proj = self.ev_gdf.to_crs(utm_crs)
            
            # Create grid cells
            xmin, ymin, xmax, ymax = ev_proj.total_bounds
            cols = int((xmax - xmin) / grid_size)
            rows = int((ymax - ymin) / grid_size)
            
            grid_cells = []
            for i in range(cols):
                for j in range(rows):
                    x_cell = xmin + i * grid_size
                    y_cell = ymin + j * grid_size
                    cell = box(x_cell, y_cell, x_cell + grid_size, y_cell + grid_size)
                    
                    # Only include cells within boundary
                    if boundary_proj is None or cell.intersects(boundary_proj):
                        # Count EV chargers in cell
                        ev_in_cell = ev_proj[ev_proj.intersects(cell)]
                        count = len(ev_in_cell)
                        
                        # Calculate weighted capacity
                        capacity = ev_in_cell['capacity_kw'].sum() if 'capacity_kw' in ev_in_cell.columns else 0
                        
                        grid_cells.append({
                            'geometry': cell,
                            'ev_count': count,
                            'ev_density': count / (grid_size * grid_size / 1_000_000),  # per km²
                            'capacity_density': capacity / (grid_size * grid_size / 1_000_000),  # kW per km²
                        })
            
            if grid_cells:
                density_gdf = gpd.GeoDataFrame(grid_cells, crs=utm_crs)
                density_gdf = density_gdf.to_crs(epsg=4326)  # Back to WGS84
                
                # Save density layer
                density_path = self.data_dir / "leipzig_ev_density.geojson"
                density_gdf.to_file(density_path, driver="GeoJSON")
                
                max_density = density_gdf['ev_density'].max()
                print(f"   ✅ EV density layer saved: {density_path}")
                print(f"   📊 Max density: {max_density:.2f} chargers/km²")
                print(f"   🔋 Total capacity density: {density_gdf['capacity_density'].sum():.0f} kW/km²")
                
                return density_gdf
            else:
                print("   ⚠️  Could not create density grid")
                return None
                
        except Exception as e:
            print(f"   ⚠️  Density calculation error: {e}")
            return None
    
    def create_synthetic_test_data(self):
        """Create comprehensive synthetic test data."""
        print("\n🔧 Creating synthetic test data...")
        
        # Create boundary
        boundary = Polygon([
            (12.35, 51.33), (12.45, 51.33),
            (12.45, 51.38), (12.35, 51.38),
            (12.35, 51.33)
        ])
        
        self.boundary_gdf = gpd.GeoDataFrame(
            {'name': ['Leipzig Test Area'], 'source': ['synthetic']},
            geometry=[boundary],
            crs="EPSG:4326"
        )
        
        # Create land use
        landuse_data = []
        categories = ['residential', 'commercial', 'industrial', 'park', 'mixed_use']
        
        for i, category in enumerate(categories):
            offset = i * 0.02
            poly = Polygon([
                (12.36 + offset, 51.34 + offset),
                (12.39 + offset, 51.34 + offset),
                (12.39 + offset, 51.36 + offset),
                (12.36 + offset, 51.36 + offset),
                (12.36 + offset, 51.34 + offset)
            ])
            landuse_data.append({
                'category': category,
                'source': 'synthetic',
                'properties': '{}',
                'area_sqkm': 0.25
            })
        
        self.landuse_gdf = gpd.GeoDataFrame(
            landuse_data,
            geometry=[Polygon([
                (12.36, 51.34), (12.39, 51.34), (12.39, 51.36), (12.36, 51.36), (12.36, 51.34)
            ]) for _ in range(len(categories))],
            crs="EPSG:4326"
        )
        
        # Create POIs
        poi_data = [
            {'poi_type': 'school', 'name': 'Test School', 'source': 'synthetic', 'properties': '{}'},
            {'poi_type': 'hospital', 'name': 'Test Hospital', 'source': 'synthetic', 'properties': '{}'},
            {'poi_type': 'restaurant', 'name': 'Test Restaurant', 'source': 'synthetic', 'properties': '{}'},
            {'poi_type': 'shop', 'name': 'Test Shop', 'source': 'synthetic', 'properties': '{}'},
            {'poi_type': 'park', 'name': 'Test Park', 'source': 'synthetic', 'properties': '{}'},
            {'poi_type': 'charging_station', 'name': 'Test EV Charger', 'source': 'synthetic', 'properties': '{}'},
            {'poi_type': 'bank', 'name': 'Test Bank', 'source': 'synthetic', 'properties': '{}'},
            {'poi_type': 'hotel', 'name': 'Test Hotel', 'source': 'synthetic', 'properties': '{}'},
        ]
        
        self.pois_gdf = gpd.GeoDataFrame(
            poi_data,
            geometry=[
                Point(12.365, 51.345),
                Point(12.375, 51.345),
                Point(12.365, 51.355),
                Point(12.375, 51.355),
                Point(12.370, 51.350),
                Point(12.380, 51.350),
                Point(12.370, 51.340),
                Point(12.380, 51.340),
            ],
            crs="EPSG:4326"
        )
        
        # Create transport network
        transport_data = [
            {'network_type': 'road', 'length_meters': 1200, 'source': 'synthetic', 'properties': '{}'},
            {'network_type': 'road', 'length_meters': 1200, 'source': 'synthetic', 'properties': '{}'},
            {'network_type': 'bike', 'length_meters': 800, 'source': 'synthetic', 'properties': '{}'},
            {'network_type': 'walk', 'length_meters': 600, 'source': 'synthetic', 'properties': '{}'},
            {'network_type': 'road', 'length_meters': 800, 'source': 'synthetic', 'properties': '{}'},
        ]
        
        self.transport_gdf = gpd.GeoDataFrame(
            transport_data,
            geometry=[
                LineString([(12.36, 51.34), (12.39, 51.34)]),
                LineString([(12.39, 51.34), (12.39, 51.36)]),
                LineString([(12.36, 51.34), (12.36, 51.36)]),
                LineString([(12.36, 51.36), (12.39, 51.36)]),
                LineString([(12.375, 51.34), (12.375, 51.36)]),
            ],
            crs="EPSG:4326"
        )
        
        # Create EV infrastructure
        ev_data = [
            {'ev_type': 'fast_charger', 'capacity_kw': 150, 'operator': 'Stadtwerke Leipzig', 
             'authentication': 'app', 'fee': 'yes', 'source': 'synthetic', 'properties': '{}'},
            {'ev_type': 'fast_charger', 'capacity_kw': 150, 'operator': 'EnBW', 
             'authentication': 'rfid_card', 'fee': 'yes', 'source': 'synthetic', 'properties': '{}'},
            {'ev_type': 'standard', 'capacity_kw': 22, 'operator': 'Tesla', 
             'authentication': 'app', 'fee': 'no', 'source': 'synthetic', 'properties': '{}'},
            {'ev_type': 'standard', 'capacity_kw': 22, 'operator': 'ChargePoint', 
             'authentication': 'rfid_card', 'fee': 'yes', 'source': 'synthetic', 'properties': '{}'},
        ]
        
        self.ev_gdf = gpd.GeoDataFrame(
            ev_data,
            geometry=[
                Point(12.370, 51.345),
                Point(12.380, 51.345),
                Point(12.370, 51.355),
                Point(12.380, 51.355),
            ],
            crs="EPSG:4326"
        )
        
        print("   ✅ Created comprehensive synthetic test data")
        print(f"   📊 Test data includes:")
        print(f"      - Boundary: 1 polygon")
        print(f"      - Land use: {len(self.landuse_gdf)} features")
        print(f"      - POIs: {len(self.pois_gdf)} points (including EV charger)")
        print(f"      - Transport: {len(self.transport_gdf)} segments")
        print(f"      - EV Infrastructure: {len(self.ev_gdf)} chargers")
        
        return self.boundary_gdf, self.landuse_gdf, self.pois_gdf, self.transport_gdf, self.ev_gdf
    
    def load_to_database_enhanced(self):
        """Enhanced database loading with proper error handling and validation."""
        print("\n💾 Loading data to database (Enhanced)...")
        
        try:
            with db_config.get_session() as session:
                # 1. Clear existing data safely
                print("   Clearing existing data...")
                try:
                    # Disable foreign key checks
                    session.execute(text("SET session_replication_role = 'replica';"))
                    
                    # Clear tables in correct order
                    session.execute(text("""
                        TRUNCATE TABLE 
                            points_of_interest, 
                            transport_network, 
                            land_use,
                            ev_infrastructure
                        CASCADE;
                    """))
                    
                    session.execute(text("SET session_replication_role = 'origin';"))
                    session.commit()
                    print("   ✅ Tables cleared")
                except Exception as e:
                    print(f"   ⚠️  Warning during clear: {e}")
                    session.rollback()
                
                # 2. Ensure EV infrastructure table exists
                print("   Checking EV infrastructure table...")
                try:
                    session.execute(text("""
                        CREATE TABLE IF NOT EXISTS ev_infrastructure (
                            id SERIAL PRIMARY KEY,
                            ev_type VARCHAR(50),
                            capacity_kw INTEGER,
                            operator VARCHAR(100),
                            authentication VARCHAR(100),
                            fee VARCHAR(10),
                            source VARCHAR(50),
                            geometry GEOMETRY(Point, 4326),
                            properties JSONB,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """))
                    session.commit()
                    print("   ✅ EV infrastructure table ready")
                except Exception as e:
                    print(f"   ⚠️  EV table check: {e}")
                
                total_loaded = {'land_use': 0, 'pois': 0, 'transport': 0, 'ev': 0}
                
                # 3. Load land use data
                if self.landuse_gdf is not None and not self.landuse_gdf.empty:
                    print(f"   Loading {len(self.landuse_gdf)} land use features...")
                    from database.models import LandUse
                    
                    batch = []
                    for idx, row in self.landuse_gdf.iterrows():
                        try:
                            # Validate geometry
                            valid_geom = self.validate_and_fix_geometry(row.geometry)
                            if valid_geom is None:
                                continue
                            
                            # Prepare properties
                            properties = {}
                            if 'properties' in row and row['properties']:
                                if isinstance(row['properties'], str) and row['properties'].strip():
                                    try:
                                        properties = json.loads(row['properties'])
                                    except:
                                        properties = {'raw': str(row['properties'])[:200]}
                            elif isinstance(row['properties'], dict):
                                properties = row['properties']
                            
                            # Ensure numeric fields are valid
                            area_sqkm = 0.0
                            if 'area_sqkm' in row:
                                try:
                                    val = row['area_sqkm']
                                    if pd.notna(val):
                                        area_sqkm = float(val)
                                except:
                                    area_sqkm = 0.0
                            
                            # Ensure category is string
                            category = str(row.get('category', 'unknown')).strip()[:100]
                            source = str(row.get('source', 'unknown')).strip()[:50]
                            
                            landuse = LandUse(
                                source=source,
                                category=category,
                                geometry=from_shape(valid_geom, srid=4326),
                                area_sqkm=area_sqkm,
                                properties=properties
                            )
                            batch.append(landuse)
                            
                            # Commit in batches
                            if len(batch) >= 25:
                                session.add_all(batch)
                                session.commit()
                                total_loaded['land_use'] += len(batch)
                                batch = []
                                if (idx + 1) % 100 == 0:
                                    print(f"      ... {idx + 1}/{len(self.landuse_gdf)}")
                        
                        except Exception as e:
                            print(f"      ⚠️  Skipping land use {idx}: {str(e)[:80]}")
                            continue
                    
                    # Commit remaining batch
                    if batch:
                        session.add_all(batch)
                        session.commit()
                        total_loaded['land_use'] += len(batch)
                    
                    print(f"   ✅ Land use loaded: {total_loaded['land_use']} features")
                
                # 4. Load POIs
                if self.pois_gdf is not None and not self.pois_gdf.empty:
                    print(f"   Loading {len(self.pois_gdf)} points of interest...")
                    from database.models import PointsOfInterest
                    
                    batch = []
                    for idx, row in self.pois_gdf.iterrows():
                        try:
                            # Validate geometry
                            valid_geom = self.validate_and_fix_geometry(row.geometry)
                            if valid_geom is None:
                                continue
                            
                            # Handle name field
                            name = row.get('name')
                            if pd.isna(name):
                                name = None
                            elif isinstance(name, (int, float)):
                                name = str(int(name)) if name == int(name) else str(name)
                            name = str(name)[:255] if name else None
                            
                            # Handle poi_type
                            poi_type = str(row.get('poi_type', 'unknown')).strip()[:100]
                            source = str(row.get('source', 'unknown')).strip()[:50]
                            
                            # Handle properties
                            properties = {}
                            if 'properties' in row and row['properties']:
                                if isinstance(row['properties'], str) and row['properties'].strip():
                                    try:
                                        properties = json.loads(row['properties'])
                                    except:
                                        properties = {'raw': str(row['properties'])[:200]}
                            elif isinstance(row['properties'], dict):
                                properties = row['properties']
                            
                            poi = PointsOfInterest(
                                poi_type=poi_type,
                                name=name,
                                geometry=from_shape(valid_geom, srid=4326),
                                source=source,
                                properties=properties
                            )
                            batch.append(poi)
                            
                            # Commit in batches
                            if len(batch) >= 25:
                                session.add_all(batch)
                                session.commit()
                                total_loaded['pois'] += len(batch)
                                batch = []
                                if (idx + 1) % 100 == 0:
                                    print(f"      ... {idx + 1}/{len(self.pois_gdf)}")
                        
                        except Exception as e:
                            print(f"      ⚠️  Skipping POI {idx}: {str(e)[:80]}")
                            continue
                    
                    if batch:
                        session.add_all(batch)
                        session.commit()
                        total_loaded['pois'] += len(batch)
                    
                    print(f"   ✅ POIs loaded: {total_loaded['pois']} points")
                
                # 5. Load transport network
                if self.transport_gdf is not None and not self.transport_gdf.empty:
                    print(f"   Loading {len(self.transport_gdf)} transport segments...")
                    from database.models import TransportNetwork
                    
                    batch = []
                    for idx, row in self.transport_gdf.iterrows():
                        try:
                            # Validate geometry
                            valid_geom = self.validate_and_fix_geometry(row.geometry)
                            if valid_geom is None:
                                continue
                            
                            # Calculate length
                            length_meters = 0.0
                            if 'length_meters' in row:
                                try:
                                    val = row['length_meters']
                                    if pd.notna(val):
                                        length_meters = float(val)
                                except:
                                    length_meters = 0.0
                            
                            # If length not provided or invalid, calculate it
                            if length_meters <= 0:
                                length_meters = self.calculate_geodesic_length(valid_geom)
                            
                            # Handle properties
                            properties = {}
                            if 'properties' in row and row['properties']:
                                if isinstance(row['properties'], str) and row['properties'].strip():
                                    try:
                                        properties = json.loads(row['properties'])
                                    except:
                                        properties = {'raw': str(row['properties'])[:200]}
                            elif isinstance(row['properties'], dict):
                                properties = row['properties']
                            
                            network_type = str(row.get('network_type', 'road')).strip()[:50]
                            source = str(row.get('source', 'unknown')).strip()[:50]
                            
                            transport = TransportNetwork(
                                network_type=network_type,
                                geometry=from_shape(valid_geom, srid=4326),
                                length_meters=length_meters,
                                properties=properties
                            )
                            batch.append(transport)
                            
                            # Commit in batches
                            if len(batch) >= 25:
                                session.add_all(batch)
                                session.commit()
                                total_loaded['transport'] += len(batch)
                                batch = []
                                if (idx + 1) % 100 == 0:
                                    print(f"      ... {idx + 1}/{len(self.transport_gdf)}")
                        
                        except Exception as e:
                            print(f"      ⚠️  Skipping transport {idx}: {str(e)[:80]}")
                            continue
                    
                    if batch:
                        session.add_all(batch)
                        session.commit()
                        total_loaded['transport'] += len(batch)
                    
                    print(f"   ✅ Transport loaded: {total_loaded['transport']} segments")
                
                # 6. Load EV infrastructure
                if self.ev_gdf is not None and not self.ev_gdf.empty:
                    print(f"   Loading {len(self.ev_gdf)} EV chargers...")
                    from database.models import EVInfrastructure
                    
                    batch = []
                    for idx, row in self.ev_gdf.iterrows():
                        try:
                            # Validate geometry
                            valid_geom = self.validate_and_fix_geometry(row.geometry)
                            if valid_geom is None:
                                continue
                            
                            # Extract EV-specific fields
                            ev_type = str(row.get('ev_type', 'unknown')).strip()[:50]
                            
                            capacity_kw = 0
                            if 'capacity_kw' in row:
                                try:
                                    val = row['capacity_kw']
                                    if pd.notna(val):
                                        capacity_kw = int(float(val))
                                except:
                                    capacity_kw = 22  # Default
                            
                            operator = str(row.get('operator', 'unknown')).strip()[:100]
                            authentication = str(row.get('authentication', 'unknown')).strip()[:100]
                            fee = str(row.get('fee', 'unknown')).strip()[:10]
                            source = str(row.get('source', 'unknown')).strip()[:50]
                            
                            # Handle properties
                            properties = {}
                            if 'properties' in row and row['properties']:
                                if isinstance(row['properties'], str) and row['properties'].strip():
                                    try:
                                        properties = json.loads(row['properties'])
                                    except:
                                        properties = {'raw': str(row['properties'])[:200]}
                            elif isinstance(row['properties'], dict):
                                properties = row['properties']
                            
                            # Create EV infrastructure record using ORM model
                            ev_record = EVInfrastructure(
                                ev_type=ev_type,
                                capacity_kw=capacity_kw,
                                operator=operator,
                                authentication=authentication,
                                fee=fee,
                                source=source,
                                geometry=from_shape(valid_geom, srid=4326),
                                properties=properties
                            )
                            batch.append(ev_record)
                            
                            # Commit in batches
                            if len(batch) >= 25:
                                session.add_all(batch)
                                session.commit()
                                total_loaded['ev'] += len(batch)
                                batch = []
                                if (idx + 1) % 100 == 0:
                                    print(f"      ... {idx + 1}/{len(self.ev_gdf)}")
                        
                        except Exception as e:
                            print(f"      ⚠️  Skipping EV charger {idx}: {str(e)[:80]}")
                            continue
                    
                    # Commit remaining batch
                    if batch:
                        session.add_all(batch)
                        session.commit()
                        total_loaded['ev'] += len(batch)
                    
                    print(f"   ✅ EV infrastructure loaded: {total_loaded['ev']} chargers")
                
                # 7. Verify loaded data
                print("\n   Verifying loaded data...")
                try:
                    landuse_count = session.execute(text("SELECT COUNT(*) FROM land_use")).scalar() or 0
                    pois_count = session.execute(text("SELECT COUNT(*) FROM points_of_interest")).scalar() or 0
                    transport_count = session.execute(text("SELECT COUNT(*) FROM transport_network")).scalar() or 0
                    ev_count = session.execute(text("SELECT COUNT(*) FROM ev_infrastructure")).scalar() or 0
                    
                    print(f"   📊 Database verification:")
                    print(f"      Land use: {landuse_count} features")
                    print(f"      POIs: {pois_count} points")
                    print(f"      Transport: {transport_count} segments")
                    print(f"      EV Infrastructure: {ev_count} chargers")
                    
                    # Check for invalid geometries
                    invalid_counts = session.execute(text("""
                        SELECT 
                            (SELECT COUNT(*) FROM land_use WHERE NOT ST_IsValid(geometry)) as land_use_invalid,
                            (SELECT COUNT(*) FROM points_of_interest WHERE NOT ST_IsValid(geometry)) as pois_invalid,
                            (SELECT COUNT(*) FROM transport_network WHERE NOT ST_IsValid(geometry)) as transport_invalid,
                            (SELECT COUNT(*) FROM ev_infrastructure WHERE NOT ST_IsValid(geometry)) as ev_invalid
                    """)).fetchone()
                    
                    if any(invalid_counts):
                        print(f"   ⚠️  Invalid geometries found:")
                        if invalid_counts[0] > 0:
                            print(f"      Land use: {invalid_counts[0]}")
                        if invalid_counts[1] > 0:
                            print(f"      POIs: {invalid_counts[1]}")
                        if invalid_counts[2] > 0:
                            print(f"      Transport: {invalid_counts[2]}")
                        if invalid_counts[3] > 0:
                            print(f"      EV Infrastructure: {invalid_counts[3]}")
                    
                    # Spatial index creation
                    print("   🔧 Creating spatial indexes...")
                    session.execute(text("CREATE INDEX IF NOT EXISTS idx_land_use_geom ON land_use USING GIST(geometry);"))
                    session.execute(text("CREATE INDEX IF NOT EXISTS idx_pois_geom ON points_of_interest USING GIST(geometry);"))
                    session.execute(text("CREATE INDEX IF NOT EXISTS idx_transport_geom ON transport_network USING GIST(geometry);"))
                    session.execute(text("CREATE INDEX IF NOT EXISTS idx_ev_geom ON ev_infrastructure USING GIST(geometry);"))
                    session.commit()
                    print("   ✅ Spatial indexes created")
                    
                    return True
                    
                except Exception as e:
                    print(f"   ⚠️  Verification error: {e}")
                    return True  # Data loaded, verification failed
        
        except Exception as e:
            print(f"   ❌ Database loading error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def diagnose_data_issues(self):
        """Diagnose data quality issues."""
        print("\n🔍 Data Quality Diagnosis")
        print("=" * 50)
        
        issues_found = False
        
        # Check each dataset
        datasets = [
            ("Land Use", self.landuse_gdf),
            ("POIs", self.pois_gdf),
            ("Transport", self.transport_gdf),
            ("EV Infrastructure", self.ev_gdf)
        ]
        
        for name, gdf in datasets:
            if gdf is not None and not gdf.empty:
                print(f"\n📊 {name}:")
                print(f"   Total features: {len(gdf)}")
                
                # Check for null values
                null_counts = gdf.isnull().sum()
                for col, count in null_counts.items():
                    if count > 0 and col not in ['properties']:
                        print(f"   ⚠️  {col}: {count} null values ({count/len(gdf)*100:.1f}%)")
                        issues_found = True
                
                # Check geometry validity
                valid_count = gdf.geometry.is_valid.sum()
                if valid_count < len(gdf):
                    print(f"   ⚠️  {len(gdf) - valid_count} invalid geometries")
                    issues_found = True
                
                # Check area/length for reasonable values
                if name == "Land Use" and 'area_sqkm' in gdf.columns:
                    max_area = gdf['area_sqkm'].max()
                    min_area = gdf['area_sqkm'].min()
                    if max_area > 100:  # Unreasonably large
                        print(f"   ⚠️  Suspiciously large area: {max_area:.1f} km²")
                        issues_found = True
                
                if name == "Transport" and 'length_meters' in gdf.columns:
                    max_len = gdf['length_meters'].max()
                    if max_len > 10000:  # 10km segment
                        print(f"   ⚠️  Suspiciously long segment: {max_len:.0f} m")
                        issues_found = True
            
            elif gdf is None:
                print(f"\n📊 {name}: Not loaded")
                issues_found = True
            else:
                print(f"\n📊 {name}: Empty")
                issues_found = True
        
        if not issues_found:
            print("\n✅ No major issues detected")
        
        return not issues_found
    
    def generate_data_report(self):
        """Generate a comprehensive data report."""
        print("\n📈 Data Collection Report")
        print("=" * 60)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'city': self.city_name,
            'data_sources': {},
            'statistics': {},
            'quality_metrics': {}
        }
        
        # Collect statistics for each dataset
        if self.landuse_gdf is not None and not self.landuse_gdf.empty:
            report['data_sources']['land_use'] = self.landuse_gdf['source'].value_counts().to_dict()
            report['statistics']['land_use'] = {
                'total_features': len(self.landuse_gdf),
                'categories': self.landuse_gdf['category'].value_counts().head(10).to_dict(),
                'total_area_km2': self.landuse_gdf['area_sqkm'].sum() if 'area_sqkm' in self.landuse_gdf.columns else 0
            }
        
        if self.pois_gdf is not None and not self.pois_gdf.empty:
            report['data_sources']['pois'] = self.pois_gdf['source'].value_counts().to_dict()
            report['statistics']['pois'] = {
                'total_points': len(self.pois_gdf),
                'top_types': self.pois_gdf['poi_type'].value_counts().head(10).to_dict()
            }
        
        if self.transport_gdf is not None and not self.transport_gdf.empty:
            report['data_sources']['transport'] = self.transport_gdf['source'].value_counts().to_dict()
            report['statistics']['transport'] = {
                'total_segments': len(self.transport_gdf),
                'network_types': self.transport_gdf['network_type'].value_counts().to_dict(),
                'total_length_km': self.transport_gdf['length_meters'].sum() / 1000 if 'length_meters' in self.transport_gdf.columns else 0
            }
        
        if self.ev_gdf is not None and not self.ev_gdf.empty:
            report['data_sources']['ev_infrastructure'] = self.ev_gdf['source'].value_counts().to_dict()
            report['statistics']['ev_infrastructure'] = {
                'total_chargers': len(self.ev_gdf),
                'charger_types': self.ev_gdf['ev_type'].value_counts().to_dict(),
                'total_capacity_kw': self.ev_gdf['capacity_kw'].sum() if 'capacity_kw' in self.ev_gdf.columns else 0,
                'top_operators': self.ev_gdf['operator'].value_counts().head(5).to_dict()
            }
        
        # Save report
        report_path = self.data_dir / "data_collection_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"   ✅ Report saved: {report_path}")
        
        # Print summary
        print(f"\n📋 Summary:")
        for data_type, stats in report['statistics'].items():
            print(f"\n   {data_type.replace('_', ' ').title()}:")
            for key, value in stats.items():
                if key == 'categories' or key == 'top_types' or key == 'network_types' or key == 'charger_types':
                    continue
                print(f"      {key.replace('_', ' ').title()}: {value}")
        
        return report
    
    def run_enhanced_pipeline(self, use_real_data=True):
        """Run enhanced data pipeline with EV integration."""
        print("=" * 70)
        print("🚀 ENHANCED LEIPZIG DATA PIPELINE WITH EV SUPPORT")
        print("=" * 70)
        
        start_time = time.time()
        
        if use_real_data:
            print("\n🌐 ATTEMPTING TO FETCH REAL DATA FROM OPENSTREETMAP")
            print("   This will download Leipzig's urban data including EV infrastructure")
            print("   Note: This may take 5-15 minutes depending on server load\n")
            
            # Fetch all data
            boundary = self.fetch_city_boundary()
            landuse = self.fetch_enhanced_land_use()
            pois = self.fetch_enhanced_pois()
            transport = self.fetch_enhanced_transport()
            ev_data = self.fetch_ev_infrastructure()
            
            # Check if we got reasonable data
            data_counts = {
                'Land Use': len(landuse) if landuse is not None else 0,
                'POIs': len(pois) if pois is not None else 0,
                'Transport': len(transport) if transport is not None else 0,
                'EV': len(ev_data) if ev_data is not None else 0
            }
            
            # If we got very little data, fall back to synthetic
            if sum(data_counts.values()) < 50:
                print(f"\n⚠️  Insufficient real data fetched (total: {sum(data_counts.values())} features)")
                print("   Falling back to synthetic test data...")
                self.create_synthetic_test_data()
        else:
            print("\n🛠️  USING SYNTHETIC TEST DATA")
            print("   Creating comprehensive test dataset for development...")
            self.create_synthetic_test_data()
        
        # Create EV density layer
        density_layer = self.create_ev_density_layer()
        
        # Diagnose data issues
        self.diagnose_data_issues()
        
        # Load to database
        print("\n" + "=" * 50)
        print("DATABASE LOADING")
        print("=" * 50)
        
        success = self.load_to_database_enhanced()
        
        # Generate report
        print("\n" + "=" * 50)
        print("REPORT GENERATION")
        print("=" * 50)
        
        report = self.generate_data_report()
        
        # Calculate elapsed time
        elapsed = time.time() - start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        
        print("\n" + "=" * 70)
        if success:
            print(f"✅ PIPELINE COMPLETED SUCCESSFULLY!")
            print(f"   ⏱️  Total time: {minutes}m {seconds}s")
            print(f"   💾 Data directory: {self.data_dir.absolute()}")
            print(f"   🗃️  Files saved:")
            for file in self.data_dir.glob("*.geojson"):
                size_kb = file.stat().st_size / 1024
                print(f"      - {file.name}: {size_kb:.1f} KB")
            
            print(f"\n🎯 NEXT STEPS FOR EV CATALYST MODELING:")
            print(f"   1. Create spatial grid: python src/data_pipeline/create_spatial_grid.py")
            print(f"   2. Run simulation with EV module: python src/core_engine/run_simulation.py --ev")
            print(f"   3. Analyze EV impact: python src/analysis/ev_catalyst_analysis.py")
            print(f"   4. Visualize results: python src/visualization/ev_dashboard.py")
            
        else:
            print(f"❌ PIPELINE FAILED")
            print(f"   ⏱️  Time: {minutes}m {seconds}s")
            print(f"\n🔧 TROUBLESHOOTING:")
            print(f"   - Check database connection in database/db_config.py")
            print(f"   - Verify PostgreSQL/PostGIS is running")
            print(f"   - Check available disk space")
            print(f"   - Try with synthetic data first: python fetch_leipzig_data.py --test")
        
        print("=" * 70)
        return success

def main():
    """Main execution function with command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Leipzig Urban Data Fetcher with EV Support')
    parser.add_argument('--test', action='store_true', help='Use synthetic test data')
    parser.add_argument('--real', action='store_true', help='Force real OSM data (may fail)')
    parser.add_argument('--diagnose', action='store_true', help='Run data diagnosis only')
    parser.add_argument('--report', action='store_true', help='Generate data report only')
    parser.add_argument('--ev-only', action='store_true', help='Fetch only EV infrastructure data')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔌 LEIPZIG URBAN DATA FETCHER WITH EV CATALYST SUPPORT")
    print("=" * 60)
    
    # Create data fetcher
    fetcher = LeipzigDataFetcher()
    
    # Determine mode
    if args.ev_only:
        print("\n⚡ Fetching EV infrastructure data only...")
        ev_data = fetcher.fetch_ev_infrastructure()
        if ev_data is not None:
            print(f"✅ EV data fetched: {len(ev_data)} chargers")
        return
    
    if args.diagnose:
        print("\n🔍 Running data diagnosis...")
        fetcher.create_synthetic_test_data()
        fetcher.diagnose_data_issues()
        return
    
    if args.report:
        print("\n📈 Generating data report...")
        fetcher.create_synthetic_test_data()
        fetcher.generate_data_report()
        return
    
    # Main pipeline
    use_real_data = not args.test
    if args.real:
        use_real_data = True
    
    if use_real_data:
        print("\n🌐 Mode: Real OSM Data Fetch")
        print("   This will attempt to download Leipzig's actual urban data.")
        print("   Note: Internet connection required, may take several minutes.")
    else:
        print("\n🛠️  Mode: Synthetic Test Data")
        print("   Creating realistic test data for development.")
    
    confirm = input("\nProceed? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return False
    
    # Run enhanced pipeline
    success = fetcher.run_enhanced_pipeline(use_real_data=use_real_data)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)   