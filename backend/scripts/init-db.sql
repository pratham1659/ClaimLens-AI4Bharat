-- ClaimLens Database Initialization Script
-- This script runs when the PostgreSQL container starts for the first time

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE claimlens TO postgres;

-- Create schemas if needed
CREATE SCHEMA IF NOT EXISTS public;

-- Log initialization completion
DO $$
BEGIN
    RAISE NOTICE 'ClaimLens database initialized successfully';
END $$;
