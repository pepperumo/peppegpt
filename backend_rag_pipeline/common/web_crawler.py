"""
Web crawler module using Crawl4AI for extracting content from web pages.
Supports JavaScript-rendered pages, crawl depth, and structured data extraction.
"""

import os
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse
from pathlib import Path
from dotenv import load_dotenv

# Crawl4AI imports
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# Environment loading pattern (consistent with other modules)
is_production = os.getenv("ENVIRONMENT") == "production"
if not is_production:
    project_root = Path(__file__).resolve().parent.parent
    dotenv_path = project_root / '.env'
    load_dotenv(dotenv_path, override=True)
else:
    load_dotenv()


@dataclass
class CrawlResult:
    """
    Structured result from a web crawl operation.

    Attributes:
        url: The URL that was crawled
        title: Page title extracted from the document
        content: Clean markdown content extracted from the page
        links: List of links found on the page
        success: Whether the crawl operation succeeded
        error_message: Error message if the crawl failed
    """
    url: str
    title: str = ""
    content: str = ""
    links: List[str] = field(default_factory=list)
    success: bool = False
    error_message: Optional[str] = None


@dataclass
class CrawlerConfig:
    """Configuration for web crawler from environment variables."""

    # Browser configuration
    headless: bool = True
    browser_type: str = "chromium"
    verbose: bool = False
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # Crawl configuration
    wait_for_timeout: int = 10000  # ms to wait for page load
    page_timeout: int = 30000  # ms timeout for page operations (reduced from 60s)
    delay_before_return: float = 2.0  # seconds to wait after DOM ready before extracting
    wait_until: str = "domcontentloaded"  # 'domcontentloaded' is faster and more reliable than 'networkidle'
    respect_robots_txt: bool = True

    # Content extraction
    remove_overlay_elements: bool = True
    exclude_external_links: bool = False

    @classmethod
    def from_env(cls) -> 'CrawlerConfig':
        """Load configuration from environment variables."""
        config = cls()

        # Browser settings
        config.headless = os.getenv("CRAWLER_HEADLESS", "true").lower() == "true"
        config.browser_type = os.getenv("CRAWLER_BROWSER_TYPE", "chromium")
        config.verbose = os.getenv("CRAWLER_VERBOSE", "false").lower() == "true"
        config.user_agent = os.getenv(
            "CRAWLER_USER_AGENT",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Timeout settings
        try:
            config.wait_for_timeout = int(os.getenv("CRAWLER_WAIT_TIMEOUT", "10000"))
        except ValueError:
            config.wait_for_timeout = 10000

        try:
            config.page_timeout = int(os.getenv("CRAWLER_PAGE_TIMEOUT", "30000"))
        except ValueError:
            config.page_timeout = 30000

        try:
            config.delay_before_return = float(os.getenv("CRAWLER_DELAY_BEFORE_RETURN", "2.0"))
        except ValueError:
            config.delay_before_return = 2.0

        # Wait strategy: 'domcontentloaded' is faster, 'networkidle' waits for all requests
        config.wait_until = os.getenv("CRAWLER_WAIT_UNTIL", "domcontentloaded")

        # Crawl behavior
        config.respect_robots_txt = os.getenv("CRAWLER_RESPECT_ROBOTS", "true").lower() == "true"
        config.remove_overlay_elements = os.getenv("CRAWLER_REMOVE_OVERLAYS", "true").lower() == "true"
        config.exclude_external_links = os.getenv("CRAWLER_EXCLUDE_EXTERNAL", "false").lower() == "true"

        return config


class WebCrawler:
    """
    Web crawler using Crawl4AI for extracting content from web pages.

    Supports:
    - JavaScript-rendered pages (uses headless browser)
    - Crawl depth (follow links on page)
    - Clean markdown content extraction
    - Structured data output (title, content, links)
    - robots.txt compliance

    Example usage:
        crawler = WebCrawler()
        result = await crawler.crawl_url("https://example.com", depth=2)
        print(result.content)
    """

    def __init__(self, config: Optional[CrawlerConfig] = None):
        """
        Initialize the web crawler.

        Args:
            config: Optional CrawlerConfig instance. If None, loads from environment.
        """
        self.config = config or CrawlerConfig.from_env()
        self._visited_urls: Set[str] = set()

    def _normalize_url(self, url: str) -> str:
        """Normalize a URL for deduplication."""
        parsed = urlparse(url)
        # Remove fragment and trailing slash for comparison
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized

    def _is_same_domain(self, base_url: str, target_url: str) -> bool:
        """Check if target URL is on the same domain as base URL."""
        base_domain = urlparse(base_url).netloc
        target_domain = urlparse(target_url).netloc
        return base_domain == target_domain

    def _extract_links(self, result, base_url: str) -> List[str]:
        """
        Extract and filter links from crawl result.

        Args:
            result: Crawl4AI result object
            base_url: Base URL for resolving relative links

        Returns:
            List of absolute URLs found on the page
        """
        links = []

        if not hasattr(result, 'links') or not result.links:
            return links

        # Crawl4AI returns links as a dict with 'internal' and 'external' keys
        internal_links = result.links.get('internal', []) if isinstance(result.links, dict) else []
        external_links = result.links.get('external', []) if isinstance(result.links, dict) else []

        # Process internal links
        for link_info in internal_links:
            href = link_info.get('href', '') if isinstance(link_info, dict) else str(link_info)
            if href:
                absolute_url = urljoin(base_url, href)
                links.append(absolute_url)

        # Process external links if not excluded
        if not self.config.exclude_external_links:
            for link_info in external_links:
                href = link_info.get('href', '') if isinstance(link_info, dict) else str(link_info)
                if href:
                    absolute_url = urljoin(base_url, href)
                    links.append(absolute_url)

        return links

    async def crawl_url(self, url: str, depth: int = 1) -> CrawlResult:
        """
        Crawl a single URL and optionally follow links to specified depth.

        Args:
            url: The URL to crawl
            depth: How many levels of links to follow (1 = only this page)

        Returns:
            CrawlResult with extracted content and metadata
        """
        # Reset visited URLs for new crawl session
        self._visited_urls = set()

        return await self._crawl_recursive(url, depth, is_root=True)

    async def _crawl_recursive(self, url: str, depth: int, is_root: bool = False) -> CrawlResult:
        """
        Internal recursive crawl implementation.

        Args:
            url: The URL to crawl
            depth: Remaining depth to crawl
            is_root: Whether this is the root URL of the crawl

        Returns:
            CrawlResult with extracted content
        """
        normalized_url = self._normalize_url(url)

        # Check if already visited
        if normalized_url in self._visited_urls:
            return CrawlResult(
                url=url,
                success=False,
                error_message="URL already visited in this session"
            )

        self._visited_urls.add(normalized_url)

        try:
            print(f"Crawling URL: {url} (depth remaining: {depth})")

            # Configure browser with custom user agent to avoid bot detection
            browser_config = BrowserConfig(
                headless=self.config.headless,
                browser_type=self.config.browser_type,
                verbose=self.config.verbose,
                user_agent=self.config.user_agent
            )

            # Configure crawl run with optimized settings for difficult sites
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,  # Always fetch fresh content
                page_timeout=self.config.page_timeout,
                wait_until=self.config.wait_until,  # 'domcontentloaded' is more reliable
                delay_before_return_html=self.config.delay_before_return,  # Wait for JS to render
                remove_overlay_elements=self.config.remove_overlay_elements,
                # Note: robots.txt handling is done at the crawler level
            )

            # Perform the crawl
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=crawl_config
                )

                if not result.success:
                    return CrawlResult(
                        url=url,
                        success=False,
                        error_message=result.error_message or "Crawl failed without specific error"
                    )

                # Extract content
                title = result.metadata.get('title', '') if result.metadata else ''
                # Handle both new API (result.markdown.raw_markdown) and fallbacks
                if hasattr(result.markdown, 'raw_markdown'):
                    content = result.markdown.raw_markdown or ""
                else:
                    content = result.markdown or result.cleaned_html or ""

                # Extract links
                links = self._extract_links(result, url)

                # Create result for this page
                crawl_result = CrawlResult(
                    url=url,
                    title=title,
                    content=content,
                    links=links,
                    success=True
                )

                # If depth > 1, crawl child pages and aggregate content
                if depth > 1 and links:
                    # Filter to same-domain links only for recursive crawling
                    same_domain_links = [
                        link for link in links
                        if self._is_same_domain(url, link) and
                        self._normalize_url(link) not in self._visited_urls
                    ]

                    # Limit number of links to follow to avoid explosion
                    max_links_per_page = int(os.getenv("CRAWLER_MAX_LINKS_PER_PAGE", "10"))
                    links_to_follow = same_domain_links[:max_links_per_page]

                    print(f"Following {len(links_to_follow)} links from {url}")

                    # Crawl child pages
                    child_contents = []
                    for child_url in links_to_follow:
                        try:
                            child_result = await self._crawl_recursive(
                                child_url,
                                depth - 1,
                                is_root=False
                            )
                            if child_result.success and child_result.content:
                                child_contents.append(
                                    f"\n\n---\n\n## {child_result.title or child_result.url}\n\n{child_result.content}"
                                )
                        except Exception as e:
                            print(f"Error crawling child URL {child_url}: {e}")
                            continue

                    # Aggregate content from child pages
                    if child_contents:
                        crawl_result.content += "\n".join(child_contents)

                print(f"Successfully crawled {url}: {len(content)} chars, {len(links)} links")
                return crawl_result

        except Exception as e:
            error_msg = f"Error crawling {url}: {type(e).__name__}: {str(e)}"
            print(error_msg)
            return CrawlResult(
                url=url,
                success=False,
                error_message=error_msg
            )

    async def crawl_multiple(self, urls: List[str], depth: int = 1) -> List[CrawlResult]:
        """
        Crawl multiple URLs concurrently.

        Args:
            urls: List of URLs to crawl
            depth: How many levels of links to follow for each URL

        Returns:
            List of CrawlResult objects, one for each input URL
        """
        # Reset visited URLs for new batch
        self._visited_urls = set()

        # Create tasks for concurrent crawling
        tasks = [self.crawl_url(url, depth) for url in urls]

        # Execute all crawls concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to CrawlResult objects
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(CrawlResult(
                    url=urls[i],
                    success=False,
                    error_message=f"Exception during crawl: {type(result).__name__}: {str(result)}"
                ))
            else:
                final_results.append(result)

        return final_results


# Convenience function for simple crawling
async def crawl_url(url: str, depth: int = 1, config: Optional[CrawlerConfig] = None) -> CrawlResult:
    """
    Convenience function to crawl a single URL.

    Args:
        url: The URL to crawl
        depth: How many levels of links to follow
        config: Optional CrawlerConfig

    Returns:
        CrawlResult with extracted content
    """
    crawler = WebCrawler(config)
    return await crawler.crawl_url(url, depth)


async def crawl_multiple(urls: List[str], depth: int = 1, config: Optional[CrawlerConfig] = None) -> List[CrawlResult]:
    """
    Convenience function to crawl multiple URLs.

    Args:
        urls: List of URLs to crawl
        depth: How many levels of links to follow
        config: Optional CrawlerConfig

    Returns:
        List of CrawlResult objects
    """
    crawler = WebCrawler(config)
    return await crawler.crawl_multiple(urls, depth)


# Export public API
__all__ = [
    'CrawlResult',
    'CrawlerConfig',
    'WebCrawler',
    'crawl_url',
    'crawl_multiple',
]
