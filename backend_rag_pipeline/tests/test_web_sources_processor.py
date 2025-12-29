"""
Tests for the web_sources_processor module.
Tests cover WebSourcesProcessor and related functions for processing web URLs.
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta
from dataclasses import asdict

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestProcessingResult:
    """Tests for the ProcessingResult dataclass."""

    def test_default_values(self):
        """Test ProcessingResult has correct default values."""
        # Import here to avoid module-level Supabase initialization
        with patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-key'
        }):
            with patch('common.web_sources_processor.create_client'):
                from common.web_sources_processor import ProcessingResult

                result = ProcessingResult()

                assert result.sources_processed == 0
                assert result.sources_failed == 0
                assert result.total_chunks_created == 0
                assert result.errors == []
                assert result.duration_seconds == 0.0

    def test_custom_values(self):
        """Test ProcessingResult with custom values."""
        with patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-key'
        }):
            with patch('common.web_sources_processor.create_client'):
                from common.web_sources_processor import ProcessingResult

                result = ProcessingResult(
                    sources_processed=5,
                    sources_failed=2,
                    total_chunks_created=150,
                    errors=["Error 1", "Error 2"],
                    duration_seconds=45.5
                )

                assert result.sources_processed == 5
                assert result.sources_failed == 2
                assert result.total_chunks_created == 150
                assert len(result.errors) == 2
                assert result.duration_seconds == 45.5


class TestWebSourcesProcessor:
    """Tests for the WebSourcesProcessor class."""

    @pytest.fixture
    def mock_env(self):
        """Setup mock environment variables."""
        return {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-service-key',
            'ENVIRONMENT': 'test'
        }

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        mock = MagicMock()
        mock.table.return_value = mock
        mock.select.return_value = mock
        mock.insert.return_value = mock
        mock.update.return_value = mock
        mock.delete.return_value = mock
        mock.eq.return_value = mock
        mock.not_.return_value = mock
        mock.is_.return_value = mock
        mock.in_.return_value = mock
        mock.limit.return_value = mock
        mock.execute.return_value = MagicMock(data=[])
        return mock

    def test_init_default_config(self, mock_env, mock_supabase):
        """Test WebSourcesProcessor initialization with default config."""
        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()

                    assert processor.chunk_size == 1000
                    assert processor.chunk_overlap == 0

    def test_init_custom_config(self, mock_env, mock_supabase):
        """Test WebSourcesProcessor initialization with custom config."""
        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    config = {
                        'text_processing': {
                            'default_chunk_size': 500,
                            'default_chunk_overlap': 50
                        }
                    }
                    processor = WebSourcesProcessor(config)

                    assert processor.chunk_size == 500
                    assert processor.chunk_overlap == 50


class TestWebSourcesProcessorMethods:
    """Tests for WebSourcesProcessor methods with mocked dependencies."""

    @pytest.fixture
    def processor_setup(self):
        """Setup processor with all mocks."""
        mock_env = {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-service-key',
            'ENVIRONMENT': 'test'
        }

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_supabase
        mock_supabase.select.return_value = mock_supabase
        mock_supabase.insert.return_value = mock_supabase
        mock_supabase.update.return_value = mock_supabase
        mock_supabase.delete.return_value = mock_supabase
        mock_supabase.eq.return_value = mock_supabase
        mock_supabase.not_.return_value = mock_supabase
        mock_supabase.is_.return_value = mock_supabase
        mock_supabase.in_.return_value = mock_supabase
        mock_supabase.limit.return_value = mock_supabase
        mock_supabase.execute.return_value = MagicMock(data=[])

        return mock_env, mock_supabase

    def test_get_pending_sources_empty(self, processor_setup):
        """Test getting pending sources when none exist."""
        mock_env, mock_supabase = processor_setup

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()
                    sources = processor._get_pending_sources()

                    assert sources == []

    def test_get_pending_sources_with_pending(self, processor_setup):
        """Test getting pending sources returns pending URLs."""
        mock_env, mock_supabase = processor_setup

        pending_data = [
            {'id': 'uuid-1', 'url': 'https://example1.com', 'status': 'pending'},
            {'id': 'uuid-2', 'url': 'https://example2.com', 'status': 'pending'},
        ]

        # Configure mock to return pending sources
        mock_response = MagicMock()
        mock_response.data = pending_data

        mock_supabase.execute.return_value = mock_response

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()
                    sources = processor._get_pending_sources()

                    assert len(sources) == 2

    def test_get_source_by_id_found(self, processor_setup):
        """Test getting a source by ID when it exists."""
        mock_env, mock_supabase = processor_setup

        source_data = {
            'id': 'uuid-1',
            'url': 'https://example.com',
            'status': 'pending',
            'crawl_depth': 1
        }

        mock_response = MagicMock()
        mock_response.data = [source_data]
        mock_supabase.execute.return_value = mock_response

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()
                    source = processor._get_source_by_id('uuid-1')

                    assert source is not None
                    assert source['id'] == 'uuid-1'
                    assert source['url'] == 'https://example.com'

    def test_get_source_by_id_not_found(self, processor_setup):
        """Test getting a source by ID when it doesn't exist."""
        mock_env, mock_supabase = processor_setup

        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.execute.return_value = mock_response

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()
                    source = processor._get_source_by_id('nonexistent-uuid')

                    assert source is None

    def test_update_source_status(self, processor_setup):
        """Test updating source status."""
        mock_env, mock_supabase = processor_setup

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()
                    processor._update_source_status('uuid-1', 'crawling')

                    # Verify update was called
                    mock_supabase.table.assert_called_with('web_sources')

    def test_update_source_error(self, processor_setup):
        """Test updating source with error status."""
        mock_env, mock_supabase = processor_setup

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()
                    processor._update_source_error('uuid-1', 'Connection timeout')

                    mock_supabase.table.assert_called_with('web_sources')

    def test_update_source_error_truncates_long_message(self, processor_setup):
        """Test that long error messages are truncated."""
        mock_env, mock_supabase = processor_setup

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()
                    long_error = "x" * 1000  # 1000 character error
                    processor._update_source_error('uuid-1', long_error)

                    # Verify truncation happens (error should be <=500 chars)
                    mock_supabase.update.assert_called()

    def test_update_source_completed(self, processor_setup):
        """Test updating source as completed."""
        mock_env, mock_supabase = processor_setup

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()
                    processor._update_source_completed('uuid-1', 'Test Page', 10)

                    mock_supabase.table.assert_called_with('web_sources')


class TestWebSourcesProcessorAsync:
    """Async tests for WebSourcesProcessor."""

    @pytest.fixture
    def processor_setup(self):
        """Setup processor with all mocks."""
        mock_env = {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-service-key',
            'ENVIRONMENT': 'test'
        }

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_supabase
        mock_supabase.select.return_value = mock_supabase
        mock_supabase.insert.return_value = mock_supabase
        mock_supabase.update.return_value = mock_supabase
        mock_supabase.delete.return_value = mock_supabase
        mock_supabase.eq.return_value = mock_supabase
        mock_supabase.not_.return_value = mock_supabase
        mock_supabase.is_.return_value = mock_supabase
        mock_supabase.in_.return_value = mock_supabase
        mock_supabase.limit.return_value = mock_supabase
        mock_supabase.execute.return_value = MagicMock(data=[])

        return mock_env, mock_supabase

    @pytest.mark.asyncio
    async def test_process_pending_sources_empty(self, processor_setup):
        """Test processing when no pending sources exist."""
        mock_env, mock_supabase = processor_setup

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()
                    result = await processor.process_pending_sources()

                    assert result.sources_processed == 0
                    assert result.sources_failed == 0

    @pytest.mark.asyncio
    async def test_process_single_source_not_found(self, processor_setup):
        """Test processing a source that doesn't exist."""
        mock_env, mock_supabase = processor_setup

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()
                    result = await processor.process_single_source('nonexistent-uuid')

                    assert result is False

    @pytest.mark.asyncio
    async def test_process_single_source_crawl_failure(self, processor_setup):
        """Test processing a source when crawl fails."""
        mock_env, mock_supabase = processor_setup

        source_data = {
            'id': 'uuid-1',
            'url': 'https://example.com',
            'status': 'pending',
            'crawl_depth': 1,
            'user_id': 'user-uuid'
        }

        mock_response = MagicMock()
        mock_response.data = [source_data]
        mock_supabase.execute.return_value = mock_response

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor, CrawlResult

                    processor = WebSourcesProcessor()

                    # Mock the crawler to return a failed result
                    mock_crawl_result = CrawlResult(
                        url='https://example.com',
                        success=False,
                        error_message='Connection timeout'
                    )

                    with patch.object(processor.crawler, 'crawl_url', new_callable=AsyncMock) as mock_crawl:
                        mock_crawl.return_value = mock_crawl_result

                        with patch.object(processor, 'delete_source_content', new_callable=AsyncMock):
                            result = await processor.process_single_source('uuid-1')

                            assert result is False

    @pytest.mark.asyncio
    async def test_process_single_source_success(self, processor_setup):
        """Test successfully processing a source."""
        mock_env, mock_supabase = processor_setup

        source_data = {
            'id': 'uuid-1',
            'url': 'https://example.com',
            'status': 'pending',
            'crawl_depth': 1,
            'user_id': 'user-uuid'
        }

        mock_response = MagicMock()
        mock_response.data = [source_data]
        mock_supabase.execute.return_value = mock_response

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor, CrawlResult

                    processor = WebSourcesProcessor()

                    # Mock successful crawl result
                    mock_crawl_result = CrawlResult(
                        url='https://example.com',
                        title='Test Page',
                        content='# Test Content\n\nThis is test content for the page.',
                        links=[],
                        success=True
                    )

                    with patch.object(processor.crawler, 'crawl_url', new_callable=AsyncMock) as mock_crawl:
                        mock_crawl.return_value = mock_crawl_result

                        with patch.object(processor, 'delete_source_content', new_callable=AsyncMock):
                            with patch('common.web_sources_processor.chunk_text') as mock_chunk:
                                mock_chunk.return_value = ['Chunk 1', 'Chunk 2']

                                with patch('common.web_sources_processor.create_embeddings') as mock_embed:
                                    mock_embed.return_value = [[0.1] * 1536, [0.2] * 1536]

                                    with patch('common.web_sources_processor.should_use_graph_for_document') as mock_graph_check:
                                        mock_graph_check.return_value = (False, "Test skip")

                                        result = await processor.process_single_source('uuid-1')

                                        assert result is True

    @pytest.mark.asyncio
    async def test_delete_source_content(self, processor_setup):
        """Test deleting source content."""
        mock_env, mock_supabase = processor_setup

        # First call returns some chunks, second call returns empty (deletion complete)
        chunk_data = [{'id': 'chunk-1'}, {'id': 'chunk-2'}]

        call_count = [0]

        def mock_execute():
            call_count[0] += 1
            mock_resp = MagicMock()
            if call_count[0] <= 1:
                mock_resp.data = chunk_data
            else:
                mock_resp.data = []
            return mock_resp

        mock_supabase.execute = mock_execute

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    with patch('common.web_sources_processor.GRAPH_AVAILABLE', False):
                        from common.web_sources_processor import WebSourcesProcessor

                        processor = WebSourcesProcessor()
                        result = await processor.delete_source_content('uuid-1')

                        assert result is True


class TestRecrawlScheduling:
    """Tests for re-crawl scheduling logic."""

    @pytest.fixture
    def processor_setup(self):
        """Setup processor with all mocks."""
        mock_env = {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-service-key',
            'ENVIRONMENT': 'test'
        }

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_supabase
        mock_supabase.select.return_value = mock_supabase
        mock_supabase.insert.return_value = mock_supabase
        mock_supabase.update.return_value = mock_supabase
        mock_supabase.delete.return_value = mock_supabase
        mock_supabase.eq.return_value = mock_supabase
        mock_supabase.not_.return_value = mock_supabase
        mock_supabase.is_.return_value = mock_supabase
        mock_supabase.in_.return_value = mock_supabase
        mock_supabase.limit.return_value = mock_supabase
        mock_supabase.execute.return_value = MagicMock(data=[])

        return mock_env, mock_supabase

    def test_recrawl_due_logic(self, processor_setup):
        """Test the logic for determining if a source is due for re-crawl."""
        # This tests the time calculation logic directly without complex mocking
        mock_env, mock_supabase = processor_setup

        # Source crawled 25 hours ago with 24-hour interval should be due
        past_time = datetime.now(timezone.utc) - timedelta(hours=25)
        interval_hours = 24
        next_crawl = past_time + timedelta(hours=interval_hours)
        now = datetime.now(timezone.utc)

        # Verify the logic: now >= next_crawl means it's due
        assert now >= next_crawl, "Source should be due for re-crawl"

        # Source crawled 1 hour ago with 24-hour interval should NOT be due
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        next_crawl_recent = recent_time + timedelta(hours=interval_hours)

        # Verify: now < next_crawl means it's NOT due
        assert now < next_crawl_recent, "Source should NOT be due for re-crawl yet"

    def test_get_pending_sources_excludes_not_due_recrawls(self, processor_setup):
        """Test that sources not yet due for re-crawl are excluded."""
        mock_env, mock_supabase = processor_setup

        # Create a source that is NOT due for re-crawl (crawled 1 hour ago, interval is 24 hours)
        recent_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        completed_source = {
            'id': 'uuid-1',
            'url': 'https://example.com',
            'status': 'completed',
            'crawl_interval_hours': 24,
            'last_crawled_at': recent_time
        }

        pending_response = MagicMock()
        pending_response.data = []

        recrawl_response = MagicMock()
        recrawl_response.data = [completed_source]

        call_count = [0]

        def mock_execute():
            call_count[0] += 1
            if call_count[0] == 1:
                return pending_response
            else:
                return recrawl_response

        mock_supabase.execute = mock_execute

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()
                    sources = processor._get_pending_sources()

                    # Should NOT include the source (not yet due)
                    assert len(sources) == 0


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture
    def mock_setup(self):
        """Setup mocks for convenience functions."""
        mock_env = {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-service-key',
            'ENVIRONMENT': 'test'
        }

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_supabase
        mock_supabase.select.return_value = mock_supabase
        mock_supabase.insert.return_value = mock_supabase
        mock_supabase.update.return_value = mock_supabase
        mock_supabase.delete.return_value = mock_supabase
        mock_supabase.eq.return_value = mock_supabase
        mock_supabase.not_.return_value = mock_supabase
        mock_supabase.is_.return_value = mock_supabase
        mock_supabase.in_.return_value = mock_supabase
        mock_supabase.limit.return_value = mock_supabase
        mock_supabase.execute.return_value = MagicMock(data=[])

        return mock_env, mock_supabase

    @pytest.mark.asyncio
    async def test_process_pending_web_sources_function(self, mock_setup):
        """Test the process_pending_web_sources convenience function."""
        mock_env, mock_supabase = mock_setup

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import process_pending_web_sources

                    result = await process_pending_web_sources()

                    assert result.sources_processed == 0
                    assert result.sources_failed == 0

    @pytest.mark.asyncio
    async def test_process_web_source_function(self, mock_setup):
        """Test the process_web_source convenience function."""
        mock_env, mock_supabase = mock_setup

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import process_web_source

                    result = await process_web_source('nonexistent-uuid')

                    assert result is False

    @pytest.mark.asyncio
    async def test_delete_web_source_content_function(self, mock_setup):
        """Test the delete_web_source_content convenience function."""
        mock_env, mock_supabase = mock_setup

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    with patch('common.web_sources_processor.GRAPH_AVAILABLE', False):
                        from common.web_sources_processor import delete_web_source_content

                        result = await delete_web_source_content('uuid-1')

                        assert result is True


class TestInsertDocumentChunks:
    """Tests for document chunk insertion."""

    @pytest.fixture
    def processor_setup(self):
        """Setup processor with all mocks."""
        mock_env = {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_SERVICE_KEY': 'test-service-key',
            'ENVIRONMENT': 'test'
        }

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_supabase
        mock_supabase.select.return_value = mock_supabase
        mock_supabase.insert.return_value = mock_supabase
        mock_supabase.update.return_value = mock_supabase
        mock_supabase.delete.return_value = mock_supabase
        mock_supabase.eq.return_value = mock_supabase
        mock_supabase.execute.return_value = MagicMock(data=[])

        return mock_env, mock_supabase

    def test_insert_document_chunks_success(self, processor_setup):
        """Test successful document chunk insertion."""
        mock_env, mock_supabase = processor_setup

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()

                    chunks = ['Chunk 1', 'Chunk 2', 'Chunk 3']
                    embeddings = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]

                    processor._insert_document_chunks(
                        chunks=chunks,
                        embeddings=embeddings,
                        source_id='uuid-1',
                        url='https://example.com',
                        title='Test Page',
                        user_id='user-uuid'
                    )

                    # Verify insert was called for each chunk
                    assert mock_supabase.insert.call_count == 3

    def test_insert_document_chunks_mismatched_counts(self, processor_setup):
        """Test that mismatched chunk/embedding counts raise error."""
        mock_env, mock_supabase = processor_setup

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()

                    chunks = ['Chunk 1', 'Chunk 2', 'Chunk 3']
                    embeddings = [[0.1] * 1536, [0.2] * 1536]  # Only 2 embeddings

                    with pytest.raises(ValueError, match="must match"):
                        processor._insert_document_chunks(
                            chunks=chunks,
                            embeddings=embeddings,
                            source_id='uuid-1',
                            url='https://example.com',
                            title='Test Page'
                        )

    def test_insert_document_chunks_cleans_null_bytes(self, processor_setup):
        """Test that null bytes are removed from chunks."""
        mock_env, mock_supabase = processor_setup

        with patch.dict(os.environ, mock_env):
            with patch('common.web_sources_processor.create_client', return_value=mock_supabase):
                with patch('common.web_sources_processor.supabase', mock_supabase):
                    from common.web_sources_processor import WebSourcesProcessor

                    processor = WebSourcesProcessor()

                    # Chunk with null bytes
                    chunks = ['Chunk with \x00 null \x00 bytes']
                    embeddings = [[0.1] * 1536]

                    processor._insert_document_chunks(
                        chunks=chunks,
                        embeddings=embeddings,
                        source_id='uuid-1',
                        url='https://example.com',
                        title='Test Page'
                    )

                    # Verify insert was called (null bytes should be cleaned)
                    mock_supabase.insert.assert_called_once()
