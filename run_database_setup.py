#!/usr/bin/env python3
"""
Main script to set up the database for the Urban Simulator.
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from src.database.setup_database import setup_database

def main():
    """Run database setup."""
    print("Urban Simulator - Database Setup")
    print("=" * 50)
    
    print("\nThis script will:")
    print("1. Test database connection")
    print("2. Create all necessary tables")
    print("3. Set up indexes and constraints")
    print("4. Verify the setup")
    
    response = input("\nDo you want to continue? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("Setup cancelled.")
        return False
    
    print("\nStarting database setup...")
    success = setup_database()
    
    if success:
        print("\n✅ Database setup completed successfully!")
        print("\nNext steps:")
        print("1. Fetch Leipzig data: python src/data_pipeline/fetch_leipzig_data.py")
        print("2. Generate spatial grid: python src/data_pipeline/create_spatial_grid.py")
        print("3. Run tests: python -m pytest tests/test_database/")
    else:
        print("\n❌ Database setup failed!")
        print("\nTroubleshooting:")
        print("- Check that PostgreSQL is running")
        print("- Verify database credentials in .env file")
        print("- Ensure PostGIS extension is installed")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)