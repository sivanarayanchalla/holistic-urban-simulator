#!/usr/bin/env python3
"""
Dashboard Quick Start Script
=============================

This script helps you quickly launch the Urban Simulator dashboard.

Usage:
    python launch_dashboard.py              # Open HTML dashboard in browser
    python launch_dashboard.py --streamlit  # Launch interactive Streamlit dashboard
    python launch_dashboard.py --help       # Show all options
"""

import sys
import webbrowser
import subprocess
from pathlib import Path
import argparse

def launch_html_dashboard():
    """Open the static HTML dashboard in default browser."""
    print("\n[*] Launching HTML Dashboard...")
    
    dashboard_file = Path(__file__).parent / 'urban_simulator_dashboard.html'
    
    if not dashboard_file.exists():
        print(f"[ERROR] Dashboard file not found: {dashboard_file}")
        print("[*] Generating dashboard...")
        result = subprocess.run([sys.executable, 'dashboard.py'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERROR] Failed to generate dashboard:")
            print(result.stderr)
            return False
        print("[OK] Dashboard generated successfully!")
    
    # Open in browser
    dashboard_url = f"file:///{dashboard_file.absolute()}".replace("\\", "/")
    print(f"[OK] Opening dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    
    return True

def launch_streamlit_dashboard():
    """Launch the interactive Streamlit dashboard."""
    print("\n[*] Launching Streamlit Dashboard...")
    print("[*] Checking dependencies...")
    
    try:
        import streamlit
        print("[OK] Streamlit is installed")
    except ImportError:
        print("[WARN] Streamlit not found. Installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'streamlit', 
                       'plotly', 'pandas', 'numpy'], 
                      capture_output=True)
        print("[OK] Dependencies installed")
    
    print("[*] Starting Streamlit server...")
    print("[*] Dashboard will open at: http://localhost:8501")
    
    try:
        subprocess.run([sys.executable, '-m', 'streamlit', 'run', 
                       'streamlit_dashboard.py'])
    except KeyboardInterrupt:
        print("\n[*] Dashboard closed")
        return True

def regenerate_dashboard():
    """Regenerate the HTML dashboard from scratch."""
    print("\n[*] Regenerating HTML Dashboard...")
    
    result = subprocess.run([sys.executable, 'dashboard.py'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("[OK] Dashboard regenerated successfully!")
        print(result.stdout)
        return True
    else:
        print("[ERROR] Failed to regenerate dashboard:")
        print(result.stderr)
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Urban Simulator Dashboard Launcher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_dashboard.py              # Open HTML dashboard
  python launch_dashboard.py --streamlit  # Launch Streamlit dashboard
  python launch_dashboard.py --regenerate # Rebuild HTML dashboard
  python launch_dashboard.py --info       # Show dashboard information
        """
    )
    
    parser.add_argument('--streamlit', action='store_true',
                       help='Launch interactive Streamlit dashboard')
    parser.add_argument('--regenerate', action='store_true',
                       help='Regenerate HTML dashboard from data')
    parser.add_argument('--info', action='store_true',
                       help='Display dashboard information')
    
    args = parser.parse_args()
    
    # Header
    print("\n" + "="*70)
    print("URBAN SIMULATOR CALIBRATION DASHBOARD")
    print("="*70)
    
    if args.info:
        print("""
DASHBOARD INFORMATION
=====================

Available Dashboards:
1. Static HTML Dashboard (html)
   - No dependencies required
   - Works offline
   - Print-friendly
   - Single file (urban_simulator_dashboard.html)
   - Size: ~127 KB

2. Interactive Streamlit Dashboard (--streamlit)
   - Real-time filters and interactions
   - Dynamic chart updates
   - Export capabilities
   - Requires: streamlit, plotly, pandas

FEATURES
========

1. Rent Calibration Comparison
   - Real targets vs simulation results
   - City-by-city analysis

2. Real Data Analysis  
   - 51 neighborhoods from real estate database
   - Rent distribution and statistics

3. Demographics & Displacement
   - Income segmentation (30/40/30)
   - Displacement risk curves

4. Error Analysis
   - Before/after calibration metrics
   - Validation results

5. Module Metrics
   - All 11 urban modules listed
   - Execution priorities visualized

6. Calibration Timeline
   - 8-phase program progress
   - Key deliverables

DATA SOURCES
============

CSV Files:
- real_rent_calibration_2024.csv (51 neighborhoods)
- population_scaling_factors.csv (3 cities)
- baseline_simulation_state.csv (500 records)
- zone_definitions_2024.csv (12 zones)

Database:
- PostgreSQL with 300+ simulation records
- Run IDs: Berlin, Leipzig, Munich
- 30+ metrics per timestep

QUICK START
===========

HTML Dashboard (recommended):
  1. Open urban_simulator_dashboard.html in browser
  2. Or run: python launch_dashboard.py

Streamlit Dashboard:
  1. pip install streamlit
  2. python launch_dashboard.py --streamlit
  3. Opens at http://localhost:8501

TROUBLESHOOTING
===============

File not found errors:
  - Ensure all CSV files are in data/outputs/
  - Run from project root directory

Import errors:
  - pip install plotly pandas numpy

Port conflicts:
  - Streamlit uses port 8501 by default
  - Use: streamlit run streamlit_dashboard.py --server.port 8502

REPOSITORY
==========

GitHub: https://github.com/sivanarayanchalla/holistic-urban-simulator
Last updated: January 2026
Calibration status: Complete (8/8 phases)
        """)
        return 0
    
    if args.regenerate:
        if regenerate_dashboard():
            print("\n[OK] Dashboard ready! Run again without --regenerate to launch")
            return 0
        else:
            return 1
    
    if args.streamlit:
        launch_streamlit_dashboard()
    else:
        # Default: launch HTML dashboard
        if launch_html_dashboard():
            print("\n[OK] Dashboard launched in browser")
            return 0
        else:
            return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
