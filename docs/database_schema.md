# Database Schema Documentation

## Overview
The Urban Simulator uses a PostgreSQL database with PostGIS extension for spatial data management.

## Tables

### 1. spatial_grid
Hexagonal grid cells for spatial aggregation in simulations.

| Column | Type | Description |
|--------|------|-------------|
| grid_id | VARCHAR(50) | Primary key, unique grid identifier |
| grid_type | VARCHAR(20) | Type of grid (hexagon, square, voronoi) |
| resolution_meters | INTEGER | Grid resolution in meters |
| geometry | GEOMETRY(Polygon, 4326) | Grid cell geometry |
| area_sqkm | FLOAT | Area in square kilometers |
| centroid | GEOMETRY(Point, 4326) | Grid cell centroid |
| created_at | TIMESTAMP | Creation timestamp |

**Indexes:**
- idx_grid_geometry (GIST on geometry)
- idx_grid_centroid (GIST on centroid)

### 2. simulation_run
Metadata for simulation experiments.

| Column | Type | Description |
|--------|------|-------------|
| run_id | UUID | Primary key, unique simulation identifier |
| name | VARCHAR(200) | Simulation name |
| description | TEXT | Description of simulation |
| city_name | VARCHAR(100) | City being simulated |
| start_timestep | INTEGER | Starting timestep (default: 0) |
| total_timesteps | INTEGER | Total timesteps in simulation |
| config | JSONB | Simulation configuration parameters |
| status | VARCHAR(20) | Status (created, running, completed, failed) |
| created_at | TIMESTAMP | Creation timestamp |
| started_at | TIMESTAMP | Start timestamp |
| completed_at | TIMESTAMP | Completion timestamp |
| created_by | VARCHAR(100) | Creator identifier |

### 3. simulation_state
Core table storing urban metrics for each grid cell at each timestep.

| Column | Type | Description | Range |
|--------|------|-------------|-------|
| state_id | BIGSERIAL | Primary key | |
| run_id | UUID | Foreign key to simulation_run | |
| timestep | INTEGER | Simulation timestep | >= 0 |
| grid_id | VARCHAR(50) | Foreign key to spatial_grid | |
| population | INTEGER | Population count | |
| traffic_congestion | FLOAT | Traffic congestion level | 0-1 |
| safety_score | FLOAT | Safety score | 0-1 |
| displacement_risk | FLOAT | Displacement risk | 0-1 |
| avg_rent_euro | FLOAT | Average rent in Euros | |
| commercial_vitality | FLOAT | Commercial vitality index | |
| geometry | GEOMETRY(Polygon, 4326) | Grid geometry | |

**Constraints:**
- Unique: (run_id, timestep, grid_id)
- Check: timestep >= 0
- Check: traffic_congestion BETWEEN 0 AND 1
- Check: safety_score BETWEEN 0 AND 1
- Check: displacement_risk BETWEEN 0 AND 1

**Indexes:**
- idx_state_run_timestep (run_id, timestep)
- idx_state_geometry (GIST on geometry)
- idx_state_grid (grid_id)

### 4. land_use
Land use classification data from OSM or city portals.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| source | VARCHAR(50) | Data source (OSM, city portal) |
| category | VARCHAR(100) | Land use category |
| geometry | GEOMETRY(Geometry, 4326) | Land use geometry |
| area_sqkm | FLOAT | Area in square kilometers |
| properties | JSONB | Additional properties |

**Index:**
- idx_landuse_geometry (GIST on geometry)

### 5. points_of_interest
Points of interest (schools, hospitals, restaurants, etc.).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| poi_type | VARCHAR(100) | POI type |
| name | VARCHAR(255) | POI name |
| geometry | GEOMETRY(Point, 4326) | POI location |
| properties | JSONB | Additional properties |
| source | VARCHAR(50) | Data source |

**Index:**
- idx_poi_geometry (GIST on geometry)

### 6. transport_network
Transportation network (roads, bike paths, etc.).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| network_type | VARCHAR(50) | Network type (road, bike, rail) |
| geometry | GEOMETRY(Geometry, 4326) | Network geometry |
| length_meters | FLOAT | Length in meters |
| properties | JSONB | Additional properties |

**Index:**
- idx_transport_geometry (GIST on geometry)

## Views

### latest_simulation_state
Shows the latest state for each grid cell in each simulation run.

```sql
SELECT DISTINCT ON (run_id, grid_id) *
FROM simulation_state
ORDER BY run_id, grid_id, timestep DESC;