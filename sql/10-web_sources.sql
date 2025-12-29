-- Web Sources Table
-- This table stores web URLs that are crawled and indexed for RAG retrieval

-- Drop existing table if it exists
DROP TABLE IF EXISTS web_sources CASCADE;

-- Create the web_sources table
CREATE TABLE web_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT UNIQUE NOT NULL,
    title TEXT,                                          -- Extracted after crawl
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'crawling', 'completed', 'error')),
    error_message TEXT,                                  -- Error details if crawl failed
    chunks_count INTEGER DEFAULT 0,                      -- Number of document chunks created
    last_crawled_at TIMESTAMPTZ,                         -- Last successful crawl timestamp
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    crawl_depth INTEGER DEFAULT 1,                       -- How many levels deep to crawl links
    crawl_interval_hours INTEGER,                        -- For scheduled re-crawls (NULL = no re-crawl)
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create indexes for efficient querying
CREATE INDEX idx_web_sources_status ON web_sources(status);
CREATE INDEX idx_web_sources_user_id ON web_sources(user_id);
CREATE INDEX idx_web_sources_last_crawled ON web_sources(last_crawled_at);
CREATE INDEX idx_web_sources_crawl_interval ON web_sources(crawl_interval_hours) WHERE crawl_interval_hours IS NOT NULL;

-- Enable Row Level Security
ALTER TABLE web_sources ENABLE ROW LEVEL SECURITY;

-- RLS Policies for authenticated users

-- Users can view their own web sources
CREATE POLICY "Users can view their own web sources"
ON web_sources
FOR SELECT
USING (auth.uid() = user_id);

-- Users can insert their own web sources
CREATE POLICY "Users can insert their own web sources"
ON web_sources
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can update their own web sources
CREATE POLICY "Users can update their own web sources"
ON web_sources
FOR UPDATE
USING (auth.uid() = user_id);

-- Users can delete their own web sources
CREATE POLICY "Users can delete their own web sources"
ON web_sources
FOR DELETE
USING (auth.uid() = user_id);

-- Admin policies (requires is_admin() function to exist)
-- Uncomment these if is_admin() function is available in your database

-- CREATE POLICY "Admins can view all web sources"
-- ON web_sources
-- FOR SELECT
-- USING (is_admin());

-- CREATE POLICY "Admins can update all web sources"
-- ON web_sources
-- FOR UPDATE
-- USING (is_admin());

-- CREATE POLICY "Admins can insert web sources"
-- ON web_sources
-- FOR INSERT
-- WITH CHECK (is_admin());

-- CREATE POLICY "Admins can delete web sources"
-- ON web_sources
-- FOR DELETE
-- USING (is_admin());

-- Trigger function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_web_sources_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Create trigger to automatically update updated_at on changes
CREATE OR REPLACE TRIGGER update_web_sources_updated_at
    BEFORE UPDATE ON web_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_web_sources_updated_at();

-- Add helpful comments
COMMENT ON TABLE web_sources IS 'Stores web URLs that are crawled and indexed for RAG retrieval';
COMMENT ON COLUMN web_sources.id IS 'Unique identifier for the web source';
COMMENT ON COLUMN web_sources.url IS 'The URL to crawl (must be unique)';
COMMENT ON COLUMN web_sources.title IS 'Page title extracted after crawling';
COMMENT ON COLUMN web_sources.status IS 'Current crawl status: pending, crawling, completed, or error';
COMMENT ON COLUMN web_sources.error_message IS 'Error details if the crawl failed';
COMMENT ON COLUMN web_sources.chunks_count IS 'Number of document chunks created from this source';
COMMENT ON COLUMN web_sources.last_crawled_at IS 'Timestamp of the last successful crawl';
COMMENT ON COLUMN web_sources.crawl_depth IS 'How many levels deep to follow links (1 = just the page)';
COMMENT ON COLUMN web_sources.crawl_interval_hours IS 'Hours between scheduled re-crawls (NULL = no automatic re-crawl)';
COMMENT ON COLUMN web_sources.user_id IS 'Owner of this web source for RLS';
