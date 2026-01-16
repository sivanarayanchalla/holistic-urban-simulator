#!/usr/bin/env python3
"""
Multi-City Simulation Runner
Runs simulations for multiple German cities (Leipzig, Berlin, Munich)
and enables multi-city comparison analysis.
"""
import sys
from pathlib import Path
import subprocess
import time
import pandas as pd
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from database.db_config import db_config
from sqlalchemy import text

class MultiCitySimulator:
    """Run simulations across multiple German cities."""
    
    CITIES = {
        'leipzig': 'Leipzig, Germany',
        'berlin': 'Berlin, Germany',
        'munich': 'Munich, Germany',
    }
    
    def __init__(self):
        self.results = {}
    
    def run_city_simulation(self, city_key):
        """Run simulation for a specific city."""
        city_name = self.CITIES.get(city_key, city_key)
        
        print(f"\n{'='*70}")
        print(f"SIMULATING: {city_name}")
        print(f"{'='*70}")
        
        try:
            # Update simulation config for city
            print(f"\n[*] Configuring simulation for {city_name}...")
            self._configure_city_simulation(city_key, city_name)
            
            # Run simulation
            print(f"[*] Starting simulation for {city_name}...\n")
            result = subprocess.run(
                [sys.executable, 'run_simulation.py'],
                cwd=Path(__file__).parent.parent.parent,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Check result
            if result.returncode == 0:
                print(result.stdout)
                print(f"\n✅ Simulation completed for {city_name}")
                
                # Extract run ID from output
                run_id = self._extract_run_id(result.stdout)
                self.results[city_key] = {
                    'status': 'success',
                    'run_id': run_id,
                    'timestamp': datetime.now()
                }
                return True
            else:
                print(result.stderr)
                print(f"\n❌ Simulation failed for {city_name}")
                self.results[city_key] = {
                    'status': 'failed',
                    'error': result.stderr,
                    'timestamp': datetime.now()
                }
                return False
                
        except subprocess.TimeoutExpired:
            print(f"❌ Simulation timeout for {city_name}")
            self.results[city_key] = {
                'status': 'timeout',
                'timestamp': datetime.now()
            }
            return False
        except Exception as e:
            print(f"❌ Error running simulation for {city_name}: {e}")
            self.results[city_key] = {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now()
            }
            return False
    
    def _configure_city_simulation(self, city_key, city_name):
        """Configure simulation for specific city."""
        try:
            with db_config.engine.connect() as conn:
                # This updates the default city for the next simulation run
                # The simulation engine will use this to set city_name in simulation_run table
                query = text(f"""
                    INSERT INTO config (key, value) 
                    VALUES ('default_city', '{city_key}')
                    ON CONFLICT (key) DO UPDATE SET value = '{city_key}'
                """)
                try:
                    conn.execute(query)
                    conn.commit()
                except:
                    pass  # Table might not exist, simulation will handle it
                
        except Exception as e:
            print(f"⚠️  Could not update config: {e}")
    
    def _extract_run_id(self, output_str):
        """Extract run ID from simulation output."""
        try:
            for line in output_str.split('\n'):
                if 'Run ID:' in line or 'run_id' in line.lower():
                    parts = line.split(':')
                    if len(parts) > 1:
                        return parts[-1].strip().split()[0]
        except:
            pass
        return None
    
    def run_all_cities(self):
        """Run simulations for all cities."""
        print(f"\n{'='*70}")
        print(f"MULTI-CITY SIMULATION SUITE")
        print(f"Cities: {', '.join(self.CITIES.values())}")
        print(f"{'='*70}")
        
        start_time = time.time()
        successful = 0
        
        for city_key in self.CITIES.keys():
            if self.run_city_simulation(city_key):
                successful += 1
            time.sleep(2)  # Rate limiting between runs
        
        elapsed = time.time() - start_time
        
        # Print summary
        self._print_summary(successful, elapsed)
        
        return successful == len(self.CITIES)
    
    def _print_summary(self, successful, elapsed):
        """Print summary of simulation results."""
        print(f"\n{'='*70}")
        print(f"SIMULATION SUMMARY")
        print(f"{'='*70}")
        
        print(f"\nResults:")
        for city_key, result in self.results.items():
            city_name = self.CITIES[city_key]
            status = result.get('status', 'unknown').upper()
            
            if status == 'SUCCESS':
                symbol = '✅'
                run_id = result.get('run_id', 'unknown')
                print(f"  {symbol} {city_name}: {status} (Run: {run_id[:8]}...)")
            else:
                symbol = '❌'
                print(f"  {symbol} {city_name}: {status}")
        
        print(f"\nStatistics:")
        print(f"  Total cities: {len(self.CITIES)}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {len(self.CITIES) - successful}")
        print(f"  Total time: {elapsed:.1f} seconds")
        print(f"  Average per city: {elapsed/len(self.CITIES):.1f} seconds")
        
        print(f"\nNext steps:")
        print(f"  1. Run: python analyze_multi_city.py")
        print(f"  2. View comparisons in: data/outputs/visualizations/")
        print(f"\n{'='*70}\n")

def main():
    """Run multi-city simulations."""
    simulator = MultiCitySimulator()
    success = simulator.run_all_cities()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
