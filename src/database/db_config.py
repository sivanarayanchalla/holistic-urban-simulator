# src/database/db_config.py (FIXED VERSION)
import os
from pathlib import Path
from typing import Dict, Any
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker
import psycopg2

# Load environment variables - force reload
env_path = Path(".env")
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
    print(f"[*] Loaded .env from: {env_path.absolute()}")
else:
    print("[!] .env file not found, using defaults")

class DatabaseConfig:
    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path) if config_path else Path("config.yaml")
        
        # DEBUG: Print what we're reading
        print("\n[DEBUG] Reading configuration:")
        print(f"   DB_HOST from env: '{os.getenv('DB_HOST')}'")
        print(f"   DB_USER from env: '{os.getenv('DB_USER')}'")
        print(f"   DB_PASSWORD from env: '{'*' * len(os.getenv('DB_PASSWORD', '')) if os.getenv('DB_PASSWORD') else 'NOT SET'}'")
        
        self.config = self._load_config()
        self._engine = None
        self._session_factory = None
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration with better error handling."""
        # Start with hardcoded defaults
        config = {
            'database': {
                'host': 'localhost',
                'port': 5432,
                'name': 'urban_sim',
                'user': 'simulator_user',
                'password': 'UrbanSim2026!',
                'schema': 'public',
                'pool_size': 5
            }
        }
        
        # Override with environment variables
        env_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        for var in env_vars:
            env_value = os.getenv(var)
            if env_value is not None:
                key = var.lower().replace('db_', '')
                if var == 'DB_PORT':
                    config['database'][key] = int(env_value)
                else:
                    config['database'][key] = env_value
        
        print(f"\n[OK] Final database config:")
        print(f"   Host: {config['database']['host']}")
        print(f"   Port: {config['database']['port']}")
        print(f"   Database: {config['database']['name']}")
        print(f"   User: {config['database']['user']}")
        print(f"   Password: {'*' * len(config['database']['password'])}")
        
        return config
    
    def get_connection_url(self, show_password=False) -> URL:
        """Create SQLAlchemy connection URL."""
        db_config = self.config['database']
        
        url = URL.create(
            drivername="postgresql+psycopg2",
            username=db_config['user'],
            password=db_config['password'],
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['name']
        )
        
        if show_password:
            print(f"🔗 Connection URL: {url}")
        
        return url
    
    @property
    def engine(self):
        if self._engine is None:
            connection_url = self.get_connection_url(show_password=False)
            
            # Test connection first with psycopg2
            print("\n[*] Testing raw connection...")
            try:
                conn = psycopg2.connect(
                    host=self.config['database']['host'],
                    port=self.config['database']['port'],
                    database=self.config['database']['name'],
                    user=self.config['database']['user'],
                    password=self.config['database']['password']
                )
                print("   [OK] Raw psycopg2 connection successful")
                conn.close()
            except Exception as e:
                print(f"   [ERROR] Raw connection failed: {e}")
                raise
            
            # Create SQLAlchemy engine
            self._engine = create_engine(
                connection_url,
                pool_size=self.config['database'].get('pool_size', 5),
                pool_pre_ping=True,
                echo=False,
                connect_args={'connect_timeout': 10}
            )
            
        return self._engine
    
    @property
    def session_factory(self):
        """Get session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False
            )
        return self._session_factory
    
    def get_session(self):
        """Get a new database session."""
        return self.session_factory()
    
    def test_connection(self) -> bool:
        """Test database connection with detailed error messages."""
        print("\n" + "=" * 50)
        print("TESTING DATABASE CONNECTION")
        print("=" * 50)
        
        try:
            # Test 1: Direct psycopg2 connection
            print("\n1. Testing direct psycopg2 connection...")
            conn = psycopg2.connect(
                host=self.config['database']['host'],
                port=self.config['database']['port'],
                database=self.config['database']['name'],
                user=self.config['database']['user'],
                password=self.config['database']['password'],
                connect_timeout=5
            )
            
            # Test 2: Basic query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            if cursor.fetchone()[0] == 1:
                print("   ✅ Basic query successful")
            
            # Test 3: Check PostGIS
            cursor.execute("SELECT PostGIS_Version()")
            postgis_version = cursor.fetchone()[0]
            print(f"   ✅ PostGIS available: {postgis_version}")
            
            # Test 4: Check our tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            print(f"   ✅ Found {len(tables)} tables in database")
            
            cursor.close()
            conn.close()
            
            print("\n" + "=" * 50)
            print("✅ ALL CONNECTION TESTS PASSED!")
            print("=" * 50)
            return True
            
        except psycopg2.OperationalError as e:
            print(f"\n❌ OPERATIONAL ERROR: {e}")
            print("\nPossible causes:")
            print("1. PostgreSQL service not running")
            print("2. Wrong host/port")
            print("3. Wrong username/password")
            print("4. Database doesn't exist")
            return False
            
        except psycopg2.ProgrammingError as e:
            print(f"\n❌ PROGRAMMING ERROR: {e}")
            print("\nPossible causes:")
            print("1. User doesn't exist")
            print("2. User doesn't have permissions")
            return False
            
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

# Global instance
db_config = DatabaseConfig()