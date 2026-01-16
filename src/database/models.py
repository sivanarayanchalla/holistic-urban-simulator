"""
SQLAlchemy ORM models for the Urban Simulator.
"""
from datetime import datetime
from typing import Dict, Any, Optional
import uuid
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, Text, ForeignKey, JSON, CheckConstraint,
    UniqueConstraint, Index, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from geoalchemy2 import Geometry

Base = declarative_base()

class SpatialGrid(Base):
    """Hexagonal grid for spatial aggregation."""
    __tablename__ = 'spatial_grid'
    
    grid_id = Column(String(50), primary_key=True)
    grid_type = Column(String(20), nullable=False)
    resolution_meters = Column(Integer, nullable=False)
    geometry = Column(Geometry('POLYGON', srid=4326), nullable=False)
    area_sqkm = Column(Float)
    centroid = Column(Geometry('POINT', srid=4326))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    simulation_states = relationship("SimulationState", back_populates="grid")
    
    __table_args__ = (
        Index('idx_grid_geometry', 'geometry', postgresql_using='gist'),
        Index('idx_grid_centroid', 'centroid', postgresql_using='gist'),
    )
    
    def __repr__(self):
        return f"<SpatialGrid({self.grid_id}, {self.grid_type}, {self.resolution_meters}m)>"

class SimulationRun(Base):
    """Metadata for a simulation experiment."""
    __tablename__ = 'simulation_run'
    
    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    city_name = Column(String(100))
    start_timestep = Column(Integer, default=0)
    total_timesteps = Column(Integer)
    config = Column(JSON, nullable=False, default=dict)
    status = Column(String(20), default='created')
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_by = Column(String(100))
    
    # Relationships
    simulation_states = relationship("SimulationState", back_populates="run", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('created', 'running', 'completed', 'failed')",
            name='check_simulation_status'
        ),
    )
    
    def __repr__(self):
        return f"<SimulationRun({self.name}, {self.status})>"

class SimulationState(Base):
    """Core state table for urban metrics at each timestep."""
    __tablename__ = 'simulation_state'
    
    state_id = Column(Integer, primary_key=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey('simulation_run.run_id', ondelete='CASCADE'), nullable=False)
    timestep = Column(Integer, nullable=False)
    grid_id = Column(String(50), ForeignKey('spatial_grid.grid_id'), nullable=False)
    
    # Demographic metrics
    population = Column(Integer)
    population_density = Column(Float)
    employment = Column(Integer)
    unemployment_rate = Column(Float)
    
    # Housing metrics
    housing_units = Column(Integer)
    avg_rent_euro = Column(Float)
    vacancy_rate = Column(Float)
    
    # Transportation metrics
    traffic_congestion = Column(Float)
    public_transit_accessibility = Column(Float)
    bike_score = Column(Float)
    walk_score = Column(Float)
    
    # Environmental metrics
    air_quality_index = Column(Float)
    noise_pollution_db = Column(Float)
    green_space_ratio = Column(Float)
    
    # Economic metrics
    commercial_vitality = Column(Float)
    avg_property_value_euro = Column(Float)
    tax_revenue_euro = Column(Float)
    
    # Social metrics
    safety_score = Column(Float)
    social_cohesion_index = Column(Float)
    displacement_risk = Column(Float)
    
    # EV Infrastructure metrics
    chargers_count = Column(Integer, default=0)
    ev_capacity_kw = Column(Float, default=0)
    charger_density_per_sqkm = Column(Float)
    charger_types = Column(JSON, default=dict)  # e.g., {'AC': 5, 'DC': 2, 'Tesla': 1}
    avg_charger_capacity_kw = Column(Float)
    
    # Spatial context
    geometry = Column(Geometry('POLYGON', srid=4326))
    
    # Metadata
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    run = relationship("SimulationRun", back_populates="simulation_states")
    grid = relationship("SpatialGrid", back_populates="simulation_states")
    
    __table_args__ = (
        UniqueConstraint('run_id', 'timestep', 'grid_id', name='uq_simulation_state'),
        CheckConstraint('timestep >= 0', name='check_timestep_positive'),
        CheckConstraint('traffic_congestion >= 0 AND traffic_congestion <= 1', name='check_congestion_range'),
        CheckConstraint('safety_score >= 0 AND safety_score <= 1', name='check_safety_range'),
        CheckConstraint('displacement_risk >= 0 AND displacement_risk <= 1', name='check_displacement_range'),
        Index('idx_state_run_timestep', 'run_id', 'timestep'),
        Index('idx_state_geometry', 'geometry', postgresql_using='gist'),
        Index('idx_state_grid', 'grid_id'),
    )
    
    def __repr__(self):
        return f"<SimulationState(run={self.run_id}, t={self.timestep}, grid={self.grid_id})>"

class LandUse(Base):
    """Land use classification data."""
    __tablename__ = 'land_use'
    
    id = Column(Integer, primary_key=True)
    source = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False)
    geometry = Column(Geometry('GEOMETRY', srid=4326), nullable=False)
    area_sqkm = Column(Float)
    properties = Column(JSON, default=dict)
    
    __table_args__ = (
        Index('idx_landuse_geometry', 'geometry', postgresql_using='gist'),
    )
    
    def __repr__(self):
        return f"<LandUse({self.category})>"

class PointsOfInterest(Base):
    """Points of interest data."""
    __tablename__ = 'points_of_interest'
    
    id = Column(Integer, primary_key=True)
    poi_type = Column(String(100), nullable=False)
    name = Column(String(255))
    geometry = Column(Geometry('POINT', srid=4326), nullable=False)
    properties = Column(JSON, default=dict)
    source = Column(String(50))
    
    __table_args__ = (
        Index('idx_poi_geometry', 'geometry', postgresql_using='gist'),
    )
    
    def __repr__(self):
        return f"<PointsOfInterest({self.poi_type}: {self.name})>"

class TransportNetwork(Base):
    """Transportation network data."""
    __tablename__ = 'transport_network'
    
    id = Column(Integer, primary_key=True)
    network_type = Column(String(50), nullable=False)
    geometry = Column(Geometry('GEOMETRY', srid=4326), nullable=False)
    length_meters = Column(Float)
    properties = Column(JSON, default=dict)
    
    __table_args__ = (
        Index('idx_transport_geometry', 'geometry', postgresql_using='gist'),
    )
    
    def __repr__(self):
        return f"<TransportNetwork({self.network_type})>"

# ============= NEW EV INFRASTRUCTURE MODEL =============
class EVInfrastructure(Base):
    """EV charging infrastructure data."""
    __tablename__ = 'ev_infrastructure'
    
    id = Column(Integer, primary_key=True)
    ev_type = Column(String(50), nullable=False)
    capacity_kw = Column(Integer, nullable=False, default=22)
    operator = Column(String(100))
    authentication = Column(String(100))
    fee = Column(String(10))
    source = Column(String(50), nullable=False)
    geometry = Column(Geometry('POINT', srid=4326), nullable=False)
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint('capacity_kw > 0', name='check_positive_capacity'),
        Index('idx_ev_geometry', 'geometry', postgresql_using='gist'),
        Index('idx_ev_type', 'ev_type'),
        Index('idx_ev_capacity', 'capacity_kw'),
    )
    
    def __repr__(self):
        return f"<EVInfrastructure({self.ev_type}, {self.capacity_kw}kW, {self.operator})>"