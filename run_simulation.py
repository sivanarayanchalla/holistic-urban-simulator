#!/usr/bin/env python3
"""
Main script to run the urban simulation.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

print("=" * 60)
print("URBAN SIMULATOR - SIMULATION RUNNER")
print("=" * 60)

try:
    from src.core_engine.simulation_engine import main as run_simulation
    
    if __name__ == "__main__":
        run_id = run_simulation()
        if run_id:
            print(f"\n✅ Simulation successful! Run ID: {run_id}")
            sys.exit(0)
        else:
            print("\n❌ Simulation failed")
            sys.exit(1)
            
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nMake sure you have installed all requirements:")
    print("  pip install mesa numpy sqlalchemy geoalchemy2")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)