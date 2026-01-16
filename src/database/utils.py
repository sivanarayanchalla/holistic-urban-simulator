"""
Database utility functions for the Urban Simulator with EV infrastructure support.
"""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from geoalchemy2.shape import from_shape
from shapely.geometry import shape, mapping, Polygon
from sqlalchemy.orm import Session
from sqlalchemy import func, text, select, insert, update, delete
import inspect

from .db_config import db_config
from .models import SpatialGrid, SimulationRun, SimulationState, LandUse, PointsOfInterest, TransportNetwork, EVInfrastructure

class DatabaseUtils:
    """Utility class for common database operations."""
    
    @staticmethod
    def test_connection() -> bool:
        """Test database connection."""
        try:
            with db_config.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
                return result == 1
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    @staticmethod
    def create_tables():
        """Create all database tables from models."""
        from .models import Base
        Base.metadata.create_all(db_config.engine)
        table_count = len(Base.metadata.tables)
        print(f"✅ Created {table_count} tables")
        return table_count
    
    @staticmethod
    def drop_tables():
        """Drop all database tables."""
        from .models import Base
        Base.metadata.drop_all(db_config.engine)
        print("✅ Dropped all tables")
    
    @staticmethod
    def reset_database():
        """Reset database (drop and recreate all tables)."""
        print("Resetting database...")
        DatabaseUtils.drop_tables()
        count = DatabaseUtils.create_tables()
        print(f"✅ Database reset complete ({count} tables created)")
        return count
    
    @staticmethod
    def get_table_counts() -> Dict[str, int]:
        """Get row counts for all tables."""
        table_counts = {}
        tables = [
            ('spatial_grid', SpatialGrid),
            ('simulation_run', SimulationRun),
            ('simulation_state', SimulationState),
            ('land_use', LandUse),
            ('points_of_interest', PointsOfInterest),
            ('transport_network', TransportNetwork),
            ('ev_infrastructure', EVInfrastructure)
        ]
        
        try:
            with db_config.get_session() as session:
                for table_name, model in tables:
                    try:
                        count = session.query(model).count()
                        table_counts[table_name] = count
                    except Exception as e:
                        # Table might not exist yet
                        table_counts[table_name] = 0
                        
                # Also check for city_boundary table (which might not be in models.py)
                try:
                    city_boundary_count = session.execute(
                        text("SELECT COUNT(*) FROM city_boundary")
                    ).scalar() or 0
                    table_counts['city_boundary'] = city_boundary_count
                except:
                    table_counts['city_boundary'] = 0
                    
        except Exception as e:
            print(f"Error getting table counts: {e}")
        
        return table_counts
    
    @staticmethod
    def spatial_query_to_geodataframe(query, geometry_column='geometry'):
        """Convert SQLAlchemy query with spatial data to GeoDataFrame."""
        from geopandas import GeoDataFrame
        
        try:
            # Execute query and get results
            with db_config.engine.connect() as conn:
                results = conn.execute(query).fetchall()
            
            if not results:
                return GeoDataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame([dict(row._mapping) for row in results])
            
            # Convert geometry column if present
            if geometry_column in df.columns and not df.empty:
                df[geometry_column] = df[geometry_column].apply(
                    lambda x: shape(json.loads(x)) if x else None
                )
                gdf = GeoDataFrame(df, geometry=geometry_column)
                return gdf
            
            return GeoDataFrame(df)
            
        except Exception as e:
            print(f"Error converting to GeoDataFrame: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def save_simulation_state(
        run_id: str,
        timestep: int,
        grid_states: List[Dict[str, Any]]
    ) -> bool:
        """Save simulation states for multiple grid cells."""
        try:
            with db_config.get_session() as session:
                states_to_add = []
                
                for grid_state in grid_states:
                    # Create state object
                    state = SimulationState(
                        run_id=run_id,
                        timestep=timestep,
                        grid_id=grid_state['grid_id'],
                        population=grid_state.get('population'),
                        traffic_congestion=grid_state.get('traffic_congestion'),
                        safety_score=grid_state.get('safety_score'),
                        commercial_vitality=grid_state.get('commercial_vitality'),
                        avg_rent_euro=grid_state.get('avg_rent_euro'),
                        displacement_risk=grid_state.get('displacement_risk'),
                        geometry=grid_state.get('geometry')
                    )
                    states_to_add.append(state)
                
                session.add_all(states_to_add)
                session.commit()
                
                print(f"✅ Saved {len(states_to_add)} simulation states for timestep {timestep}")
                return True
                
        except Exception as e:
            print(f"❌ Error saving simulation state: {e}")
            return False
    
    @staticmethod
    def get_simulation_states(run_id: str, timestep: Optional[int] = None):
        """Get simulation states for a run."""
        with db_config.get_session() as session:
            query = session.query(SimulationState).filter(
                SimulationState.run_id == run_id
            )
            
            if timestep is not None:
                query = query.filter(SimulationState.timestep == timestep)
            
            return query.all()
    
    @staticmethod
    def create_spatial_grid(
        geometry_wkt: str,
        resolution: int = 500,
        grid_type: str = 'hexagon'
    ) -> List[str]:
        """Create spatial grid within boundary geometry."""
        try:
            # This is a simplified version - in practice, you'd use H3 or PostGIS functions
            # For now, we'll create a dummy implementation
            with db_config.get_session() as session:
                # Create a simple test grid cell
                grid_id = f"{grid_type}_{resolution}_test_001"
                grid = SpatialGrid(
                    grid_id=grid_id,
                    grid_type=grid_type,
                    resolution_meters=resolution,
                    geometry=geometry_wkt  # Should be WKT format
                )
                session.add(grid)
                session.commit()
                
                return [grid_id]
                
        except Exception as e:
            print(f"❌ Error creating spatial grid: {e}")
            return []
    
    @staticmethod
    def backup_database(backup_path: str = "backup.sql"):
        """Create database backup using pg_dump."""
        import subprocess
        import os
        
        config = db_config.config['database']
        
        # Build pg_dump command
        cmd = [
            'pg_dump',
            '-h', config['host'],
            '-p', str(config['port']),
            '-U', config['user'],
            '-d', config['name'],
            '-F', 'p',  # Plain SQL format
            '-f', backup_path
        ]
        
        # Set password in environment
        env = os.environ.copy()
        env['PGPASSWORD'] = config['password']
        
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Database backup created: {backup_path}")
                return True
            else:
                print(f"❌ Backup failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Backup error: {e}")
            return False
    
    @staticmethod
    def execute_raw_sql(sql: str, params: Dict = None):
        """Execute raw SQL query."""
        try:
            with db_config.engine.connect() as conn:
                if params:
                    result = conn.execute(text(sql), params)
                else:
                    result = conn.execute(text(sql))
                
                if result.returns_rows:
                    return result.fetchall()
                else:
                    conn.commit()
                    return result.rowcount
        except Exception as e:
            print(f"❌ SQL execution error: {e}")
            return None
    
    @staticmethod
    def get_database_info() -> Dict[str, Any]:
        """Get database information and statistics."""
        info = {}
        
        try:
            # Basic connection info
            info['connection'] = {
                'host': db_config.host,
                'port': db_config.port,
                'database': db_config.database,
                'user': db_config.user
            }
            
            # Table counts
            info['table_counts'] = DatabaseUtils.get_table_counts()
            
            # PostGIS info
            sql = """
            SELECT 
                PostGIS_Version() as postgis_version,
                PostGIS_Full_Version() as postgis_full_version,
                (SELECT COUNT(*) FROM spatial_ref_sys) as spatial_ref_count
            """
            
            result = DatabaseUtils.execute_raw_sql(sql)
            if result:
                info['postgis'] = dict(result[0]._mapping)
            
            # Database size
            size_sql = """
            SELECT 
                pg_database_size(current_database()) as db_size_bytes,
                pg_size_pretty(pg_database_size(current_database())) as db_size_pretty
            """
            size_result = DatabaseUtils.execute_raw_sql(size_sql)
            if size_result:
                info['size'] = dict(size_result[0]._mapping)
                
        except Exception as e:
            print(f"Error getting database info: {e}")
        
        return info
    
    @staticmethod
    def get_ev_statistics() -> Dict[str, Any]:
        """Get statistics about EV infrastructure."""
        stats = {}
        
        try:
            with db_config.engine.connect() as conn:
                # Basic counts
                stats['total_chargers'] = conn.execute(
                    text("SELECT COUNT(*) FROM ev_infrastructure")
                ).scalar() or 0
                
                stats['fast_chargers'] = conn.execute(
                    text("SELECT COUNT(*) FROM ev_infrastructure WHERE ev_type = 'fast_charger' OR capacity_kw >= 50")
                ).scalar() or 0
                
                stats['total_capacity'] = conn.execute(
                    text("SELECT SUM(capacity_kw) FROM ev_infrastructure")
                ).scalar() or 0
                
                stats['avg_capacity'] = conn.execute(
                    text("SELECT AVG(capacity_kw) FROM ev_infrastructure")
                ).scalar() or 0
                
                # Operator distribution
                operator_sql = """
                SELECT operator, COUNT(*) as count, SUM(capacity_kw) as total_capacity
                FROM ev_infrastructure
                GROUP BY operator
                ORDER BY count DESC
                """
                operator_result = conn.execute(text(operator_sql)).fetchall()
                stats['operators'] = [dict(row._mapping) for row in operator_result]
                
                # Charger type distribution
                type_sql = """
                SELECT ev_type, COUNT(*) as count, AVG(capacity_kw) as avg_capacity
                FROM ev_infrastructure
                GROUP BY ev_type
                """
                type_result = conn.execute(text(type_sql)).fetchall()
                stats['types'] = [dict(row._mapping) for row in type_result]
                
                # Spatial distribution
                spatial_sql = """
                SELECT 
                    ST_X(geometry) as longitude,
                    ST_Y(geometry) as latitude,
                    ev_type,
                    capacity_kw,
                    operator
                FROM ev_infrastructure
                """
                spatial_result = conn.execute(text(spatial_sql)).fetchall()
                stats['locations'] = [dict(row._mapping) for row in spatial_result]
                
        except Exception as e:
            print(f"Error getting EV statistics: {e}")
        
        return stats
    
    @staticmethod
    def find_nearby_amenities(ev_id: int, radius_km: float = 0.5):
        """Find amenities near an EV charger."""
        try:
            sql = f"""
            SELECT * FROM find_nearby_amenities({radius_km})
            WHERE ev_id = {ev_id}
            """
            result = DatabaseUtils.execute_raw_sql(sql)
            if result:
                return [dict(row._mapping) for row in result]
            return []
        except Exception as e:
            print(f"Error finding nearby amenities: {e}")
            return []
    
    @staticmethod
    def get_all_ev_chargers():
        """Get all EV chargers from the database."""
        try:
            with db_config.get_session() as session:
                return session.query(EVInfrastructure).all()
        except Exception as e:
            print(f"Error getting EV chargers: {e}")
            return []
    
    @staticmethod
    def add_ev_charger(
        ev_type: str,
        capacity_kw: int,
        geometry_wkt: str,
        operator: str = None,
        authentication: str = None,
        fee: str = None,
        source: str = 'manual',
        properties: Dict = None
    ) -> bool:
        """Add a new EV charger to the database."""
        try:
            with db_config.get_session() as session:
                charger = EVInfrastructure(
                    ev_type=ev_type,
                    capacity_kw=capacity_kw,
                    operator=operator,
                    authentication=authentication,
                    fee=fee,
                    source=source,
                    geometry=geometry_wkt,
                    properties=properties or {}
                )
                session.add(charger)
                session.commit()
                print(f"✅ Added EV charger: {ev_type} ({capacity_kw}kW) by {operator}")
                return True
        except Exception as e:
            print(f"❌ Error adding EV charger: {e}")
            return False