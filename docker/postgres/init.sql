-- Initialize Djobea AI Database
-- This script runs when the PostgreSQL container starts for the first time

-- Create the database user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'djobea_user') THEN
        CREATE ROLE djobea_user WITH LOGIN PASSWORD 'djobea_secure_password';
    END IF;
END
$$;

-- Grant necessary privileges
GRANT ALL PRIVILEGES ON DATABASE djobea_ai TO djobea_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO djobea_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO djobea_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO djobea_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO djobea_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO djobea_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO djobea_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO djobea_user;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Log initialization
SELECT 'Djobea AI database initialized successfully' AS message;