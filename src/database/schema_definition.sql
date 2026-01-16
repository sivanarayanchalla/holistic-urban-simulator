-- ============================================
-- HOLISTIC URBAN SIMULATOR - DATABASE SCHEMA
-- ============================================

-- Enable PostGIS and other extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS hstore;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. SPATIAL REFERENCE & META TABLES
-- ============================================

CREATE TABLE spatial_reference (
    srid INTEGER PRIMARY KEY,
    auth_name VARCHAR(256),
    auth_srid INTEGER,
    srtext VARCHAR(2048),
    proj4text VARCHAR(2048)
);

-- ============================================
-- 2. STATIC GEOGRAPHY TABLES
-- ============================================

-- City boundary and administrative units
CREATE TABLE city_boundary (
    id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL,
    country_code CHAR(2),
    admin_level INTEGER,
    area_sqkm FLOAT,
    geometry GEOMETRY(Polygon, 4326),
    UNIQUE(city_name, country_code)
);

-- Spatial grid for simulation (Hexagonal grid)
CREATE TABLE spatial_grid (
    grid_id VARCHAR(50) PRIMARY KEY,
    grid_type VARCHAR(20) CHECK (grid_type IN ('hexagon', 'square', 'voronoi')),
    resolution_meters INTEGER,
    geometry GEOMETRY(Polygon, 4326),
    area_sqkm FLOAT GENERATED ALWAYS AS (ST_Area(geometry::geography) / 1000000) STORED,
    centroid GEOMETRY(Point, 4326) GENERATED ALWAYS AS (ST_Centroid(geometry)) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_grid_geometry ON spatial_grid USING GIST(geometry);
CREATE INDEX idx_grid_centroid ON spatial_grid USING GIST(centroid);

-- Land use classification
CREATE TABLE land_use (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    geometry GEOMETRY(Geometry, 4326),
    area_sqkm FLOAT,
    properties JSONB DEFAULT '{}',
    UNIQUE(source, category, geometry)
);

-- Transportation network
CREATE TABLE transport_network (
    id SERIAL PRIMARY KEY,
    network_type VARCHAR(50) NOT NULL,
    element_type VARCHAR(50) CHECK (element_type IN ('node', 'way', 'relation')),
    geometry GEOMETRY(Geometry, 4326),
    length_meters FLOAT,
    properties JSONB DEFAULT '{}',
    source VARCHAR(50),
    extracted_at TIMESTAMP
);

-- Points of Interest
CREATE TABLE points_of_interest (
    id SERIAL PRIMARY KEY,
    poi_type VARCHAR(100) NOT NULL,
    name VARCHAR(255),
    geometry GEOMETRY(Point, 4326),
    properties JSONB DEFAULT '{}',
    source VARCHAR(50),
    UNIQUE(poi_type, name, geometry)
);

-- ============================================
-- 3. DEMOGRAPHIC & SOCIO-ECONOMIC DATA
-- ============================================

CREATE TABLE demographic_data (
    id SERIAL PRIMARY KEY,
    spatial_unit_id VARCHAR(50), -- Could reference grid_id or administrative unit
    spatial_unit_type VARCHAR(30),
    year INTEGER,
    total_population INTEGER,
    population_density FLOAT,
    age_0_14 INTEGER,
    age_15_64 INTEGER,
    age_65_plus INTEGER,
    households INTEGER,
    avg_household_size FLOAT,
    median_income FLOAT,
    unemployment_rate FLOAT,
    geometry GEOMETRY(Geometry, 4326),
    source VARCHAR(100),
    UNIQUE(spatial_unit_id, year)
);

-- ============================================
-- 4. SIMULATION CORE TABLES
-- ============================================

-- Simulation runs metadata
CREATE TABLE simulation_run (
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    city_name VARCHAR(100),
    start_timestep INTEGER DEFAULT 0,
    total_timesteps INTEGER,
    config JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'created' CHECK (status IN ('created', 'running', 'completed', 'failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_by VARCHAR(100)
);

-- Core state table: One row per grid cell per timestep
CREATE TABLE simulation_state (
    state_id BIGSERIAL PRIMARY KEY,
    run_id UUID REFERENCES simulation_run(run_id) ON DELETE CASCADE,
    timestep INTEGER NOT NULL,
    grid_id VARCHAR(50) REFERENCES spatial_grid(grid_id),
    
    -- DYNAMIC METRICS (Add more as modules are developed)
    population INTEGER,
    population_density FLOAT,
    employment INTEGER,
    unemployment_rate FLOAT,
    
    -- Housing metrics
    housing_units INTEGER,
    avg_rent_euro FLOAT,
    vacancy_rate FLOAT,
    
    -- Transportation metrics
    traffic_congestion FLOAT CHECK (traffic_congestion >= 0 AND traffic_congestion <= 1),
    public_transit_accessibility FLOAT,
    bike_score FLOAT,
    walk_score FLOAT,
    
    -- Environmental metrics
    air_quality_index FLOAT,
    noise_pollution_db FLOAT,
    green_space_ratio FLOAT CHECK (green_space_ratio >= 0 AND green_space_ratio <= 1),
    
    -- Economic metrics
    commercial_vitality FLOAT,
    avg_property_value_euro FLOAT,
    tax_revenue_euro FLOAT,
    
    -- Social metrics
    safety_score FLOAT CHECK (safety_score >= 0 AND safety_score <= 1),
    social_cohesion_index FLOAT,
    displacement_risk FLOAT CHECK (displacement_risk >= 0 AND displacement_risk <= 1),
    
    -- Spatial context (duplicated for query performance)
    geometry GEOMETRY(Polygon, 4326),
    
    -- Metadata
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints and indexes
    UNIQUE(run_id, timestep, grid_id),
    CHECK (timestep >= 0)
);

-- Indexes for performance
CREATE INDEX idx_simulation_state_run_timestep ON simulation_state(run_id, timestep);
CREATE INDEX idx_simulation_state_geometry ON simulation_state USING GIST(geometry);
CREATE INDEX idx_simulation_state_grid ON simulation_state(grid_id);

-- Agent trajectory table (for tracking individual agents if needed)
CREATE TABLE agent_trajectory (
    trajectory_id BIGSERIAL PRIMARY KEY,
    run_id UUID REFERENCES simulation_run(run_id),
    agent_id VARCHAR(100),
    agent_type VARCHAR(50),
    timestep INTEGER,
    grid_id VARCHAR(50),
    activity_type VARCHAR(50),
    geometry GEOMETRY(Point, 4326),
    properties JSONB DEFAULT '{}',
    UNIQUE(run_id, agent_id, timestep)
);

-- ============================================
-- 5. MODULE-SPECIFIC TABLES
-- ============================================

-- Module: Transportation
CREATE TABLE transport_demand (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES simulation_run(run_id),
    timestep INTEGER,
    origin_grid_id VARCHAR(50),
    dest_grid_id VARCHAR(50),
    trip_count INTEGER,
    mode_share JSONB, -- {'car': 0.4, 'transit': 0.3, 'bike': 0.2, 'walk': 0.1}
    peak_hour_factor FLOAT
);

-- Module: Housing Market
CREATE TABLE housing_transactions (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES simulation_run(run_id),
    timestep INTEGER,
    grid_id VARCHAR(50),
    transaction_type VARCHAR(20),
    price_euro FLOAT,
    property_type VARCHAR(50),
    buyer_type VARCHAR(50) -- {'resident', 'investor', 'developer'}
);

-- Module: Business Dynamics
CREATE TABLE business_locations (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES simulation_run(run_id),
    timestep INTEGER,
    grid_id VARCHAR(50),
    business_type VARCHAR(100),
    employees INTEGER,
    revenue_estimate FLOAT,
    geometry GEOMETRY(Point, 4326)
);

-- ============================================
-- 6. VIEWS FOR ANALYSIS
-- ============================================

-- View: Current simulation state (latest timestep)
CREATE OR REPLACE VIEW current_simulation_state AS
SELECT DISTINCT ON (run_id, grid_id) *
FROM simulation_state
ORDER BY run_id, grid_id, timestep DESC;

-- View: Grid cell summary statistics
CREATE OR REPLACE VIEW grid_cell_summary AS
SELECT 
    g.grid_id,
    g.grid_type,
    g.resolution_meters,
    g.geometry,
    COUNT(DISTINCT lu.category) as land_use_types,
    COUNT(poi.id) as poi_count,
    AVG(ss.population_density) as avg_pop_density,
    AVG(ss.traffic_congestion) as avg_congestion
FROM spatial_grid g
LEFT JOIN land_use lu ON ST_Intersects(g.geometry, lu.geometry)
LEFT JOIN points_of_interest poi ON ST_Within(poi.geometry, g.geometry)
LEFT JOIN simulation_state ss ON g.grid_id = ss.grid_id
GROUP BY g.grid_id, g.grid_type, g.resolution_meters, g.geometry;

-- ============================================
-- 7. FUNCTIONS AND TRIGGERS
-- ============================================

-- Function: Update spatial grid area automatically
CREATE OR REPLACE FUNCTION update_grid_area()
RETURNS TRIGGER AS $$
BEGIN
    NEW.area_sqkm := ST_Area(NEW.geometry::geography) / 1000000;
    NEW.centroid := ST_Centroid(NEW.geometry);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trig_update_grid_area
    BEFORE INSERT OR UPDATE ON spatial_grid
    FOR EACH ROW
    EXECUTE FUNCTION update_grid_area();

-- Function: Validate simulation state consistency
CREATE OR REPLACE FUNCTION validate_simulation_state()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure grid exists
    IF NOT EXISTS (SELECT 1 FROM spatial_grid WHERE grid_id = NEW.grid_id) THEN
        RAISE EXCEPTION 'Grid ID % does not exist', NEW.grid_id;
    END IF;
    
    -- Ensure run exists
    IF NOT EXISTS (SELECT 1 FROM simulation_run WHERE run_id = NEW.run_id) THEN
        RAISE EXCEPTION 'Run ID % does not exist', NEW.run_id;
    END IF;
    
    -- Validate metric ranges
    IF NEW.traffic_congestion < 0 OR NEW.traffic_congestion > 1 THEN
        RAISE EXCEPTION 'Traffic congestion must be between 0 and 1';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trig_validate_simulation_state
    BEFORE INSERT OR UPDATE ON simulation_state
    FOR EACH ROW
    EXECUTE FUNCTION validate_simulation_state();

-- ============================================
-- 8. COMMENTS FOR DOCUMENTATION
-- ============================================

COMMENT ON TABLE spatial_grid IS 'Hexagonal grid cells for spatial aggregation in simulations';
COMMENT ON TABLE simulation_state IS 'Core table storing all dynamic urban metrics for each grid cell at each timestep';
COMMENT ON TABLE simulation_run IS 'Metadata table for simulation experiments';
COMMENT ON COLUMN simulation_state.traffic_congestion IS 'Value between 0 (no congestion) and 1 (gridlock)';
COMMENT ON COLUMN simulation_state.displacement_risk IS 'Risk of resident displacement (0=no risk, 1=certain displacement)';

-- ============================================
-- 9. GRANT PERMISSIONS
-- ============================================

-- Create application user (run this separately after creating user)
-- CREATE USER simulator_user WITH PASSWORD 'your_password';
-- GRANT CONNECT ON DATABASE urban_sim TO simulator_user;
-- GRANT USAGE ON SCHEMA public TO simulator_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO simulator_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO simulator_user;