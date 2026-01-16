#!/usr/bin/env python3
"""
Database setup script for the Urban Simulator with EV infrastructure support.
Creates all tables, indexes, and initial data structures.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from database.db_config import db_config
from database.utils import DatabaseUtils
from database.models import Base
from sqlalchemy import text, inspect

def setup_ev_infrastructure():
    """Create EV infrastructure table and related objects."""
    print("\n⚡ Setting up EV infrastructure tables...")
    
    try:
        with db_config.engine.connect() as conn:
            # Check if EV infrastructure table already exists
            inspector = inspect(db_config.engine)
            existing_tables = inspector.get_table_names()
            
            if 'ev_infrastructure' in existing_tables:
                print("  ℹ️  EV infrastructure table already exists")
                return True
            
            # Create EV infrastructure table
            create_ev_table_sql = """
            CREATE TABLE IF NOT EXISTS ev_infrastructure (
                id SERIAL PRIMARY KEY,
                ev_type VARCHAR(50) NOT NULL,
                capacity_kw INTEGER NOT NULL DEFAULT 22,
                operator VARCHAR(100),
                authentication VARCHAR(100),
                fee VARCHAR(10),
                source VARCHAR(50) NOT NULL,
                geometry GEOMETRY(Point, 4326) NOT NULL,
                properties JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                CONSTRAINT valid_capacity CHECK (capacity_kw > 0),
                CONSTRAINT valid_geometry CHECK (ST_IsValid(geometry))
            );
            """
            conn.execute(text(create_ev_table_sql))
            
            # Create spatial index
            create_ev_index_sql = """
            CREATE INDEX IF NOT EXISTS idx_ev_infrastructure_geom 
            ON ev_infrastructure USING GIST(geometry);
            """
            conn.execute(text(create_ev_index_sql))
            
            # Create other indexes
            conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ev_infrastructure_type 
            ON ev_infrastructure(ev_type);
            """))
            
            conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ev_infrastructure_capacity 
            ON ev_infrastructure(capacity_kw);
            """))
            
            # Create trigger for updated_at
            conn.execute(text("""
            CREATE OR REPLACE FUNCTION update_ev_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """))
            
            conn.execute(text("""
            DROP TRIGGER IF EXISTS trigger_ev_updated_at ON ev_infrastructure;
            CREATE TRIGGER trigger_ev_updated_at
                BEFORE UPDATE ON ev_infrastructure
                FOR EACH ROW
                EXECUTE FUNCTION update_ev_updated_at();
            """))
            
            # Create views
            conn.execute(text("""
            CREATE OR REPLACE VIEW ev_fast_chargers AS
            SELECT * FROM ev_infrastructure 
            WHERE ev_type = 'fast_charger' OR capacity_kw >= 50;
            """))
            
            conn.execute(text("""
            CREATE OR REPLACE VIEW ev_spatial_analysis AS
            SELECT 
                id,
                ev_type,
                capacity_kw,
                operator,
                geometry,
                ST_X(geometry::geometry) as longitude,
                ST_Y(geometry::geometry) as latitude,
                properties->>'opening_hours' as opening_hours,
                properties->>'socket' as socket_type,
                properties->>'parking' as parking_info
            FROM ev_infrastructure;
            """))
            
            # Create function for nearby amenities
            conn.execute(text("""
            CREATE OR REPLACE FUNCTION find_nearby_amenities(
                p_radius_km FLOAT DEFAULT 0.5
            )
            RETURNS TABLE(
                ev_id INTEGER,
                charger_type VARCHAR,
                capacity_kw INTEGER,
                amenities_count INTEGER,
                amenity_types JSONB
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    ev.id,
                    ev.ev_type,
                    ev.capacity_kw,
                    COUNT(poi.id)::INTEGER as amenities_count,
                    jsonb_agg(DISTINCT poi.poi_type) as amenity_types
                FROM ev_infrastructure ev
                LEFT JOIN points_of_interest poi ON 
                    ST_DWithin(
                        ev.geometry::geography,
                        poi.geometry::geography,
                        p_radius_km * 1000  -- Convert km to meters
                    )
                WHERE poi.poi_type IN ('restaurant', 'cafe', 'shop', 'supermarket', 'hotel', 'charging_station')
                GROUP BY ev.id, ev.ev_type, ev.capacity_kw;
            END;
            $$ LANGUAGE plpgsql;
            """))
            
            conn.commit()
            print("  ✅ EV infrastructure setup complete")
            
            return True
            
    except Exception as e:
        print(f"  ❌ Error setting up EV infrastructure: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_city_boundary():
    """Create default city boundary for Leipzig."""
    print("\n🏙️  Creating default city boundary...")
    
    try:
        with db_config.engine.connect() as conn:
            # Check if we already have a boundary
            result = conn.execute(text("SELECT COUNT(*) FROM city_boundary")).scalar()
            
            if result and result > 0:
                print(f"  ℹ️  City boundary already exists ({result} records)")
                return True
            
            # Create Leipzig boundary if not exists
            create_boundary_sql = """
            INSERT INTO city_boundary (city_name, country_code, admin_level, geometry, area_sqkm)
            VALUES (
                'Leipzig', 
                'DE', 
                8,
                ST_SetSRID(ST_MakeEnvelope(12.2, 51.25, 12.55, 51.45), 4326),
                ST_Area(ST_MakeEnvelope(12.2, 51.25, 12.55, 51.45)::geography) / 1000000
            )
            ON CONFLICT (city_name, country_code) DO NOTHING;
            """
            
            conn.execute(text(create_boundary_sql))
            conn.commit()
            print("  ✅ Created Leipzig city boundary")
            
            return True
            
    except Exception as e:
        print(f"  ⚠️  Could not create city boundary: {e}")
        return False

def setup_spatial_indexes():
    """Create additional spatial indexes for performance."""
    print("\n🗺️  Creating spatial indexes...")
    
    try:
        with db_config.engine.connect() as conn:
            # List of tables and their geometry columns
            spatial_tables = [
                ('land_use', 'geometry'),
                ('points_of_interest', 'geometry'),
                ('transport_network', 'geometry'),
                ('spatial_grid', 'geometry'),
                ('simulation_state', 'geometry'),
                ('ev_infrastructure', 'geometry')
            ]
            
            for table, geom_column in spatial_tables:
                # Check if index exists
                check_sql = f"""
                SELECT 1 FROM pg_indexes 
                WHERE tablename = '{table}' 
                AND indexname = 'idx_{table}_{geom_column}';
                """
                
                result = conn.execute(text(check_sql)).fetchone()
                
                if not result:
                    # Create index
                    create_sql = f"""
                    CREATE INDEX idx_{table}_{geom_column} 
                    ON {table} USING GIST({geom_column});
                    """
                    conn.execute(text(create_sql))
                    print(f"  ✅ Created index for {table}.{geom_column}")
                else:
                    print(f"  ℹ️  Index for {table}.{geom_column} already exists")
            
            conn.commit()
            print("  ✅ All spatial indexes created")
            return True
            
    except Exception as e:
        print(f"  ⚠️  Error creating spatial indexes: {e}")
        return False

def create_analysis_views():
    """Create useful analysis views."""
    print("\n📊 Creating analysis views...")
    
    try:
        with db_config.engine.connect() as conn:
            # View 1: Latest simulation state
            view1_sql = """
            CREATE OR REPLACE VIEW latest_simulation_state AS
            SELECT DISTINCT ON (run_id, grid_id) *
            FROM simulation_state
            ORDER BY run_id, grid_id, timestep DESC;
            """
            conn.execute(text(view1_sql))
            print("  ✅ Created view: latest_simulation_state")
            
            # View 2: Grid cell summary
            view2_sql = """
            CREATE OR REPLACE VIEW grid_cell_summary AS
            SELECT 
                g.grid_id,
                g.grid_type,
                g.resolution_meters,
                g.geometry,
                COUNT(DISTINCT lu.category) as land_use_types,
                COUNT(poi.id) as poi_count,
                COUNT(ev.id) as ev_charger_count,
                AVG(ss.population_density) as avg_pop_density,
                AVG(ss.traffic_congestion) as avg_congestion
            FROM spatial_grid g
            LEFT JOIN land_use lu ON ST_Intersects(g.geometry, lu.geometry)
            LEFT JOIN points_of_interest poi ON ST_Within(poi.geometry, g.geometry)
            LEFT JOIN ev_infrastructure ev ON ST_Within(ev.geometry, g.geometry)
            LEFT JOIN simulation_state ss ON g.grid_id = ss.grid_id
            GROUP BY g.grid_id, g.grid_type, g.resolution_meters, g.geometry;
            """
            conn.execute(text(view2_sql))
            print("  ✅ Created view: grid_cell_summary")
            
            # View 3: EV infrastructure analysis
            view3_sql = """
            CREATE OR REPLACE VIEW ev_accessibility_analysis AS
            SELECT 
                g.grid_id,
                g.geometry,
                COUNT(ev.id) as ev_charger_count,
                SUM(ev.capacity_kw) as total_capacity_kw,
                AVG(ev.capacity_kw) as avg_capacity_kw,
                COUNT(CASE WHEN ev.ev_type = 'fast_charger' THEN 1 END) as fast_charger_count,
                ST_Distance(g.centroid::geography, 
                    (SELECT geometry::geography FROM ev_infrastructure 
                     WHERE ST_DWithin(g.centroid::geography, geometry::geography, 5000)
                     ORDER BY ST_Distance(g.centroid::geography, geometry::geography) 
                     LIMIT 1)
                ) as distance_to_nearest_charger
            FROM spatial_grid g
            LEFT JOIN ev_infrastructure ev ON ST_Within(ev.geometry, g.geometry)
            GROUP BY g.grid_id, g.geometry, g.centroid;
            """
            conn.execute(text(view3_sql))
            print("  ✅ Created view: ev_accessibility_analysis")
            
            conn.commit()
            return True
            
    except Exception as e:
        print(f"  ⚠️  Error creating views: {e}")
        return False

def check_postgis_extensions():
    """Check and enable PostGIS extensions."""
    print("\n🌍 Checking PostGIS extensions...")
    
    try:
        with db_config.engine.connect() as conn:
            # Check if PostGIS is available
            result = conn.execute(text("SELECT COUNT(*) FROM pg_extension WHERE extname = 'postgis'")).scalar()
            
            if result == 0:
                print("  ⚠️  PostGIS extension not found, attempting to create...")
                try:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology;"))
                    conn.commit()
                    print("  ✅ PostGIS extensions created")
                except Exception as e:
                    print(f"  ❌ Failed to create PostGIS extensions: {e}")
                    return False
            else:
                print("  ✅ PostGIS extension is available")
            
            # Get PostGIS version
            version_result = conn.execute(text("SELECT PostGIS_Version();")).fetchone()
            if version_result:
                print(f"  📋 PostGIS Version: {version_result[0]}")
            
            return True
            
    except Exception as e:
        print(f"  ❌ Error checking PostGIS: {e}")
        return False

def setup_database():
    """Execute the complete database schema setup with EV support."""
    
    print("=" * 60)
    print("🏙️  HOLISTIC URBAN SIMULATOR - DATABASE SETUP")
    print("⚡ Now with EV Infrastructure Support")
    print("=" * 60)
    
    # Test connection
    print("\n1. Testing database connection...")
    if not DatabaseUtils.test_connection():
        print("❌ Database connection failed. Please check your configuration.")
        return False
    
    # Check PostGIS
    if not check_postgis_extensions():
        print("⚠️  PostGIS extensions may not be fully functional")
    
    # Create tables from models
    print("\n2. Creating database tables from models...")
    try:
        # Get existing tables before creation
        inspector = inspect(db_config.engine)
        existing_before = set(inspector.get_table_names())
        
        # Create tables
        Base.metadata.create_all(db_config.engine)
        
        # Get tables after creation
        existing_after = set(inspector.get_table_names())
        new_tables = existing_after - existing_before
        
        print(f"✅ Created {len(new_tables)} new tables:")
        for table in sorted(new_tables):
            print(f"   • {table}")
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Setup EV infrastructure (separate from ORM models)
    if not setup_ev_infrastructure():
        print("⚠️  EV infrastructure setup had issues, but continuing...")
    
    # Create city boundary
    if not create_city_boundary():
        print("⚠️  City boundary creation failed, but continuing...")
    
    # Create spatial indexes
    if not setup_spatial_indexes():
        print("⚠️  Spatial index creation had issues, but continuing...")
    
    # Create analysis views
    if not create_analysis_views():
        print("⚠️  View creation had issues, but continuing...")
    
    # Verify table creation
    print("\n3. Verifying table creation...")
    try:
        table_counts = DatabaseUtils.get_table_counts()
        
        expected_tables = [
            'spatial_grid',
            'simulation_run', 
            'simulation_state',
            'land_use',
            'points_of_interest',
            'transport_network',
            'city_boundary',
            'ev_infrastructure'
        ]
        
        all_tables_exist = True
        for table in expected_tables:
            if table in table_counts:
                row_count = table_counts[table]
                status = "✅" if row_count >= 0 else "⚠️"
                print(f"  {status} Table '{table}' exists: {row_count} rows")
            else:
                print(f"  ❌ Table '{table}' NOT FOUND")
                all_tables_exist = False
        
        if not all_tables_exist:
            print("⚠️  Some tables are missing, but setup may still work")
        
    except Exception as e:
        print(f"  ⚠️  Error verifying tables: {e}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("DATABASE SETUP COMPLETE!")
    print("=" * 60)
    
    try:
        print("\n📊 Database Summary:")
        table_counts = DatabaseUtils.get_table_counts()
        for table, count in sorted(table_counts.items()):
            if count > 0:
                print(f"  📈 {table}: {count} rows")
            else:
                print(f"  📭 {table}: {count} rows (empty)")
        
        # Get database info
        print("\n🌍 PostGIS Information:")
        info = DatabaseUtils.get_database_info()
        if 'postgis' in info:
            postgis_info = info['postgis']
            if 'postgis_version' in postgis_info:
                print(f"  Version: {postgis_info['postgis_version']}")
            if 'spatial_ref_count' in postgis_info:
                print(f"  Spatial References: {postgis_info['spatial_ref_count']}")
        
        # Print connection details
        print("\n🔗 Connection Details:")
        conn_info = info.get('connection', {})
        print(f"  Host: {conn_info.get('host', 'localhost')}")
        print(f"  Port: {conn_info.get('port', 5432)}")
        print(f"  Database: {conn_info.get('database', 'urban_sim')}")
        print(f"  User: {conn_info.get('user', 'simulator_user')}")
        
    except Exception as e:
        print(f"⚠️  Error generating summary: {e}")
    
    # Next steps
    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS FOR EV CATALYST MODELING:")
    print("=" * 60)
    print("1. Load Leipzig data:")
    print("   python src/data_pipeline/fetch_leipzig_data.py --test")
    print("\n2. Create spatial grid:")
    print("   python src/data_pipeline/create_spatial_grid.py")
    print("\n3. Run simulation with EV module:")
    print("   python src/core_engine/run_simulation.py --ev")
    print("\n4. Analyze EV impact:")
    print("   python src/analysis/ev_catalyst_analysis.py")
    print("\n5. Visualize results:")
    print("   python src/visualization/ev_dashboard.py")
    
    print("\n✅ Database is ready for the Urban Simulator with EV support!")
    return True

if __name__ == "__main__":
    success = setup_database()
    sys.exit(0 if success else 1)