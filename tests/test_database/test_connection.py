"""
Test database connection and basic operations.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database.db_config import db_config
from src.database.utils import DatabaseUtils

def test_database_connection():
    """Test database connection."""
    print("Testing database connection...")
    
    if DatabaseUtils.test_connection():
        print("✅ Database connection successful")
        return True
    else:
        print("❌ Database connection failed")
        return False

def test_table_creation():
    """Test that tables can be created."""
    print("\nTesting table creation...")
    
    try:
        # Drop tables if they exist
        DatabaseUtils.drop_tables()
        
        # Create tables
        DatabaseUtils.create_tables()
        
        # Check table counts
        counts = DatabaseUtils.get_table_counts()
        
        if len(counts) >= 6:
            print("✅ All tables created successfully")
            print(f"   Tables: {', '.join(counts.keys())}")
            return True
        else:
            print(f"❌ Only {len(counts)} tables created, expected at least 6")
            return False
            
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        return False

def test_basic_operations():
    """Test basic CRUD operations."""
    print("\nTesting basic operations...")
    
    try:
        # Test session creation
        session = db_config.get_session()
        assert session is not None
        session.close()
        
        # Test raw SQL execution
        result = DatabaseUtils.execute_raw_sql("SELECT 1 + 1 as sum")
        if result and result[0][0] == 2:
            print("✅ Basic operations test passed")
            return True
        else:
            print("❌ Basic operations test failed")
            return False
            
    except Exception as e:
        print(f"❌ Basic operations failed: {e}")
        return False

def test_database_info():
    """Test database information retrieval."""
    print("\nTesting database information retrieval...")
    
    try:
        info = DatabaseUtils.get_database_info()
        
        if 'connection' in info and 'table_counts' in info:
            print("✅ Database info retrieved successfully")
            print(f"   Host: {info['connection'].get('host')}")
            print(f"   Database: {info['connection'].get('database')}")
            print(f"   Total tables: {len(info['table_counts'])}")
            return True
        else:
            print("❌ Database info incomplete")
            return False
            
    except Exception as e:
        print(f"❌ Database info retrieval failed: {e}")
        return False

def main():
    """Run all database tests."""
    print("=" * 60)
    print("DATABASE TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Table Creation", test_table_creation),
        ("Basic Operations", test_basic_operations),
        ("Database Info", test_database_info)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} raised exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All database tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)