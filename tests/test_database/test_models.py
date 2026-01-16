"""
Tests for database models.
"""
import pytest
import uuid
from datetime import datetime
from shapely.geometry import Polygon

from src.database.models import (
    SpatialGrid, SimulationRun, SimulationState, 
    LandUse, PointsOfInterest, TransportNetwork
)

def test_spatial_grid_model():
    """Test SpatialGrid model creation."""
    polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    grid = SpatialGrid(
        grid_id="hex_500_001",
        grid_type="hexagon",
        resolution_meters=500,
        geometry=polygon.wkt,
        area_sqkm=0.25,
        centroid=polygon.centroid.wkt
    )
    
    assert grid.grid_id == "hex_500_001"
    assert grid.grid_type == "hexagon"
    assert grid.resolution_meters == 500
    assert grid.area_sqkm == 0.25
    assert "SpatialGrid" in str(grid)

def test_simulation_run_model():
    """Test SimulationRun model creation."""
    run = SimulationRun(
        name="Test Simulation",
        description="A test simulation run",
        city_name="Leipzig",
        total_timesteps=100,
        config={"param1": "value1", "param2": 42}
    )
    
    assert run.name == "Test Simulation"
    assert run.city_name == "Leipzig"
    assert run.total_timesteps == 100
    assert run.config["param1"] == "value1"
    assert run.status == "created"
    assert run.created_at is not None

def test_simulation_state_model():
    """Test SimulationState model creation."""
    state = SimulationState(
        run_id=uuid.uuid4(),
        timestep=0,
        grid_id="hex_500_001",
        population=1000,
        traffic_congestion=0.3,
        safety_score=0.8,
        avg_rent_euro=500.0,
        displacement_risk=0.2
    )
    
    assert state.timestep == 0
    assert state.grid_id == "hex_500_001"
    assert state.population == 1000
    assert state.traffic_congestion == 0.3
    assert state.safety_score == 0.8
    assert state.avg_rent_euro == 500.0
    assert state.displacement_risk == 0.2

def test_land_use_model():
    """Test LandUse model creation."""
    polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    land_use = LandUse(
        source="OSM",
        category="residential",
        geometry=polygon.wkt,
        area_sqkm=1.0,
        properties={"building": "apartments", "height": 5}
    )
    
    assert land_use.source == "OSM"
    assert land_use.category == "residential"
    assert land_use.area_sqkm == 1.0
    assert land_use.properties["building"] == "apartments"

def test_points_of_interest_model():
    """Test PointsOfInterest model creation."""
    from shapely.geometry import Point
    
    point = Point(12.37, 51.34)
    poi = PointsOfInterest(
        poi_type="restaurant",
        name="Test Restaurant",
        geometry=point.wkt,
        source="OSM",
        properties={"cuisine": "italian", "capacity": 50}
    )
    
    assert poi.poi_type == "restaurant"
    assert poi.name == "Test Restaurant"
    assert poi.source == "OSM"
    assert poi.properties["cuisine"] == "italian"

def test_transport_network_model():
    """Test TransportNetwork model creation."""
    from shapely.geometry import LineString
    
    line = LineString([(0, 0), (1, 1), (2, 0)])
    transport = TransportNetwork(
        network_type="road",
        geometry=line.wkt,
        length_meters=100.5,
        properties={"name": "Main Street", "lanes": 2}
    )
    
    assert transport.network_type == "road"
    assert transport.length_meters == 100.5
    assert transport.properties["name"] == "Main Street"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])