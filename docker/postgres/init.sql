-- Initialize Djobea AI Database
-- This script runs when the PostgreSQL container starts for the first time

-- Create additional extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create additional schemas if needed
-- CREATE SCHEMA IF NOT EXISTS analytics;
-- CREATE SCHEMA IF NOT EXISTS audit;

-- Set timezone
SET timezone TO 'UTC';

-- Create indexes for performance (these will be created by SQLAlchemy models)
-- But we can prepare the database for optimal performance

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE djobea_ai TO djobea_user;

-- Log initialization
SELECT 'Database initialized successfully' AS message;