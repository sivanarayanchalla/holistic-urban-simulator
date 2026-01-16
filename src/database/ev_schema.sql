-- EV Infrastructure Schema for Leipzig Catalyst Modeling
CREATE TABLE IF NOT EXISTS ev_infrastructure (
    id SERIAL PRIMARY KEY,
    ev_type VARCHAR(50) NOT NULL,
    capacity_kw INTEGER NOT NULL DEFAULT 22,
    operator VARCHAR(100),
    authentication VARCHAR(100),
    fee VARCHAR(10),
    source VARCHAR(50) NOT NULL,
    geometry GEOMETRY(Point, 4326) NOT NULL,
    properties JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    CONSTRAINT valid_capacity CHECK (capacity_kw > 0),
    CONSTRAINT valid_geometry CHECK (ST_IsValid(geometry))
);

-- Spatial index
CREATE INDEX IF NOT EXISTS idx_ev_infrastructure_geom 
ON ev_infrastructure USING GIST(geometry);

-- Index on ev_type for filtering
CREATE INDEX IF NOT EXISTS idx_ev_infrastructure_type 
ON ev_infrastructure(ev_type);

-- Index on capacity for analysis
CREATE INDEX IF NOT EXISTS idx_ev_infrastructure_capacity 
ON ev_infrastructure(capacity_kw);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_ev_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updated_at
CREATE TRIGGER trigger_ev_updated_at
    BEFORE UPDATE ON ev_infrastructure
    FOR EACH ROW
    EXECUTE FUNCTION update_ev_updated_at();

-- View for fast chargers only
CREATE OR REPLACE VIEW ev_fast_chargers AS
SELECT * FROM ev_infrastructure 
WHERE ev_type = 'fast_charger' OR capacity_kw >= 50;

-- View for spatial analysis
CREATE OR REPLACE VIEW ev_spatial_analysis AS
SELECT 
    id,
    ev_type,
    capacity_kw,
    operator,
    geometry,
    ST_X(geometry::geometry) as longitude,
    ST_Y(geometry::geometry) as latitude,
    properties->>'opening_hours' as opening_hours,
    properties->>'socket' as socket_type,
    properties->>'parking' as parking_info
FROM ev_infrastructure;