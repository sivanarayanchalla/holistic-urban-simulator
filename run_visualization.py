#!/usr/bin/env python3
"""
Main script to visualize urban simulation results.
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

print("=" * 60)
print("URBAN SIMULATOR - VISUALIZATION RUNNER")
print("=" * 60)

try:
    from src.visualization.create_dashboard import main
    
    if __name__ == "__main__":
        success = main()
        sys.exit(0 if success else 1)
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nMake sure you have installed all requirements:")
    print("  pip install plotly pandas geopandas")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)