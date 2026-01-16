-- Migration: Add EV Infrastructure Metrics Columns to simulation_state table
-- Date: January 15, 2026
-- Description: Adds EV-related columns to track charger count, capacity, density, and types

ALTER TABLE simulation_state
    ADD COLUMN chargers_count INTEGER DEFAULT 0,
    ADD COLUMN ev_capacity_kw FLOAT DEFAULT 0,
    ADD COLUMN charger_density_per_sqkm FLOAT DEFAULT 0,
    ADD COLUMN charger_types JSONB DEFAULT '{}',
    ADD COLUMN avg_charger_capacity_kw FLOAT DEFAULT 0;

-- Create indexes for EV-related queries
CREATE INDEX IF NOT EXISTS idx_simulation_state_chargers_count 
    ON simulation_state(chargers_count);
CREATE INDEX IF NOT EXISTS idx_simulation_state_ev_capacity 
    ON simulation_state(ev_capacity_kw);

-- Verify migration
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'simulation_state' 
AND column_name IN ('chargers_count', 'ev_capacity_kw', 'charger_density_per_sqkm', 'charger_types', 'avg_charger_capacity_kw')
ORDER BY ordinal_position;
