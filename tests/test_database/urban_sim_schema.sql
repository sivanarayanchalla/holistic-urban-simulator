-- urban_sim_schema.sql
-- HOLISTIC URBAN SIMULATOR - DATABASE SCHEMA
-- ============================================

-- Enable required extensions (run this first)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS hstore;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. SPATIAL GRID TABLES (Core simulation units)
-- ============================================

-- Hexagonal grid cells for simulation
CREATE TABLE spatial_grid (
    grid_id VARCHAR(50) PRIMARY KEY,
    grid_type VARCHAR(20) CHECK (grid_type IN ('hexagon', 'square', 'voronoi')),
    resolution_meters INTEGER NOT NULL,
    geometry GEOMETRY(Polygon, 4326) NOT NULL,
    area_sqkm FLOAT,
    centroid GEOMETRY(Point, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for spatial queries
CREATE INDEX idx_grid_geometry ON spatial_grid USING GIST(geometry);

-- ============================================
-- 2. SIMULATION MANAGEMENT TABLES
-- ============================================

-- Tracks different simulation runs
CREATE TABLE simulation_run (
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    city_name VARCHAR(100),
    start_timestep INTEGER DEFAULT 0,
    total_timesteps INTEGER,
    config JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'created' 
        CHECK (status IN ('created', 'running', 'completed', 'failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_by VARCHAR(100)
);

-- Core simulation state - ONE ROW PER GRID CELL PER TIMESTEP
CREATE TABLE simulation_state (
    state_id BIGSERIAL PRIMARY KEY,
    run_id UUID REFERENCES simulation_run(run_id) ON DELETE CASCADE,
    timestep INTEGER NOT NULL CHECK (timestep >= 0),
    grid_id VARCHAR(50) REFERENCES spatial_grid(grid_id),
    
    -- DYNAMIC METRICS (Your urban indicators)
    population INTEGER,
    population_density FLOAT,
    employment INTEGER,
    unemployment_rate FLOAT,
    housing_units INTEGER,
    avg_rent_euro FLOAT,
    vacancy_rate FLOAT,
    traffic_congestion FLOAT CHECK (traffic_congestion >= 0 AND traffic_congestion <= 1),
    public_transit_accessibility FLOAT,
    air_quality_index FLOAT,
    green_space_ratio FLOAT,
    safety_score FLOAT CHECK (safety_score >= 0 AND safety_score <= 1),
    displacement_risk FLOAT CHECK (displacement_risk >= 0 AND displacement_risk <= 1),
    commercial_vitality FLOAT,
    
    -- Spatial reference (duplicated for performance)
    geometry GEOMETRY(Polygon, 4326),
    
    -- Metadata
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint ensures one state per grid per timestep
    UNIQUE(run_id, timestep, grid_id)
);

-- Performance indexes
CREATE INDEX idx_state_run_timestep ON simulation_state(run_id, timestep);
CREATE INDEX idx_state_geometry ON simulation_state USING GIST(geometry);

-- ============================================
-- 3. URBAN DATA TABLES (Static city data)
-- ============================================

-- Land use data (from OSM or city portals)
CREATE TABLE land_use (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    category VARCHAR(100) NOT NULL,
    geometry GEOMETRY(Geometry, 4326) NOT NULL,
    area_sqkm FLOAT,
    properties JSONB DEFAULT '{}'
);

-- Points of interest
CREATE TABLE points_of_interest (
    id SERIAL PRIMARY KEY,
    poi_type VARCHAR(100) NOT NULL,
    name VARCHAR(255),
    geometry GEOMETRY(Point, 4326) NOT NULL,
    properties JSONB DEFAULT '{}',
    source VARCHAR(50)
);

-- Transportation network
CREATE TABLE transport_network (
    id SERIAL PRIMARY KEY,
    network_type VARCHAR(50) NOT NULL,
    geometry GEOMETRY(Geometry, 4326) NOT NULL,
    length_meters FLOAT,
    properties JSONB DEFAULT '{}'
);

-- ============================================
-- 4. GRANT PERMISSIONS TO APPLICATION USER
-- ============================================

-- Already done during user creation, but double-check
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO simulator_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO simulator_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO simulator_user;

-- ============================================
-- 5. HELPER VIEWS FOR ANALYSIS
-- ============================================

-- View: Get latest state for each grid cell
CREATE OR REPLACE VIEW latest_simulation_state AS
SELECT DISTINCT ON (run_id, grid_id) *
FROM simulation_state
ORDER BY run_id, grid_id, timestep DESC;

-- View: Grid summary statistics
CREATE OR REPLACE VIEW grid_summary AS
SELECT 
    g.grid_id,
    g.grid_type,
    g.resolution_meters,
    COUNT(DISTINCT lu.category) as land_use_types,
    COUNT(poi.id) as poi_count,
    g.geometry
FROM spatial_grid g
LEFT JOIN land_use lu ON ST_Intersects(g.geometry, lu.geometry)
LEFT JOIN points_of_interest poi ON ST_Within(poi.geometry, g.geometry)
GROUP BY g.grid_id, g.grid_type, g.resolution_meters, g.geometry;