"""
Tests for the web_crawler module.
Tests cover WebCrawler, CrawlerConfig, and CrawlResult classes.
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import asdict

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from common.web_crawler import (
    WebCrawler,
    CrawlerConfig,
    CrawlResult,
    crawl_url,
    crawl_multiple,
)


class TestCrawlResult:
    """Tests for the CrawlResult dataclass."""

    def test_default_values(self):
        """Test CrawlResult has correct default values."""
        result = CrawlResult(url="https://example.com")

        assert result.url == "https://example.com"
        assert result.title == ""
        assert result.content == ""
        assert result.links == []
        assert result.success is False
        assert result.error_message is None

    def test_successful_result(self):
        """Test creating a successful crawl result."""
        result = CrawlResult(
            url="https://example.com",
            title="Example Page",
            content="# Hello World\n\nThis is content.",
            links=["https://example.com/page1", "https://example.com/page2"],
            success=True
        )

        assert result.success is True
        assert result.title == "Example Page"
        assert len(result.links) == 2
        assert "Hello World" in result.content

    def test_failed_result(self):
        """Test creating a failed crawl result with error message."""
        result = CrawlResult(
            url="https://example.com",
            success=False,
            error_message="Connection timeout"
        )

        assert result.success is False
        assert result.error_message == "Connection timeout"
        assert result.content == ""


class TestCrawlerConfig:
    """Tests for the CrawlerConfig dataclass."""

    def test_default_values(self):
        """Test CrawlerConfig has correct default values."""
        config = CrawlerConfig()

        assert config.headless is True
        assert config.browser_type == "chromium"
        assert config.verbose is False
        assert config.wait_for_timeout == 10000
        assert config.page_timeout == 30000
        assert config.delay_before_return == 2.0
        assert config.wait_until == "domcontentloaded"
        assert config.respect_robots_txt is True
        assert config.remove_overlay_elements is True
        assert config.exclude_external_links is False
        assert "Mozilla" in config.user_agent

    def test_from_env_defaults(self):
        """Test loading config from environment with defaults."""
        with patch.dict(os.environ, {}, clear=False):
            config = CrawlerConfig.from_env()

            assert config.headless is True
            assert config.browser_type == "chromium"
            assert config.page_timeout == 30000

    def test_from_env_custom_values(self):
        """Test loading config from environment with custom values."""
        env_vars = {
            "CRAWLER_HEADLESS": "false",
            "CRAWLER_BROWSER_TYPE": "firefox",
            "CRAWLER_VERBOSE": "true",
            "CRAWLER_PAGE_TIMEOUT": "45000",
            "CRAWLER_WAIT_TIMEOUT": "15000",
            "CRAWLER_DELAY_BEFORE_RETURN": "3.5",
            "CRAWLER_WAIT_UNTIL": "networkidle",
            "CRAWLER_RESPECT_ROBOTS": "false",
            "CRAWLER_REMOVE_OVERLAYS": "false",
            "CRAWLER_EXCLUDE_EXTERNAL": "true",
            "CRAWLER_USER_AGENT": "CustomBot/1.0",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = CrawlerConfig.from_env()

            assert config.headless is False
            assert config.browser_type == "firefox"
            assert config.verbose is True
            assert config.page_timeout == 45000
            assert config.wait_for_timeout == 15000
            assert config.delay_before_return == 3.5
            assert config.wait_until == "networkidle"
            assert config.respect_robots_txt is False
            assert config.remove_overlay_elements is False
            assert config.exclude_external_links is True
            assert config.user_agent == "CustomBot/1.0"

    def test_from_env_invalid_integers(self):
        """Test config handles invalid integer values gracefully."""
        env_vars = {
            "CRAWLER_PAGE_TIMEOUT": "invalid",
            "CRAWLER_WAIT_TIMEOUT": "not_a_number",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = CrawlerConfig.from_env()

            # Should use defaults for invalid values
            assert config.page_timeout == 30000
            assert config.wait_for_timeout == 10000

    def test_from_env_invalid_float(self):
        """Test config handles invalid float values gracefully."""
        env_vars = {
            "CRAWLER_DELAY_BEFORE_RETURN": "not_a_float",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = CrawlerConfig.from_env()

            # Should use default for invalid value
            assert config.delay_before_return == 2.0


class TestWebCrawler:
    """Tests for the WebCrawler class."""

    def test_init_default_config(self):
        """Test WebCrawler initialization with default config."""
        crawler = WebCrawler()

        assert crawler.config is not None
        assert isinstance(crawler.config, CrawlerConfig)
        assert crawler._visited_urls == set()

    def test_init_custom_config(self):
        """Test WebCrawler initialization with custom config."""
        config = CrawlerConfig(headless=False, page_timeout=60000)
        crawler = WebCrawler(config)

        assert crawler.config.headless is False
        assert crawler.config.page_timeout == 60000

    def test_normalize_url_basic(self):
        """Test URL normalization removes trailing slashes and fragments."""
        crawler = WebCrawler()

        # Remove trailing slash
        assert crawler._normalize_url("https://example.com/") == "https://example.com"
        assert crawler._normalize_url("https://example.com/page/") == "https://example.com/page"

        # Preserve query parameters
        assert crawler._normalize_url("https://example.com/page?q=test") == "https://example.com/page?q=test"

    def test_normalize_url_with_fragment(self):
        """Test URL normalization handles fragments (they are removed by urlparse path)."""
        crawler = WebCrawler()

        # Fragment is not included in normalized URL (urlparse separates it)
        normalized = crawler._normalize_url("https://example.com/page#section")
        assert "#section" not in normalized

    def test_is_same_domain_true(self):
        """Test same domain detection returns True for matching domains."""
        crawler = WebCrawler()

        assert crawler._is_same_domain(
            "https://example.com/page1",
            "https://example.com/page2"
        ) is True

        assert crawler._is_same_domain(
            "https://www.example.com/page1",
            "https://www.example.com/page2"
        ) is True

    def test_is_same_domain_false(self):
        """Test same domain detection returns False for different domains."""
        crawler = WebCrawler()

        assert crawler._is_same_domain(
            "https://example.com/page",
            "https://other.com/page"
        ) is False

        # Subdomains are considered different
        assert crawler._is_same_domain(
            "https://www.example.com/page",
            "https://blog.example.com/page"
        ) is False

    def test_extract_links_empty(self):
        """Test link extraction with no links."""
        crawler = WebCrawler()

        # Mock result with no links attribute
        mock_result = MagicMock()
        mock_result.links = None

        links = crawler._extract_links(mock_result, "https://example.com")
        assert links == []

    def test_extract_links_internal(self):
        """Test link extraction for internal links."""
        crawler = WebCrawler()

        mock_result = MagicMock()
        mock_result.links = {
            'internal': [
                {'href': '/page1'},
                {'href': '/page2'},
                {'href': 'https://example.com/page3'},
            ],
            'external': []
        }

        links = crawler._extract_links(mock_result, "https://example.com")

        assert len(links) == 3
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links
        assert "https://example.com/page3" in links

    def test_extract_links_external_included(self):
        """Test link extraction includes external links by default."""
        crawler = WebCrawler()

        mock_result = MagicMock()
        mock_result.links = {
            'internal': [{'href': '/page1'}],
            'external': [{'href': 'https://other.com/page'}]
        }

        links = crawler._extract_links(mock_result, "https://example.com")

        assert len(links) == 2
        assert "https://example.com/page1" in links
        assert "https://other.com/page" in links

    def test_extract_links_external_excluded(self):
        """Test link extraction excludes external links when configured."""
        config = CrawlerConfig(exclude_external_links=True)
        crawler = WebCrawler(config)

        mock_result = MagicMock()
        mock_result.links = {
            'internal': [{'href': '/page1'}],
            'external': [{'href': 'https://other.com/page'}]
        }

        links = crawler._extract_links(mock_result, "https://example.com")

        assert len(links) == 1
        assert "https://example.com/page1" in links
        assert "https://other.com/page" not in links


class TestWebCrawlerAsync:
    """Async tests for WebCrawler crawl methods."""

    @pytest.mark.asyncio
    async def test_crawl_url_success(self):
        """Test successful URL crawling."""
        crawler = WebCrawler()

        # Mock the AsyncWebCrawler
        mock_crawl_result = MagicMock()
        mock_crawl_result.success = True
        mock_crawl_result.metadata = {'title': 'Test Page'}
        mock_crawl_result.markdown = MagicMock()
        mock_crawl_result.markdown.raw_markdown = "# Test Content\n\nThis is test content."
        mock_crawl_result.links = {'internal': [], 'external': []}

        with patch('common.web_crawler.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler_instance = AsyncMock()
            mock_crawler_instance.arun = AsyncMock(return_value=mock_crawl_result)
            mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
            mock_crawler_instance.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler_instance

            result = await crawler.crawl_url("https://example.com")

            assert result.success is True
            assert result.title == "Test Page"
            assert "Test Content" in result.content

    @pytest.mark.asyncio
    async def test_crawl_url_failure(self):
        """Test URL crawling failure."""
        crawler = WebCrawler()

        mock_crawl_result = MagicMock()
        mock_crawl_result.success = False
        mock_crawl_result.error_message = "Connection refused"

        with patch('common.web_crawler.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler_instance = AsyncMock()
            mock_crawler_instance.arun = AsyncMock(return_value=mock_crawl_result)
            mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
            mock_crawler_instance.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler_instance

            result = await crawler.crawl_url("https://example.com")

            assert result.success is False
            assert "Connection refused" in result.error_message

    @pytest.mark.asyncio
    async def test_crawl_url_exception(self):
        """Test URL crawling handles exceptions."""
        crawler = WebCrawler()

        with patch('common.web_crawler.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler_instance = AsyncMock()
            mock_crawler_instance.arun = AsyncMock(side_effect=Exception("Network error"))
            mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
            mock_crawler_instance.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler_instance

            result = await crawler.crawl_url("https://example.com")

            assert result.success is False
            assert "Network error" in result.error_message

    @pytest.mark.asyncio
    async def test_crawl_url_already_visited(self):
        """Test crawling skips already visited URLs."""
        crawler = WebCrawler()

        # Pre-populate visited URLs
        crawler._visited_urls.add("https://example.com")

        result = await crawler._crawl_recursive("https://example.com", depth=1)

        assert result.success is False
        assert "already visited" in result.error_message

    @pytest.mark.asyncio
    async def test_crawl_url_resets_visited_on_new_session(self):
        """Test that crawl_url resets visited URLs for new session."""
        crawler = WebCrawler()

        # Pre-populate visited URLs
        crawler._visited_urls.add("https://old-url.com")

        mock_crawl_result = MagicMock()
        mock_crawl_result.success = True
        mock_crawl_result.metadata = {'title': 'Test'}
        mock_crawl_result.markdown = MagicMock()
        mock_crawl_result.markdown.raw_markdown = "Content"
        mock_crawl_result.links = {'internal': [], 'external': []}

        with patch('common.web_crawler.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler_instance = AsyncMock()
            mock_crawler_instance.arun = AsyncMock(return_value=mock_crawl_result)
            mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
            mock_crawler_instance.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler_instance

            # Start new crawl session
            await crawler.crawl_url("https://example.com")

            # Old visited URLs should be cleared
            assert "https://old-url.com" not in crawler._visited_urls

    @pytest.mark.asyncio
    async def test_crawl_multiple_urls(self):
        """Test crawling multiple URLs."""
        crawler = WebCrawler()

        mock_crawl_result = MagicMock()
        mock_crawl_result.success = True
        mock_crawl_result.metadata = {'title': 'Test'}
        mock_crawl_result.markdown = MagicMock()
        mock_crawl_result.markdown.raw_markdown = "Content"
        mock_crawl_result.links = {'internal': [], 'external': []}

        with patch('common.web_crawler.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler_instance = AsyncMock()
            mock_crawler_instance.arun = AsyncMock(return_value=mock_crawl_result)
            mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
            mock_crawler_instance.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler_instance

            urls = ["https://example1.com", "https://example2.com"]
            results = await crawler.crawl_multiple(urls)

            assert len(results) == 2
            assert all(r.success for r in results)


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_crawl_url_function(self):
        """Test the crawl_url convenience function."""
        mock_crawl_result = MagicMock()
        mock_crawl_result.success = True
        mock_crawl_result.metadata = {'title': 'Test'}
        mock_crawl_result.markdown = MagicMock()
        mock_crawl_result.markdown.raw_markdown = "Content"
        mock_crawl_result.links = {'internal': [], 'external': []}

        with patch('common.web_crawler.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler_instance = AsyncMock()
            mock_crawler_instance.arun = AsyncMock(return_value=mock_crawl_result)
            mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
            mock_crawler_instance.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler_instance

            result = await crawl_url("https://example.com")

            assert result.success is True

    @pytest.mark.asyncio
    async def test_crawl_url_function_with_config(self):
        """Test the crawl_url convenience function with custom config."""
        custom_config = CrawlerConfig(headless=False)

        mock_crawl_result = MagicMock()
        mock_crawl_result.success = True
        mock_crawl_result.metadata = {'title': 'Test'}
        mock_crawl_result.markdown = MagicMock()
        mock_crawl_result.markdown.raw_markdown = "Content"
        mock_crawl_result.links = {'internal': [], 'external': []}

        with patch('common.web_crawler.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler_instance = AsyncMock()
            mock_crawler_instance.arun = AsyncMock(return_value=mock_crawl_result)
            mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
            mock_crawler_instance.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler_instance

            result = await crawl_url("https://example.com", config=custom_config)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_crawl_multiple_function(self):
        """Test the crawl_multiple convenience function."""
        mock_crawl_result = MagicMock()
        mock_crawl_result.success = True
        mock_crawl_result.metadata = {'title': 'Test'}
        mock_crawl_result.markdown = MagicMock()
        mock_crawl_result.markdown.raw_markdown = "Content"
        mock_crawl_result.links = {'internal': [], 'external': []}

        with patch('common.web_crawler.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler_instance = AsyncMock()
            mock_crawler_instance.arun = AsyncMock(return_value=mock_crawl_result)
            mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
            mock_crawler_instance.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler_instance

            urls = ["https://example1.com", "https://example2.com"]
            results = await crawl_multiple(urls)

            assert len(results) == 2


class TestMarkdownExtraction:
    """Tests for markdown content extraction from different API versions."""

    @pytest.mark.asyncio
    async def test_extract_raw_markdown_new_api(self):
        """Test extracting markdown using new API (result.markdown.raw_markdown)."""
        crawler = WebCrawler()

        mock_crawl_result = MagicMock()
        mock_crawl_result.success = True
        mock_crawl_result.metadata = {'title': 'Test'}
        mock_crawl_result.markdown = MagicMock()
        mock_crawl_result.markdown.raw_markdown = "# New API Content"
        mock_crawl_result.links = {'internal': [], 'external': []}

        with patch('common.web_crawler.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler_instance = AsyncMock()
            mock_crawler_instance.arun = AsyncMock(return_value=mock_crawl_result)
            mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
            mock_crawler_instance.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler_instance

            result = await crawler.crawl_url("https://example.com")

            assert "New API Content" in result.content

    @pytest.mark.asyncio
    async def test_extract_markdown_fallback_to_cleaned_html(self):
        """Test extracting content falls back to cleaned_html when markdown is empty."""
        crawler = WebCrawler()

        mock_crawl_result = MagicMock()
        mock_crawl_result.success = True
        mock_crawl_result.metadata = {'title': 'Test'}
        mock_crawl_result.links = {'internal': [], 'external': []}

        # Simulate scenario where markdown.raw_markdown is empty/None
        mock_crawl_result.markdown = MagicMock()
        mock_crawl_result.markdown.raw_markdown = None
        mock_crawl_result.cleaned_html = "<h1>Fallback HTML Content</h1>"

        with patch('common.web_crawler.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler_instance = AsyncMock()
            mock_crawler_instance.arun = AsyncMock(return_value=mock_crawl_result)
            mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
            mock_crawler_instance.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler_instance

            result = await crawler.crawl_url("https://example.com")

            # Should successfully crawl even with empty markdown
            assert result.success is True
