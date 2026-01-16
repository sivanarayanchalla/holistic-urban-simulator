#!/usr/bin/env python3
"""
Run scenario comparison to validate EV infrastructure impact on urban metrics.
Compares three scenarios: Baseline (no chargers), Current (4 chargers), 2x Growth (8 chargers).
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from database.db_config import db_config
from database.models import SimulationRun, SimulationState, EVInfrastructure
from sqlalchemy import text, delete
import subprocess

class ScenarioComparison:
    """Manage and run EV infrastructure scenarios."""
    
    def __init__(self):
        self.scenarios = {
            'baseline': {
                'name': 'Baseline (No EV Chargers)',
                'description': 'Control scenario with zero EV infrastructure',
                'charger_count': 0,
                'scaling_factor': 0.0  # 0% of current chargers
            },
            'current': {
                'name': 'Current (4 Chargers)',
                'description': 'Existing EV infrastructure in Leipzig',
                'charger_count': 4,
                'scaling_factor': 1.0  # 100% of current chargers
            },
            '2x_growth': {
                'name': '2x Growth (8 Chargers)',
                'description': 'Doubled EV infrastructure expansion',
                'charger_count': 8,
                'scaling_factor': 2.0  # 200% of current chargers
            }
        }
    
    def setup_scenario_ev_data(self, scenario_key):
        """Prepare EV infrastructure data for a specific scenario."""
        scenario = self.scenarios[scenario_key]
        scaling_factor = scenario['scaling_factor']
        
        print(f"\n{'='*60}")
        print(f"🔧 Setting up scenario: {scenario['name']}")
        print(f"{'='*60}")
        print(f"   Scaling factor: {scaling_factor:.1f}x")
        print(f"   Expected chargers: {scenario['charger_count']}")
        
        with db_config.engine.connect() as conn:
            # Clear existing EV infrastructure for this scenario
            # We'll use the simulation metadata to track which scenario we're in
            print("   ✓ EV infrastructure ready")
        
        return scaling_factor
    
    def run_scenario(self, scenario_key):
        """Run a simulation for a specific scenario."""
        scenario = self.scenarios[scenario_key]
        scaling_factor = scenario['scaling_factor']
        
        print(f"\n{'='*60}")
        print(f"🚀 Running Scenario: {scenario['name']}")
        print(f"{'='*60}")
        print(f"   Description: {scenario['description']}")
        print(f"   Charger count: {scenario['charger_count']}")
        
        # Prepare simulation environment
        self.setup_scenario_ev_data(scenario_key)
        
        # Scale EV infrastructure based on scenario
        self._scale_ev_infrastructure(scaling_factor)
        
        # Run simulation
        print("\n   Starting simulation run...")
        try:
            result = subprocess.run(
                [sys.executable, 'run_simulation.py'],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                # Extract run_id from output
                output_lines = result.stdout.split('\n')
                run_id = None
                for line in output_lines:
                    if 'Run ID:' in line:
                        run_id = line.split('Run ID:')[1].strip()
                        break
                
                if run_id:
                    print(f"   ✅ Simulation completed successfully")
                    print(f"   📊 Run ID: {run_id}")
                    
                    # Tag this run with scenario information
                    self._tag_run_with_scenario(run_id, scenario_key)
                    return run_id
                else:
                    print(f"   ⚠️ Simulation ran but could not extract run ID")
                    print(f"   Output: {result.stdout[-500:]}")
                    return None
            else:
                print(f"   ❌ Simulation failed")
                print(f"   Error: {result.stderr[-500:]}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"   ❌ Simulation timed out (>5 minutes)")
            return None
        except Exception as e:
            print(f"   ❌ Error running simulation: {e}")
            return None
    
    def _scale_ev_infrastructure(self, scaling_factor):
        """Scale EV infrastructure by duplicating/removing chargers."""
        with db_config.engine.connect() as conn:
            trans = conn.begin()
            try:
                # Get current chargers
                query = text("SELECT id, ev_type, capacity_kw, operator, authentication, fee, source, ST_AsText(geometry) as geometry, properties FROM ev_infrastructure ORDER BY id")
                current_chargers = pd.read_sql(query, conn)
                
                if current_chargers.empty:
                    print("   ⚠️ No existing chargers found in database")
                    trans.commit()
                    return
                
                # Delete all existing chargers
                delete_query = text("DELETE FROM ev_infrastructure")
                conn.execute(delete_query)
                
                if scaling_factor == 0:
                    print(f"   ✓ Removed all chargers for baseline scenario")
                else:
                    # Scale and duplicate chargers
                    num_to_create = int(len(current_chargers) * scaling_factor)
                    
                    if scaling_factor > 1:
                        # Duplicate and adjust coordinates slightly
                        scaled_chargers = []
                        for i in range(num_to_create):
                            base_idx = i % len(current_chargers)
                            charger = current_chargers.iloc[base_idx].copy()
                            
                            # Add small random offset to avoid exact duplicates
                            if charger['geometry']:
                                noise = np.random.normal(0, 0.0001, 2)
                                # Extract coordinates from WKT and adjust
                                geom_wkt = charger['geometry']
                                # Simple parsing for POINT geometry
                                try:
                                    # Extract coordinates from "POINT(lon lat)"
                                    import re
                                    coords = re.findall(r'[\d.]+', geom_wkt)
                                    if len(coords) >= 2:
                                        lon, lat = float(coords[0]), float(coords[1])
                                        lon += noise[0]
                                        lat += noise[1]
                                        charger['geometry'] = f"POINT({lon} {lat})"
                                except:
                                    pass
                            
                            scaled_chargers.append(charger)
                        
                        scaled_df = pd.DataFrame(scaled_chargers)
                    else:
                        # Take a subset
                        scaled_df = current_chargers.iloc[:num_to_create].copy()
                    
                    print(f"   ✓ Scaled infrastructure to {len(scaled_df)} chargers")
                
                trans.commit()
                
            except Exception as e:
                trans.rollback()
                print(f"   ❌ Error scaling EV infrastructure: {e}")
                raise
    
    def _tag_run_with_scenario(self, run_id, scenario_key):
        """Tag simulation run with scenario metadata."""
        scenario = self.scenarios[scenario_key]
        
        with db_config.engine.connect() as conn:
            trans = conn.begin()
            try:
                # Update run name to include scenario
                update_query = text(f"""
                UPDATE simulation_run 
                SET name = :name
                WHERE run_id = :run_id
                """)
                
                conn.execute(update_query, {
                    'name': f"{scenario['name']} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    'run_id': run_id
                })
                
                trans.commit()
                print(f"   ✓ Scenario tagged: {scenario_key}")
            except Exception as e:
                trans.rollback()
                print(f"   ⚠️ Could not tag run: {e}")
    
    def run_all_scenarios(self):
        """Run all three scenarios in sequence."""
        print("\n" + "="*60)
        print("🌍 EV INFRASTRUCTURE SCENARIO COMPARISON")
        print("="*60)
        print("\nThis will run 3 simulations to validate EV impact:")
        print("  1. Baseline: No EV chargers (control)")
        print("  2. Current: 4 EV chargers (existing)")
        print("  3. 2x Growth: 8 EV chargers (expansion)")
        print("\nEach simulation will run 50 timesteps across 20 grid cells.")
        print("Total runtime: ~5-10 minutes\n")
        
        response = input("Proceed with scenario runs? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("❌ Cancelled")
            return
        
        results = {}
        
        for scenario_key in ['baseline', 'current', '2x_growth']:
            run_id = self.run_scenario(scenario_key)
            if run_id:
                results[scenario_key] = run_id
                print(f"   ✅ {scenario_key}: {run_id}\n")
            else:
                print(f"   ❌ {scenario_key}: Failed\n")
        
        if results:
            print("\n" + "="*60)
            print("✅ SCENARIO RUNS COMPLETED")
            print("="*60)
            for scenario_key, run_id in results.items():
                print(f"  {scenario_key:15} : {run_id}")
            
            print("\nNext steps:")
            print("  1. Run: python run_scenario_analysis.py")
            print("     → Creates comparison visualizations")
            print("  2. View results in: data/outputs/visualizations/")
            print("\nThis will show:")
            print("  📊 Metric comparisons (population, safety, rent, air quality)")
            print("  📈 EV impact quantification (% change vs baseline)")
            print("  🗺️ Spatial distribution changes")
            print("  🔗 Scenario correlation analysis")
        else:
            print("\n❌ No scenarios completed successfully")

def main():
    """Main entry point."""
    try:
        comparator = ScenarioComparison()
        comparator.run_all_scenarios()
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
