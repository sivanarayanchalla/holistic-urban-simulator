#!/usr/bin/env python3
"""
Main simulation engine for the Urban Simulator.
"""
import sys
from pathlib import Path

# Fix import paths
sys.path.append(str(Path(__file__).parent.parent))

import random
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid
import json

try:
    # Try relative import first
    from ..database.db_config import db_config
    from ..database.utils import DatabaseUtils
    from ..database.models import SimulationRun, SimulationState, SpatialGrid
except ImportError:
    # Fallback to absolute import
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from src.database.db_config import db_config
    from src.database.utils import DatabaseUtils
    from src.database.models import SimulationRun, SimulationState, SpatialGrid

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Polygon, shape
from sqlalchemy.orm import Session
from sqlalchemy import text

class UrbanCell:
    """Represents a spatial grid cell in the urban simulation."""
    
    def __init__(self, cell_id, grid_id, geometry, initial_state=None):
        self.cell_id = cell_id
        self.grid_id = grid_id
        self.geometry = geometry
        
        # Initialize state
        self.state = initial_state or {
            'population': 1000,
            'population_density': 0.0,
            'traffic_congestion': 0.3,
            'safety_score': 0.5,
            'commercial_vitality': 0.0,
            'avg_rent_euro': 500.0,
            'displacement_risk': 0.0,
            'green_space_ratio': 0.0,
            'employment': 500,
            'unemployment_rate': 0.05,
            'housing_units': 400,
            'vacancy_rate': 0.02,
            'public_transit_accessibility': 0.0,
            'air_quality_index': 50.0,
            'social_cohesion_index': 0.5,
            'chargers_count': 0,
            'ev_capacity_kw': 0.0,
            'charger_density_per_sqkm': 0.0,
            'charger_types': {},
            'avg_charger_capacity_kw': 0.0
        }
        
        # Calculate initial density if area is known
        self.area_sqkm = self.calculate_area()
        if self.area_sqkm > 0:
            self.state['population_density'] = self.state['population'] / self.area_sqkm
        
        # Track changes
        self.state_history = []
    
    def calculate_area(self):
        """Calculate cell area in square kilometers."""
        try:
            if hasattr(self.geometry, 'area'):
                # Convert from square degrees to square km (approximate)
                return self.geometry.area * 111.32 * 111.32
        except:
            pass
        return 1.0  # Default area
    
    def step(self, neighbors, modules):
        """Execute one simulation step for this cell."""
        # Apply module rules
        for module in modules:
            module.apply_cell_rules(self, neighbors)
        
        # Record state
        return {
            'timestep': None,  # Will be set by model
            'state': self.state.copy()
        }
    
    def get_state_for_db(self, timestep):
        """Prepare state for database storage."""
        # Convert geometry to WKT for PostgreSQL
        geometry_wkt = None
        try:
            if hasattr(self.geometry, 'wkt'):
                geometry_wkt = self.geometry.wkt
            else:
                # Fallback: create simple WKT
                geometry_wkt = "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))"
        except:
            geometry_wkt = "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))"
        
        return {
            'grid_id': self.grid_id,
            'geometry': geometry_wkt,  # Use WKT string instead of Polygon object
            'timestep': timestep,
            'population': self.state.get('population', 0),
            'traffic_congestion': self.state.get('traffic_congestion', 0.0),
            'safety_score': self.state.get('safety_score', 0.5),
            'commercial_vitality': self.state.get('commercial_vitality', 0.0),
            'avg_rent_euro': self.state.get('avg_rent_euro', 500.0),
            'displacement_risk': self.state.get('displacement_risk', 0.0),
            'population_density': self.state.get('population_density', 0.0),
            'employment': self.state.get('employment', 0),
            'unemployment_rate': self.state.get('unemployment_rate', 0.05),
            'housing_units': self.state.get('housing_units', 0),
            'vacancy_rate': self.state.get('vacancy_rate', 0.0),
            'public_transit_accessibility': self.state.get('public_transit_accessibility', 0.0),
            'air_quality_index': self.state.get('air_quality_index', 50.0),
            'green_space_ratio': self.state.get('green_space_ratio', 0.0),
            'social_cohesion_index': self.state.get('social_cohesion_index', 0.5),
            'chargers_count': self.state.get('chargers_count', 0),
            'ev_capacity_kw': self.state.get('ev_capacity_kw', 0.0),
            'charger_density_per_sqkm': self.state.get('charger_density_per_sqkm', 0.0),
            'charger_types': self.state.get('charger_types', {}),
            'avg_charger_capacity_kw': self.state.get('avg_charger_capacity_kw', 0.0)
        }

class UrbanModule:
    """Base class for all urban simulation modules."""
    
    def __init__(self, name, config=None):
        self.name = name
        self.config = config or {}
        self.priority = self.config.get('priority', 1)
    
    def initialize(self, model):
        """Initialize module with the simulation model."""
        self.model = model
    
    def apply_cell_rules(self, cell, neighbors):
        """Apply module rules to a specific cell."""
        pass
    
    def calculate_neighbor_influence(self, cell, neighbors, metric):
        """Calculate influence from neighboring cells."""
        if not neighbors:
            return cell.state.get(metric, 0)
        
        total_influence = 0
        total_weight = 0
        
        for neighbor in neighbors:
            if hasattr(neighbor, 'state') and metric in neighbor.state:
                # Simple average for now
                total_influence += neighbor.state[metric]
                total_weight += 1
        
        return total_influence / total_weight if total_weight > 0 else 0

class PopulationModule(UrbanModule):
    """Handles population dynamics."""
    
    def __init__(self):
        super().__init__("Population", {"priority": 1})
    
    def apply_cell_rules(self, cell, neighbors):
        """Update population based on various factors."""
        # Base values
        current_pop = cell.state.get('population', 1000)
        safety = cell.state.get('safety_score', 0.5)
        rent = cell.state.get('avg_rent_euro', 500)
        congestion = cell.state.get('traffic_congestion', 0.3)
        
        # Calculate attractiveness
        safety_factor = safety * 100  # 0-100 scale
        rent_factor = max(0, 1 - (rent / 2000)) * 100  # Cheaper rent is better
        congestion_factor = (1 - congestion) * 50  # Less congestion is better
        
        attractiveness = (safety_factor * 0.4 + 
                         rent_factor * 0.3 + 
                         congestion_factor * 0.3)
        
        # Add EV attractiveness bonus if available
        ev_bonus = cell.state.get('_ev_attractiveness_bonus', 0.0)
        attractiveness = attractiveness * (1 + ev_bonus)
        
        # Migration based on attractiveness
        migration_rate = (attractiveness - 50) / 100  # -0.5 to +0.5
        
        # Natural growth (0.5% per timestep)
        natural_growth = current_pop * 0.005
        
        # Total change
        population_change = (current_pop * migration_rate * 0.1) + natural_growth
        
        # Apply with limits
        new_population = max(100, current_pop + population_change)
        cell.state['population'] = new_population
        
        # Update density
        if hasattr(cell, 'area_sqkm') and cell.area_sqkm > 0:
            cell.state['population_density'] = new_population / cell.area_sqkm

class TransportationModule(UrbanModule):
    """Handles transportation and traffic."""
    
    def __init__(self):
        super().__init__("Transportation", {"priority": 2})
    
    def apply_cell_rules(self, cell, neighbors):
        """Update traffic congestion based on population and network."""
        population = cell.state.get('population', 1000)
        current_congestion = cell.state.get('traffic_congestion', 0.3)
        
        # Base congestion from population density
        density = cell.state.get('population_density', 0)
        density_factor = min(1.0, density / 10000)
        
        # Influence from neighbors (congestion spreads)
        neighbor_congestion = self.calculate_neighbor_influence(cell, neighbors, 'traffic_congestion')
        
        # Road capacity (simplified)
        road_capacity = 0.5  # Default capacity
        
        # Calculate new congestion
        demand = density_factor * 0.7 + neighbor_congestion * 0.3
        capacity_utilization = demand / max(road_capacity, 0.1)
        
        # Smooth the change
        new_congestion = current_congestion * 0.8 + min(1.0, capacity_utilization) * 0.2
        cell.state['traffic_congestion'] = max(0.0, min(1.0, new_congestion))

class HousingMarketModule(UrbanModule):
    """Handles housing market dynamics."""
    
    def __init__(self):
        super().__init__("Housing Market", {"priority": 3})
    
    def apply_cell_rules(self, cell, neighbors):
        """Update housing market metrics."""
        population = cell.state.get('population', 1000)
        current_rent = cell.state.get('avg_rent_euro', 500)
        safety = cell.state.get('safety_score', 0.5)
        commercial = cell.state.get('commercial_vitality', 0.0)
        congestion = cell.state.get('traffic_congestion', 0.3)
        
        # Demand factors
        safety_factor = safety
        commercial_factor = commercial
        congestion_factor = 1 - congestion
        
        # Calculate demand score
        demand_score = (safety_factor * 0.4 + 
                       commercial_factor * 0.3 + 
                       congestion_factor * 0.3)
        
        # Supply (simplified)
        housing_units = cell.state.get('housing_units', max(400, population / 2.5))
        cell.state['housing_units'] = housing_units
        
        # Price adjustment
        demand_supply_ratio = (population / max(housing_units, 1)) * demand_score
        
        # Rent change (max 2% per timestep)
        rent_change_pct = min(0.02, max(-0.02, (demand_supply_ratio - 1) * 0.05))
        new_rent = current_rent * (1 + rent_change_pct)
        
        cell.state['avg_rent_euro'] = max(300, min(3000, new_rent))
        
        # Update vacancy rate
        occupancy_rate = min(1.0, housing_units / max(population / 2.5, 1))
        cell.state['vacancy_rate'] = max(0.0, 1 - occupancy_rate)
        
        # Calculate displacement risk
        rent_affordability = 1500 / max(new_rent, 500)  # Assuming €1500 is affordable threshold
        cell.state['displacement_risk'] = max(0.0, min(1.0, 1 - rent_affordability))

class SafetyModule(UrbanModule):
    """Handles safety and crime dynamics."""
    
    def __init__(self):
        super().__init__("Safety", {"priority": 4})
    
    def apply_cell_rules(self, cell, neighbors):
        """Update safety score based on various factors."""
        current_safety = cell.state.get('safety_score', 0.5)
        
        # Negative factors
        density = cell.state.get('population_density', 0)
        congestion = cell.state.get('traffic_congestion', 0.3)
        vacancy = cell.state.get('vacancy_rate', 0.02)
        
        # Positive factors
        commercial = cell.state.get('commercial_vitality', 0.0)
        green_space = cell.state.get('green_space_ratio', 0.0)
        
        # Calculate safety change
        negative_impact = (min(1.0, density / 20000) * 0.3 +
                          congestion * 0.3 +
                          vacancy * 0.4)
        
        positive_impact = (commercial * 0.4 +
                          green_space * 0.6)
        
        net_impact = positive_impact - negative_impact
        
        # Influence from neighbors (safety spreads)
        neighbor_safety = self.calculate_neighbor_influence(cell, neighbors, 'safety_score')
        
        # Update safety score
        safety_change = net_impact * 0.5 + (neighbor_safety - current_safety) * 0.5
        new_safety = current_safety + safety_change * 0.1  # Slow change
        
        cell.state['safety_score'] = max(0.0, min(1.0, new_safety))

class CommercialModule(UrbanModule):
    """Handles commercial and business dynamics."""
    
    def __init__(self):
        super().__init__("Commercial", {"priority": 5})
    
    def apply_cell_rules(self, cell, neighbors):
        """Update commercial vitality."""
        current_vitality = cell.state.get('commercial_vitality', 0.0)
        population = cell.state.get('population', 1000)
        safety = cell.state.get('safety_score', 0.5)
        congestion = cell.state.get('traffic_congestion', 0.3)
        
        # Demand from population
        population_demand = min(1.0, population / 5000)
        
        # Accessibility (less congestion helps commerce)
        accessibility = 1 - congestion
        
        # Calculate vitality
        base_vitality = population_demand * accessibility * safety
        
        # Influence from neighbors (commercial clusters)
        neighbor_vitality = self.calculate_neighbor_influence(cell, neighbors, 'commercial_vitality')
        
        # Update
        vitality_change = base_vitality * 0.6 + neighbor_vitality * 0.4
        new_vitality = current_vitality * 0.7 + vitality_change * 0.3
        
        cell.state['commercial_vitality'] = max(0.0, min(1.0, new_vitality))

class EVModule(UrbanModule):
    """Handles EV infrastructure impact on urban metrics."""
    
    def __init__(self):
        super().__init__("EV Infrastructure", {"priority": 0})  # High priority
    
    def apply_cell_rules(self, cell, neighbors):
        """Calculate EV infrastructure impact on urban metrics.
        
        EV infrastructure affects:
        - Air quality: High charger density reduces emissions
        - Population attraction: Modern EV infrastructure attracts residents
        - Property values: EV-ready areas command premium
        - Employment: EV charging network creates jobs
        """
        charger_density = cell.state.get('charger_density_per_sqkm', 0.0)
        ev_capacity_kw = cell.state.get('ev_capacity_kw', 0.0)
        chargers_count = cell.state.get('chargers_count', 0)
        
        if chargers_count == 0:
            # No EV infrastructure - no impact
            return
        
        # === AIR QUALITY IMPROVEMENT ===
        # EV infrastructure reduces emissions
        # Charger density improves air quality: 1 charger/km2 = ~5% AQI improvement
        current_aqi = cell.state.get('air_quality_index', 50.0)
        aqi_improvement = min(15, charger_density * 5)  # Max 15 point improvement
        new_aqi = current_aqi - aqi_improvement
        cell.state['air_quality_index'] = max(0.0, new_aqi)
        
        # === PROPERTY VALUE PREMIUM ===
        # EV infrastructure increases desirability
        # ~€50 per kW of available capacity
        current_rent = cell.state.get('avg_rent_euro', 500.0)
        ev_premium = ev_capacity_kw * 0.05  # €50 per 1000 kW = 5% factor
        new_rent = current_rent * (1 + ev_premium / 100)
        cell.state['avg_rent_euro'] = new_rent
        
        # === POPULATION ATTRACTION ===
        # Modern, sustainable areas attract young professionals and families
        # EV infrastructure is a positive signal
        population = cell.state.get('population', 1000)
        
        # Attractiveness bonus from EV infrastructure
        ev_attractiveness_bonus = min(0.15, charger_density * 0.1)  # Max 15% boost
        
        # This will help population growth in the PopulationModule
        # Store as a factor that other modules can use
        cell.state['_ev_attractiveness_bonus'] = ev_attractiveness_bonus
        
        # === EMPLOYMENT CREATION ===
        # EV charging network requires maintenance and operation
        # Estimate: 1 job per 5 kW of capacity
        current_employment = cell.state.get('employment', 500)
        ev_jobs = max(0, ev_capacity_kw / 5)
        new_employment = current_employment + ev_jobs
        cell.state['employment'] = new_employment
        
        # === SOCIAL COHESION ===
        # Shared EV infrastructure can improve community feeling
        current_cohesion = cell.state.get('social_cohesion_index', 0.5)
        cohesion_boost = min(0.15, chargers_count * 0.03)  # 3% per charger
        new_cohesion = current_cohesion + cohesion_boost * 0.1
        cell.state['social_cohesion_index'] = max(0.0, min(1.0, new_cohesion))
        
        # === PUBLIC TRANSIT ACCESSIBILITY ===
        # EV charging at transit hubs improves multimodal options
        # Assume 30% of chargers are at transit hubs
        transit_hubs = chargers_count * 0.3
        current_transit = cell.state.get('public_transit_accessibility', 0.0)
        transit_boost = min(0.2, transit_hubs * 0.05)
        new_transit = current_transit + transit_boost * 0.05
        cell.state['public_transit_accessibility'] = max(0.0, min(1.0, new_transit))


class PolicyModule(UrbanModule):
    """Models the impact of government policies on urban development."""
    
    def __init__(self, policies=None):
        super().__init__("Policy Intervention", {"priority": 2})
        
        # Define active policies (can be configured per simulation)
        self.policies = policies or {
            'ev_subsidy': {
                'active': True,
                'description': 'Government EV charging infrastructure subsidies',
                'rent_reduction': 0.05,  # 5% rent reduction in subsidized areas
                'population_bonus': 0.10,  # 10% population attraction boost
            },
            'progressive_tax': {
                'active': True,
                'description': 'Progressive property tax on high-rent areas',
                'high_rent_threshold': 1200.0,  # €/month
                'tax_rate': 0.08,  # 8% tax on high-rent properties
                'displacement_risk_increase': 0.15,  # Increases displacement risk
            },
            'green_space_mandate': {
                'active': True,
                'description': 'Zoning requirement for 20% green space',
                'green_space_target': 0.20,  # 20% of cell area
                'air_quality_improvement': 0.10,  # 10% AQI improvement
                'population_bonus': 0.08,  # 8% population attraction
                'safety_improvement': 0.05,  # 5% safety improvement
            },
            'transit_investment': {
                'active': True,
                'description': 'Public transit expansion and improvement',
                'transit_accessibility_boost': 0.20,  # 20 percentage point increase
                'congestion_reduction': 0.15,  # Reduces congestion by 15%
                'population_bonus': 0.12,  # 12% population attraction
            },
            'rent_control': {
                'active': False,
                'description': 'Rent control policy to prevent displacement',
                'max_rent_increase': 0.03,  # 3% annual increase max
                'displacement_risk_reduction': 0.40,  # Reduces displacement by 40%
            }
        }
    
    def apply_cell_rules(self, cell, neighbors):
        """Apply active policies to cell state."""
        
        # === EV SUBSIDY POLICY ===
        if self.policies['ev_subsidy']['active'] and cell.state.get('chargers_count', 0) > 0:
            # Subsidies reduce costs, making living in EV-rich areas attractive
            current_rent = cell.state.get('avg_rent_euro', 500.0)
            reduction = current_rent * self.policies['ev_subsidy']['rent_reduction']
            new_rent = current_rent - reduction
            cell.state['avg_rent_euro'] = new_rent
            
            # Bonus to population in subsidized areas
            cell.state['_policy_population_bonus'] = self.policies['ev_subsidy']['population_bonus']
        
        # === PROGRESSIVE TAX POLICY ===
        if self.policies['progressive_tax']['active']:
            current_rent = cell.state.get('avg_rent_euro', 500.0)
            threshold = self.policies['progressive_tax']['high_rent_threshold']
            
            if current_rent > threshold:
                # Tax high-rent properties
                tax_amount = (current_rent - threshold) * self.policies['progressive_tax']['tax_rate']
                new_rent = current_rent - tax_amount
                cell.state['avg_rent_euro'] = new_rent
                
                # Increases displacement risk in expensive areas
                current_displacement = cell.state.get('displacement_risk', 0.0)
                displacement_increase = self.policies['progressive_tax']['displacement_risk_increase'] * 0.1
                cell.state['displacement_risk'] = min(1.0, current_displacement + displacement_increase)
        
        # === GREEN SPACE MANDATE POLICY ===
        if self.policies['green_space_mandate']['active']:
            current_green = cell.state.get('green_space_ratio', 0.0)
            target_green = self.policies['green_space_mandate']['green_space_target']
            
            # Gradually improve green space
            improvement = (target_green - current_green) * 0.2  # 20% progress per timestep
            new_green = min(target_green, current_green + improvement)
            cell.state['green_space_ratio'] = new_green
            
            # Benefits of green space
            if new_green > 0:
                # Air quality improves
                current_aqi = cell.state.get('air_quality_index', 50.0)
                aqi_improvement = new_green * self.policies['green_space_mandate']['air_quality_improvement'] * 10
                cell.state['air_quality_index'] = min(100.0, current_aqi + aqi_improvement)
                
                # Population attraction bonus
                cell.state['_policy_population_bonus'] = (cell.state.get('_policy_population_bonus', 0.0) + 
                                                         self.policies['green_space_mandate']['population_bonus'])
                
                # Safety improves in greener areas
                current_safety = cell.state.get('safety_score', 0.5)
                safety_boost = new_green * self.policies['green_space_mandate']['safety_improvement']
                cell.state['safety_score'] = min(1.0, current_safety + safety_boost * 0.1)
        
        # === TRANSIT INVESTMENT POLICY ===
        if self.policies['transit_investment']['active']:
            # Improve public transit accessibility
            current_transit = cell.state.get('public_transit_accessibility', 0.0)
            transit_boost = self.policies['transit_investment']['transit_accessibility_boost'] * 0.1
            new_transit = min(1.0, current_transit + transit_boost)
            cell.state['public_transit_accessibility'] = new_transit
            
            # Reduce congestion through multimodal options
            current_congestion = cell.state.get('traffic_congestion', 0.3)
            congestion_reduction = self.policies['transit_investment']['congestion_reduction']
            new_congestion = current_congestion * (1 - congestion_reduction * 0.05)
            cell.state['traffic_congestion'] = max(0.0, new_congestion)
            
            # Population bonus from transit improvements
            cell.state['_policy_population_bonus'] = (cell.state.get('_policy_population_bonus', 0.0) + 
                                                     self.policies['transit_investment']['population_bonus'])
        
        # === RENT CONTROL POLICY ===
        if self.policies['rent_control']['active']:
            # Limit rent increases
            current_rent = cell.state.get('avg_rent_euro', 500.0)
            previous_rent = cell.state.get('_previous_rent', current_rent)
            max_increase = previous_rent * self.policies['rent_control']['max_rent_increase']
            
            if current_rent > previous_rent + max_increase:
                cell.state['avg_rent_euro'] = previous_rent + max_increase
            
            # Reduce displacement risk significantly
            current_displacement = cell.state.get('displacement_risk', 0.0)
            reduction = current_displacement * self.policies['rent_control']['displacement_risk_reduction']
            cell.state['displacement_risk'] = max(0.0, current_displacement - reduction * 0.1)
        
        # Store current rent for next timestep
        cell.state['_previous_rent'] = cell.state.get('avg_rent_euro', 500.0)


class EducationModule(UrbanModule):
    """Models the impact of educational facilities on urban development."""
    
    def __init__(self):
        super().__init__("Education", {"priority": 3})
    
    def apply_cell_rules(self, cell, neighbors):
        """Apply education-related rules to cell state.
        
        Educational infrastructure affects:
        - Population attraction: Families value good schools
        - Property values: School catchments command premium
        - Employment: Education sector jobs
        - Social cohesion: Community-building function
        """
        # Assume education density based on population (schools scale with population)
        population = cell.state.get('population', 1000)
        area_sqkm = cell.area_sqkm
        
        # Estimate schools: ~1 school per 2000 residents
        estimated_schools = max(0, population / 2000)
        school_density = estimated_schools / max(1, area_sqkm)
        
        # === POPULATION ATTRACTION ===
        # Families are attracted to areas with good schools
        # Each school adds ~10% population attractiveness (capped at 0.3)
        school_bonus = min(0.30, estimated_schools * 0.10)
        cell.state['_education_population_bonus'] = school_bonus
        
        # === PROPERTY VALUE PREMIUM ===
        # Properties near schools command premium: ~€100 per school
        current_rent = cell.state.get('avg_rent_euro', 500.0)
        school_premium = estimated_schools * 100  # €100 per school
        new_rent = current_rent + (school_premium / 100)  # Percentage increase
        cell.state['avg_rent_euro'] = new_rent
        
        # === EMPLOYMENT CREATION ===
        # Education sector employs teachers, administrators, support staff
        # Estimate: 10 jobs per school
        current_employment = cell.state.get('employment', 500)
        education_jobs = estimated_schools * 10
        new_employment = current_employment + education_jobs
        cell.state['employment'] = new_employment
        
        # === SOCIAL COHESION ===
        # Schools are community hubs that improve social bonding
        current_cohesion = cell.state.get('social_cohesion_index', 0.5)
        cohesion_boost = min(0.20, estimated_schools * 0.08)  # 8% per school
        new_cohesion = current_cohesion + cohesion_boost * 0.1
        cell.state['social_cohesion_index'] = max(0.0, min(1.0, new_cohesion))


class HealthcareModule(UrbanModule):
    """Models the impact of healthcare facilities on urban development."""
    
    def __init__(self):
        super().__init__("Healthcare", {"priority": 4})
    
    def apply_cell_rules(self, cell, neighbors):
        """Apply healthcare-related rules to cell state.
        
        Healthcare infrastructure affects:
        - Safety/wellness: Health services improve wellbeing
        - Population attraction: Access to healthcare is crucial
        - Property values: Medical hubs attract residents
        - Employment: Healthcare sector jobs
        """
        # Assume healthcare density based on population (hospitals/clinics scale with population)
        population = cell.state.get('population', 1000)
        area_sqkm = cell.area_sqkm
        
        # Estimate healthcare facilities: ~1 major facility per 5000 residents + smaller clinics
        estimated_facilities = max(0, population / 3000)
        healthcare_density = estimated_facilities / max(1, area_sqkm)
        
        # === SAFETY & WELLNESS ===
        # Healthcare access improves public health and feeling of safety
        current_safety = cell.state.get('safety_score', 0.5)
        healthcare_safety_boost = min(0.15, estimated_facilities * 0.05)  # 5% per facility
        new_safety = current_safety + healthcare_safety_boost * 0.1
        cell.state['safety_score'] = min(1.0, new_safety)
        
        # === POPULATION ATTRACTION ===
        # People prioritize healthcare access for their families
        healthcare_bonus = min(0.25, estimated_facilities * 0.08)  # 8% per facility
        cell.state['_healthcare_population_bonus'] = healthcare_bonus
        
        # === PROPERTY VALUE PREMIUM ===
        # Healthcare access increases property desirability: ~€80 per facility
        current_rent = cell.state.get('avg_rent_euro', 500.0)
        healthcare_premium = estimated_facilities * 80  # €80 per facility
        new_rent = current_rent + (healthcare_premium / 100)  # Percentage increase
        cell.state['avg_rent_euro'] = new_rent
        
        # === EMPLOYMENT CREATION ===
        # Healthcare is major employment sector
        # Estimate: 15 jobs per healthcare facility
        current_employment = cell.state.get('employment', 500)
        healthcare_jobs = estimated_facilities * 15
        new_employment = current_employment + healthcare_jobs
        cell.state['employment'] = new_employment
        
        # === SOCIAL COHESION ===
        # Health facilities serve as community anchors
        current_cohesion = cell.state.get('social_cohesion_index', 0.5)
        cohesion_boost = min(0.18, estimated_facilities * 0.06)  # 6% per facility
        new_cohesion = current_cohesion + cohesion_boost * 0.1
        cell.state['social_cohesion_index'] = max(0.0, min(1.0, new_cohesion))


class SpatialEffectsModule(UrbanModule):
    """Models spatial spillover and neighborhood effects."""
    
    def __init__(self):
        super().__init__("Spatial Effects", {"priority": 5})
    
    def apply_cell_rules(self, cell, neighbors):
        """Apply neighborhood spillover effects.
        
        Spatial effects model:
        - Positive spillovers: Improvement spreads to neighbors
        - Negative spillovers: Gentrification/displacement effects
        - Agglomeration: Clustering of similar economic activity
        - Distance decay: Effects diminish with distance
        """
        
        if not neighbors or len(neighbors) == 0:
            return  # No neighbors to interact with
        
        # === POSITIVE SPILLOVER: PROSPERITY ===
        # High-prosperity areas attract development to neighbors
        current_employment = cell.state.get('employment', 500)
        current_rent = cell.state.get('avg_rent_euro', 500.0)
        
        if current_employment > 600 and current_rent > 600:  # Prosperous cell
            for neighbor in neighbors[:4]:  # Consider closest neighbors (Moore neighborhood)
                if neighbor is None:
                    continue
                
                # Spillover effect: neighbor gains some prosperity
                spillover_employment = current_employment * 0.05  # 5% spillover
                neighbor.state['employment'] = neighbor.state.get('employment', 500) + spillover_employment
                
                spillover_rent = current_rent * 0.03  # 3% rent spillover
                neighbor.state['avg_rent_euro'] = neighbor.state.get('avg_rent_euro', 500.0) + spillover_rent
        
        # === GENTRIFICATION & DISPLACEMENT ===
        # As neighborhoods improve, rent increases can displace vulnerable populations
        if current_rent > 800:  # High-rent area
            for neighbor in neighbors:
                if neighbor is None:
                    continue
                
                # Risk of gentrification spillover
                neighbor_displacement = neighbor.state.get('displacement_risk', 0.0)
                gentrification_pressure = 0.05 * (current_rent - 800) / 500  # Pressure from neighboring high rent
                new_displacement = min(1.0, neighbor_displacement + gentrification_pressure * 0.1)
                neighbor.state['displacement_risk'] = new_displacement
                
                # Some population turnover expected
                if new_displacement > 0.3:
                    # Vulnerable populations relocate
                    population_loss = neighbor.state.get('population', 1000) * new_displacement * 0.02
                    neighbor.state['population'] = max(500, neighbor.state.get('population', 1000) - population_loss)
        
        # === AIR QUALITY SPILLOVER ===
        # Clean air spreads to neighbors; pollution spreads
        current_aqi = cell.state.get('air_quality_index', 50.0)
        
        for neighbor in neighbors:
            if neighbor is None:
                continue
            
            neighbor_aqi = neighbor.state.get('air_quality_index', 50.0)
            aqi_diff = current_aqi - neighbor_aqi
            
            # Air moves: converge toward average
            if abs(aqi_diff) > 5:
                spillover_aqi = aqi_diff * 0.15  # 15% of difference spreads
                neighbor.state['air_quality_index'] = neighbor_aqi + spillover_aqi
                neighbor.state['air_quality_index'] = max(0.0, min(100.0, neighbor.state['air_quality_index']))
        
        # === SAFETY SPILLOVER ===
        # Crime and safety can spread between areas
        current_safety = cell.state.get('safety_score', 0.5)
        
        for neighbor in neighbors:
            if neighbor is None:
                continue
            
            neighbor_safety = neighbor.state.get('safety_score', 0.5)
            safety_diff = current_safety - neighbor_safety
            
            # Safety converges between neighbors
            if abs(safety_diff) > 0.1:
                spillover_safety = safety_diff * 0.1  # 10% of difference spreads
                neighbor.state['safety_score'] = neighbor_safety + spillover_safety
                neighbor.state['safety_score'] = max(0.0, min(1.0, neighbor.state['safety_score']))
        
        # === POPULATION ATTRACTION SPILLOVER ===
        # Vibrant neighborhoods attract people to nearby areas
        current_vitality = cell.state.get('commercial_vitality', 0.0)
        current_population = cell.state.get('population', 1000)
        
        if current_vitality > 0.7 and current_population > 2000:
            for neighbor in neighbors:
                if neighbor is None:
                    continue
                
                # Spillover population attraction
                spillover_population = current_population * 0.02  # 2% spillover
                neighbor_pop = neighbor.state.get('population', 1000)
                neighbor.state['population'] = neighbor_pop + spillover_population
        
        # === SOCIAL COHESION AGGLOMERATION ===
        # Strong communities build on neighbors' strength (agglomeration effect)
        current_cohesion = cell.state.get('social_cohesion_index', 0.5)
        
        if current_cohesion > 0.6:
            # Strong social fabric attracts like-minded neighbors
            for neighbor in neighbors:
                if neighbor is None:
                    continue
                
                neighbor_cohesion = neighbor.state.get('social_cohesion_index', 0.5)
                
                # Positive reinforcement - high cohesion areas boost neighbors
                cohesion_spillover = (current_cohesion - neighbor_cohesion) * 0.08
                neighbor.state['social_cohesion_index'] = min(1.0, neighbor_cohesion + cohesion_spillover * 0.1)
        
        # === CONGESTION SPILLOVER ===
        # Traffic congestion spreads to adjacent areas
        current_congestion = cell.state.get('traffic_congestion', 0.3)
        
        for neighbor in neighbors:
            if neighbor is None:
                continue
            
            neighbor_congestion = neighbor.state.get('traffic_congestion', 0.3)
            congestion_diff = current_congestion - neighbor_congestion
            
            # Traffic patterns influence neighbors
            if congestion_diff > 0.1:
                spillover_congestion = congestion_diff * 0.12  # 12% spillover
                neighbor.state['traffic_congestion'] = min(1.0, neighbor_congestion + spillover_congestion)

class UrbanModel:
    """Main urban simulation model."""
    
    def __init__(self, grid_cells, modules=None, run_id=None, city_name='Leipzig'):
        self.run_id = run_id or str(uuid.uuid4())
        self.grid_cells = grid_cells
        self.current_timestep = 0
        self.city_name = city_name
        
        # Create grid structure
        grid_size = int(np.ceil(np.sqrt(len(grid_cells))))
        self.grid_size = grid_size
        
        # Initialize modules
        self.modules = modules or self.get_default_modules()
        for module in self.modules:
            module.initialize(self)
        
        # Create cell agents
        self.cells = {}
        self.grid_positions = {}
        
        for idx, cell_data in enumerate(grid_cells):
            # Create cell
            cell = UrbanCell(
                cell_id=idx,
                grid_id=cell_data['grid_id'],
                geometry=cell_data['geometry'],
                initial_state=cell_data.get('initial_state', {})
            )
            
            # Store cell
            self.cells[cell_data['grid_id']] = cell
            
            # Store grid position
            x = idx % grid_size
            y = idx // grid_size
            self.grid_positions[cell_data['grid_id']] = (x, y)
        
        print(f"✅ Urban Model initialized")
        print(f"   Cells: {len(grid_cells)}")
        print(f"   Modules: {len(self.modules)}")
        print(f"   Run ID: {self.run_id}")
    
    def get_default_modules(self):
        """Get default set of urban modules."""
        return [
            EVModule(),  # Priority 0 - EV infrastructure
            PolicyModule(),  # Priority 2 - Government policies
            EducationModule(),  # Priority 3 - Schools and education
            HealthcareModule(),  # Priority 4 - Hospitals and healthcare
            SpatialEffectsModule(),  # Priority 5 - Neighborhood spillovers
            PopulationModule(),
            TransportationModule(),
            HousingMarketModule(),
            SafetyModule(),
            CommercialModule()
        ]
    
    def get_neighbors(self, cell_id):
        """Get neighboring cells for a given cell."""
        if cell_id not in self.grid_positions:
            return []
        
        x, y = self.grid_positions[cell_id]
        neighbors = []
        
        # Get Moore neighborhood (8 directions)
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue  # Skip self
                
                # Find cell at this position
                for other_cell_id, (ox, oy) in self.grid_positions.items():
                    if ox == x + dx and oy == y + dy:
                        neighbors.append(self.cells[other_cell_id])
                        break
        
        return neighbors
    
    def load_ev_metrics_from_db(self):
        """Load EV infrastructure metrics from database into cells."""
        print("\n📊 Loading EV infrastructure metrics from database...")
        
        try:
            with db_config.get_session() as session:
                # Query EV metrics for all grid cells
                result = session.execute(
                    text("""
                        SELECT sg.grid_id, COALESCE(COUNT(ev.id), 0) as chargers_count,
                               COALESCE(SUM(ev.capacity_kw), 0) as ev_capacity_kw, 
                               COALESCE(COUNT(ev.id) / NULLIF(ST_Area(sg.geometry) / 1000000.0, 0), 0) as charger_density_per_sqkm,
                               COALESCE(AVG(ev.capacity_kw), 0) as avg_charger_capacity_kw
                        FROM spatial_grid sg
                        LEFT JOIN ev_infrastructure ev ON ST_Contains(sg.geometry, ev.geometry)
                        GROUP BY sg.grid_id, sg.geometry
                    """)
                )
                
                ev_metrics_loaded = 0
                for row in result:
                    grid_id = row[0]
                    chargers_count = int(row[1] or 0)
                    ev_capacity_kw = float(row[2] or 0.0)
                    charger_density = float(row[3] or 0.0)
                    avg_capacity = float(row[4] or 0.0)
                    
                    if grid_id in self.cells:
                        cell = self.cells[grid_id]
                        cell.state['chargers_count'] = chargers_count
                        cell.state['ev_capacity_kw'] = ev_capacity_kw
                        cell.state['charger_density_per_sqkm'] = charger_density
                        cell.state['charger_types'] = {}  # Simplified for now
                        cell.state['avg_charger_capacity_kw'] = avg_capacity
                        
                        if chargers_count > 0:
                            ev_metrics_loaded += 1
                
                print(f"✅ Loaded EV metrics: {ev_metrics_loaded} cells with chargers")
                return ev_metrics_loaded
                
        except Exception as e:
            print(f"⚠️  Could not load EV metrics from database: {e}")
            return 0
    
    def step(self):
        """Execute one simulation step."""
        self.current_timestep += 1
        
        # Process all cells in random order
        cell_ids = list(self.cells.keys())
        random.shuffle(cell_ids)
        
        for cell_id in cell_ids:
            cell = self.cells[cell_id]
            neighbors = self.get_neighbors(cell_id)
            cell.step(neighbors, self.modules)
        
        # Print progress
        if self.current_timestep % 20 == 0:
            print(f"  Timestep {self.current_timestep} completed")
    
    def save_state_to_db(self):
        """Save current simulation state to database."""
        try:
            states = []
            for cell in self.cells.values():
                state_data = cell.get_state_for_db(self.current_timestep)
                state_data['run_id'] = self.run_id
                states.append(state_data)
            
            # Save to database
            if states:
                DatabaseUtils.save_simulation_state(
                    run_id=self.run_id,
                    timestep=self.current_timestep,
                    grid_states=states
                )
                print(f"✅ Saved {len(states)} simulation states for timestep {self.current_timestep}")
                
        except Exception as e:
            print(f"  ❌ Error saving state: {e}")
    
    def run_simulation(self, steps=50):
        """Run simulation for specified number of steps."""
        print(f"\n▶️  Running simulation for {steps} steps...")
        
        start_time = datetime.now()
        
        # Load EV metrics from database
        self.load_ev_metrics_from_db()
        
        # Create simulation run record
        try:
            with db_config.get_session() as session:
                run = SimulationRun(
                    run_id=self.run_id,
                    name=f"Urban Simulation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    description=f"Test simulation with {steps} steps",
                    city_name=self.city_name,
                    total_timesteps=steps,
                    config={
                        'modules': [m.name for m in self.modules],
                        'grid_cells': len(self.grid_cells),
                        'start_time': start_time.isoformat()
                    }
                )
                session.add(run)
                session.commit()
                print(f"[OK] Created simulation run record: {self.run_id}")
        except Exception as e:
            print(f"  [!] Could not create run record: {e}")
        
        # Run steps
        for step in range(steps):
            self.step()
            
            # Save state at specific intervals and at the end
            if (step + 1) % 10 == 0 or (step + 1) == steps:
                self.save_state_to_db()
        
        # Update run status
        try:
            with db_config.get_session() as session:
                run = session.query(SimulationRun).filter(SimulationRun.run_id == self.run_id).first()
                if run:
                    run.status = 'completed'
                    run.completed_at = datetime.now()
                    session.commit()
                    print(f"✅ Updated run status to completed")
        except Exception as e:
            print(f"  ⚠️  Could not update run status: {e}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n✅ Simulation completed in {duration:.1f} seconds")
        print(f"   Total timesteps: {self.current_timestep}")
        print(f"   Run ID: {self.run_id}")
        
        return self.run_id

class SimulationManager:
    """Manages simulation runs and configurations."""
    
    @staticmethod
    def get_grid_cells_for_simulation(limit=50):
        """Get grid cells for simulation from database."""
        print(f"Loading grid cells for simulation...")
        
        try:
            with db_config.get_session() as session:
                # Query spatial grid cells
                cells = session.query(SpatialGrid).limit(limit).all()
            
            grid_cells = []
            for cell in cells:
                try:
                    # Convert database geometry to Shapely geometry
                    geometry = to_shape(cell.geometry)
                    
                    # Create random initial state based on cell position
                    import random
                    initial_state = {
                        'population': random.randint(500, 5000),
                        'traffic_congestion': random.random() * 0.5,
                        'safety_score': 0.3 + random.random() * 0.4,
                        'commercial_vitality': random.random() * 0.5,
                        'avg_rent_euro': 300 + random.random() * 1200,
                        'displacement_risk': random.random() * 0.3,
                        'green_space_ratio': random.random() * 0.4,
                        'employment': random.randint(200, 2000),
                        'unemployment_rate': 0.03 + random.random() * 0.07
                    }
                    
                    grid_cells.append({
                        'grid_id': cell.grid_id,
                        'geometry': geometry,
                        'initial_state': initial_state
                    })
                    
                except Exception as e:
                    print(f"  ⚠️  Skipping cell {cell.grid_id}: {str(e)[:100]}...")
                    continue
            
            print(f"  ✅ Loaded {len(grid_cells)} grid cells")
            return grid_cells
            
        except Exception as e:
            print(f"  ❌ Error loading grid cells: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def run_test_simulation(steps=50, grid_limit=20, city='Leipzig'):
        """Run a complete test simulation for a city."""
        print("=" * 60)
        print(f"URBAN SIMULATION FOR {city}")
        print("=" * 60)
        
        # Get grid cells
        grid_cells = SimulationManager.get_grid_cells_for_simulation(limit=grid_limit)
        
        if not grid_cells:
            print("[ERROR] No grid cells available for simulation")
            return None
        
        # Create and run model
        model = UrbanModel(grid_cells=grid_cells, city_name=city)
        run_id = model.run_simulation(steps=steps)
        
        return run_id

def main(city='Leipzig', steps=50, grid_limit=20, non_interactive=False):
    """Main execution function with city support."""
    print("Urban Simulator - Core Engine")
    print("=" * 50)
    
    print(f"\nThis will run an urban simulation for {city} with:")
    print("  - Multiple interconnected urban modules")
    print(f"  - {city} spatial grid")
    print("  - Dynamic simulation of urban systems")
    
    # Non-interactive mode (for batch runs)
    if non_interactive:
        response = 'yes'
    else:
        response = input("\nRun simulation? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("Simulation cancelled.")
        return None
    
    # Run test simulation
    run_id = SimulationManager.run_test_simulation(steps=steps, grid_limit=grid_limit, city=city)
    
    if run_id:
        print(f"\n[OK] Simulation completed successfully!")
        print(f"\nRun ID: {run_id}")
        print(f"City: {city}")
        print("\nNext steps:")
        print("1. Visualize results: python src/visualization/create_dashboard.py")
        print("2. Analyze data: Check simulation_state table in database")
        print("3. Modify modules: Edit src/core_engine/simulation_engine.py")
    else:
        print("\n[!] Simulation failed.")
    
    return run_id

if __name__ == "__main__":
    run_id = main()
    sys.exit(0 if run_id else 1)