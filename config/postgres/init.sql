-- Initialize database schema

-- Users table (for demo/testing)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    groups TEXT[] DEFAULT '{}',
    department VARCHAR(100),
    country VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Connector sync state
CREATE TABLE IF NOT EXISTS connector_sync_state (
    id SERIAL PRIMARY KEY,
    connector_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    last_sync_time TIMESTAMP,
    last_sync_status VARCHAR(50),
    documents_synced INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(connector_type, source_id)
);

-- Document metadata tracking
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(255) UNIQUE NOT NULL,
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    title TEXT,
    url TEXT,
    content_type VARCHAR(100),
    language VARCHAR(10),
    country_tags TEXT[],
    department VARCHAR(100),
    acl_allow TEXT[],
    acl_deny TEXT[],
    hash VARCHAR(64),
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP,
    metadata JSONB,
    UNIQUE(source, source_id)
);

-- Search analytics
CREATE TABLE IF NOT EXISTS search_queries (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    user_id INTEGER REFERENCES users(id),
    username VARCHAR(100),
    user_groups TEXT[],
    filters JSONB,
    results_count INTEGER,
    clicked_doc_id VARCHAR(255),
    click_position INTEGER,
    dwell_time INTEGER,  -- milliseconds
    query_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_documents_source ON documents(source);
CREATE INDEX idx_documents_indexed_at ON documents(indexed_at);
CREATE INDEX idx_search_queries_user ON search_queries(user_id);
CREATE INDEX idx_search_queries_time ON search_queries(query_time);

-- Insert demo users for testing
INSERT INTO users (username, email, hashed_password, full_name, groups, department, country)
VALUES
    ('john.doe', 'john.doe@company.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7BlNuHH3Om', 'John Doe', ARRAY['all-employees', 'uk-hr'], 'HR', 'UK'),
    ('jane.smith', 'jane.smith@company.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7BlNuHH3Om', 'Jane Smith', ARRAY['all-employees', 'us-engineering'], 'Engineering', 'US'),
    ('admin', 'admin@company.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7BlNuHH3Om', 'Admin User', ARRAY['all-employees', 'admin'], 'IT', 'US')
ON CONFLICT (username) DO NOTHING;

-- Password for all demo users: "password123"
