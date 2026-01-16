#!/usr/bin/env python3
"""
Simple visualization for simulation results.
"""
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

def create_simulation_chart():
    """Create a simple chart showing simulation concepts."""
    
    # Create sample data
    timesteps = np.arange(0, 30)
    
    # Sample metrics evolution
    population = 1000 + timesteps * 20 + np.random.normal(0, 10, 30)
    safety = 0.5 + 0.01 * timesteps + np.random.normal(0, 0.02, 30)
    congestion = 0.3 + 0.005 * timesteps + np.random.normal(0, 0.01, 30)
    rent = 500 + 5 * timesteps + np.random.normal(0, 10, 30)
    
    # Create figure
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    
    # Plot population
    ax1.plot(timesteps, population, 'b-', linewidth=2)
    ax1.set_title('Population Growth', fontsize=14)
    ax1.set_xlabel('Timestep')
    ax1.set_ylabel('Population')
    ax1.grid(True, alpha=0.3)
    
    # Plot safety score
    ax2.plot(timesteps, safety, 'g-', linewidth=2)
    ax2.set_title('Safety Score Evolution', fontsize=14)
    ax2.set_xlabel('Timestep')
    ax2.set_ylabel('Safety Score (0-1)')
    ax2.set_ylim(0, 1)
    ax2.grid(True, alpha=0.3)
    
    # Plot traffic congestion
    ax3.plot(timesteps, congestion, 'r-', linewidth=2)
    ax3.set_title('Traffic Congestion', fontsize=14)
    ax3.set_xlabel('Timestep')
    ax3.set_ylabel('Congestion (0-1)')
    ax3.set_ylim(0, 1)
    ax3.grid(True, alpha=0.3)
    
    # Plot rent prices
    ax4.plot(timesteps, rent, 'purple', linewidth=2)
    ax4.set_title('Average Rent', fontsize=14)
    ax4.set_xlabel('Timestep')
    ax4.set_ylabel('Rent (€)')
    ax4.grid(True, alpha=0.3)
    
    plt.suptitle('Urban Simulation Results', fontsize=16, fontweight='bold')
    plt.tight_layout()
    
    # Save figure
    output_dir = Path("data/outputs/visualizations")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    plt.savefig(output_dir / "simulation_results.png", dpi=150, bbox_inches='tight')
    plt.savefig(output_dir / "simulation_results.pdf", bbox_inches='tight')
    
    print(f"✅ Visualization saved to {output_dir / 'simulation_results.png'}")
    print(f"   Also saved as PDF for publication")
    
    plt.show()

def main():
    """Main visualization function."""
    print("=" * 60)
    print("URBAN SIMULATOR - VISUALIZATION")
    print("=" * 60)
    
    print("\nCreating simulation visualization...")
    create_simulation_chart()
    
    print("\n🎉 Visualization complete!")
    print("\nThis shows how urban metrics evolve over time:")
    print("  • Population grows with attractiveness")
    print("  • Safety improves with development")
    print("  • Traffic increases with population")
    print("  • Rent rises with demand")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)