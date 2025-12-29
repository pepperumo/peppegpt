"""
Web sources processor module for crawling URLs and storing them in the RAG pipeline.
Integrates with the web_sources Supabase table to process pending URLs and scheduled re-crawls.
"""

import os
import asyncio
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Handle both relative and absolute imports
try:
    from common.web_crawler import WebCrawler, CrawlResult, CrawlerConfig
    from common.text_chunker import chunk_text
    from common.text_processor import create_embeddings
    from common.graph_builder import add_chunks_to_graph, delete_document_from_graph
    from common.graph_selector import should_use_graph_for_document
except ImportError:
    from web_crawler import WebCrawler, CrawlResult, CrawlerConfig
    from text_chunker import chunk_text
    from text_processor import create_embeddings
    try:
        from graph_builder import add_chunks_to_graph, delete_document_from_graph
    except ImportError:
        add_chunks_to_graph = None
        delete_document_from_graph = None
    try:
        from graph_selector import should_use_graph_for_document
    except ImportError:
        def should_use_graph_for_document(text, chunks, file_title, mime_type, file_metadata=None):
            return (True, "Graph selector not available - using graph for all documents")

# Check if we're in production
is_production = os.getenv("ENVIRONMENT") == "production"

if not is_production:
    # Development: prioritize .env file
    project_root = Path(__file__).resolve().parent.parent
    dotenv_path = project_root / '.env'
    load_dotenv(dotenv_path, override=True)
else:
    # Production: use cloud platform env vars only
    load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

# Ensure credentials are available
if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

supabase: Client = create_client(supabase_url, supabase_key)

# Check if graph is available
GRAPH_AVAILABLE = add_chunks_to_graph is not None and delete_document_from_graph is not None


@dataclass
class ProcessingResult:
    """Result from processing web sources."""
    sources_processed: int = 0
    sources_failed: int = 0
    total_chunks_created: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class WebSourcesProcessor:
    """
    Processor for web sources that crawls URLs and stores content in the RAG pipeline.

    This processor:
    1. Checks Supabase `web_sources` table for URLs with status='pending' or scheduled re-crawls
    2. Uses WebCrawler to crawl the URLs
    3. Chunks content using text_chunker
    4. Generates embeddings and stores in `documents` table
    5. Adds to Neo4j knowledge graph if available
    6. Updates web_sources table with status, chunks_count, last_crawled_at

    Example usage:
        processor = WebSourcesProcessor()
        result = await processor.process_pending_sources()
        print(f"Processed {result.sources_processed} sources")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the web sources processor.

        Args:
            config: Optional configuration dictionary with:
                - text_processing.default_chunk_size: Chunk size (default: 1000)
                - text_processing.default_chunk_overlap: Chunk overlap (default: 0)
                - crawler: Crawler configuration
        """
        self.config = config or {}
        self.crawler = WebCrawler(CrawlerConfig.from_env())

        # Get text processing settings
        text_processing = self.config.get('text_processing', {})
        self.chunk_size = text_processing.get('default_chunk_size', 1000)
        self.chunk_overlap = text_processing.get('default_chunk_overlap', 0)

    async def process_pending_sources(self) -> ProcessingResult:
        """
        Process all pending web sources and sources due for re-crawl.

        This method:
        1. Cleans up orphaned chunks (from deleted web sources)
        2. Queries web_sources for status='pending' OR scheduled re-crawls that are due
        3. Processes each source
        4. Returns aggregated results

        Returns:
            ProcessingResult with statistics about the processing
        """
        start_time = datetime.now(timezone.utc)
        result = ProcessingResult()

        try:
            # First, cleanup any orphaned chunks from deleted web sources
            orphans_cleaned = await self.cleanup_orphaned_chunks()
            if orphans_cleaned > 0:
                print(f"✓ Cleaned up {orphans_cleaned} deleted web source(s)")

            # Get pending sources
            pending_sources = self._get_pending_sources()

            if not pending_sources:
                print("No pending web sources to process")
                result.duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
                return result

            print(f"Found {len(pending_sources)} web sources to process", flush=True)

            # Process each source
            for source in pending_sources:
                try:
                    source_id = source['id']
                    url = source['url']

                    print(f"Processing web source: {url} (ID: {source_id})", flush=True)

                    success = await self.process_single_source(source_id)

                    if success:
                        result.sources_processed += 1
                        # Get updated chunks count
                        updated_source = self._get_source_by_id(source_id)
                        if updated_source:
                            result.total_chunks_created += updated_source.get('chunks_count', 0)
                    else:
                        result.sources_failed += 1

                except Exception as e:
                    error_msg = f"Error processing source {source.get('url', 'unknown')}: {str(e)}"
                    print(error_msg)
                    traceback.print_exc()
                    result.errors.append(error_msg)
                    result.sources_failed += 1

            result.duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
            print(f"Completed processing: {result.sources_processed} succeeded, "
                  f"{result.sources_failed} failed in {result.duration_seconds:.2f}s")

            return result

        except Exception as e:
            error_msg = f"Error in process_pending_sources: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            result.errors.append(error_msg)
            result.duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
            return result

    async def process_single_source(self, source_id: str) -> bool:
        """
        Process a single web source by ID.

        This method:
        1. Gets the source from the database
        2. Updates status to 'crawling'
        3. Crawls the URL using WebCrawler
        4. Chunks and creates embeddings
        5. Stores in documents table
        6. Adds to knowledge graph (if available)
        7. Updates source status to 'completed' or 'error'

        Args:
            source_id: The UUID of the web source to process

        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            # Get the source from database
            source = self._get_source_by_id(source_id)
            if not source:
                print(f"Web source not found: {source_id}")
                return False

            url = source['url']
            crawl_depth = source.get('crawl_depth', 1)
            user_id = source.get('user_id')

            # Update status to 'crawling'
            self._update_source_status(source_id, 'crawling')

            # Delete existing content for this source (in case of re-crawl)
            await self.delete_source_content(source_id)

            # Crawl the URL
            print(f"Crawling URL: {url} (depth: {crawl_depth})", flush=True)
            crawl_result = await self.crawler.crawl_url(url, depth=crawl_depth)

            if not crawl_result.success:
                error_msg = crawl_result.error_message or "Crawl failed without specific error"
                print(f"Crawl failed for {url}: {error_msg}")
                self._update_source_error(source_id, error_msg)
                return False

            if not crawl_result.content:
                error_msg = "No content extracted from URL"
                print(f"No content for {url}: {error_msg}")
                self._update_source_error(source_id, error_msg)
                return False

            # Extract content
            title = crawl_result.title or url
            content = crawl_result.content

            print(f"Crawled {url}: {len(content)} chars, title: '{title}'", flush=True)

            # Chunk the content
            chunks = chunk_text(content, chunk_size=self.chunk_size, overlap=self.chunk_overlap)

            if not chunks:
                error_msg = "No chunks created from content"
                print(f"No chunks for {url}: {error_msg}")
                self._update_source_error(source_id, error_msg)
                return False

            print(f"Created {len(chunks)} chunks for {url}", flush=True)

            # Create embeddings
            embeddings = create_embeddings(chunks)

            if len(embeddings) != len(chunks):
                error_msg = f"Embedding count mismatch: {len(embeddings)} embeddings for {len(chunks)} chunks"
                print(f"Embedding error for {url}: {error_msg}")
                self._update_source_error(source_id, error_msg)
                return False

            # Store chunks in documents table
            self._insert_document_chunks(
                chunks=chunks,
                embeddings=embeddings,
                source_id=source_id,
                url=url,
                title=title,
                user_id=user_id
            )

            # Add to knowledge graph if available
            if GRAPH_AVAILABLE:
                use_graph, reason = should_use_graph_for_document(
                    text=content,
                    chunks=chunks,
                    file_title=title,
                    mime_type="text/html",
                    file_metadata={"url": url, "source_id": source_id, "type": "web"}
                )

                print(f"Graph decision for '{title}': {'USE GRAPH' if use_graph else 'SKIP GRAPH'} - {reason}")

                if use_graph:
                    try:
                        graph_result = await add_chunks_to_graph(
                            chunks=chunks,
                            document_title=title,
                            document_source=source_id,
                            document_metadata={
                                "url": url,
                                "mime_type": "text/html",
                                "type": "web_source",
                                "processed_at": datetime.now(timezone.utc).isoformat(),
                                "graph_reason": reason
                            }
                        )
                        if graph_result:
                            print(f"Added to knowledge graph: {graph_result.get('episodes_created', 0)} episodes")
                    except Exception as e:
                        print(f"Warning: Failed to add to knowledge graph: {e}")
                        # Don't fail the entire process if graph building fails

            # Update source status to completed
            self._update_source_completed(source_id, title, len(chunks))

            print(f"Successfully processed web source: {url} ({len(chunks)} chunks)", flush=True)
            return True

        except Exception as e:
            error_msg = f"Error processing source {source_id}: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            self._update_source_error(source_id, str(e))
            return False

    async def delete_source_content(self, source_id: str) -> bool:
        """
        Delete all document chunks associated with a web source.

        This method:
        1. Deletes graph data for the source (if graph is available)
        2. Deletes all document chunks with matching source_id in metadata

        Args:
            source_id: The UUID of the web source

        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            print(f"Deleting content for web source: {source_id}")

            # Delete graph data first if available
            if GRAPH_AVAILABLE and delete_document_from_graph:
                try:
                    print(f"Deleting graph data for source: {source_id}")
                    await delete_document_from_graph(source_id)
                    print(f"Graph data deletion completed for source: {source_id}")
                except Exception as e:
                    print(f"Warning: Error deleting graph data for {source_id}: {e}")
                    # Continue with document deletion even if graph deletion fails

            # Delete document chunks in batches (similar to db_handler pattern)
            batch_size = 10
            total_deleted = 0

            while True:
                # Fetch batch of chunk IDs
                select_response = supabase.table("documents").select("id").eq(
                    "metadata->>source_id", source_id
                ).limit(batch_size).execute()

                if not select_response.data or len(select_response.data) == 0:
                    break

                chunk_ids = [doc['id'] for doc in select_response.data]

                # Delete batch
                try:
                    supabase.table("documents").delete().in_("id", chunk_ids).execute()
                    total_deleted += len(chunk_ids)
                    print(f"  Deleted batch: {len(chunk_ids)} chunks (total: {total_deleted})")
                except Exception as batch_error:
                    print(f"  Error deleting batch: {batch_error}")
                    # Continue with next batch

            print(f"Deleted {total_deleted} document chunks for source: {source_id}")

            # Update chunks_count in web_sources
            try:
                supabase.table("web_sources").update({
                    "chunks_count": 0
                }).eq("id", source_id).execute()
            except Exception as e:
                print(f"Warning: Could not update chunks_count: {e}")

            return True

        except Exception as e:
            print(f"Error deleting content for source {source_id}: {e}")
            traceback.print_exc()
            return False

    async def cleanup_orphaned_chunks(self) -> int:
        """
        Find and delete orphaned web source chunks.
        These are chunks in 'documents' table whose source_id no longer exists in 'web_sources' table.

        Returns:
            Number of orphaned sources cleaned up
        """
        try:
            # Get all valid web source IDs
            web_sources_result = supabase.table('web_sources').select('id').execute()
            valid_ids = set(row['id'] for row in (web_sources_result.data or []))

            # Get unique source_ids from web chunks
            docs_result = supabase.table('documents').select('metadata').execute()
            web_chunk_source_ids = set()
            for doc in docs_result.data or []:
                metadata = doc.get('metadata', {})
                if metadata.get('source_type') == 'web' and metadata.get('source_id'):
                    web_chunk_source_ids.add(metadata['source_id'])

            # Find orphaned source_ids
            orphaned_ids = web_chunk_source_ids - valid_ids

            if not orphaned_ids:
                return 0

            print(f"Found {len(orphaned_ids)} orphaned web source(s) to clean up")

            for source_id in orphaned_ids:
                await self.delete_source_content(source_id)

            return len(orphaned_ids)

        except Exception as e:
            print(f"Error checking for orphaned web chunks: {e}")
            return 0

    def _get_pending_sources(self) -> List[Dict[str, Any]]:
        """
        Get web sources that need processing.

        Returns sources where:
        1. status = 'pending'
        2. OR scheduled re-crawl is due (crawl_interval_hours is set and time has passed)

        Returns:
            List of web source records
        """
        try:
            # Get pending sources
            pending_response = supabase.table("web_sources").select("*").eq("status", "pending").execute()
            pending_sources = pending_response.data or []

            # Get sources due for re-crawl
            # These are completed sources with crawl_interval_hours set where
            # last_crawled_at + crawl_interval_hours < now
            recrawl_response = supabase.table("web_sources").select("*").eq(
                "status", "completed"
            ).not_.is_("crawl_interval_hours", "null").execute()

            recrawl_sources = []
            now = datetime.now(timezone.utc)

            for source in (recrawl_response.data or []):
                interval_hours = source.get('crawl_interval_hours')
                last_crawled = source.get('last_crawled_at')

                if interval_hours and last_crawled:
                    # Parse the timestamp
                    if isinstance(last_crawled, str):
                        last_crawled_dt = datetime.fromisoformat(last_crawled.replace('Z', '+00:00'))
                    else:
                        last_crawled_dt = last_crawled

                    # Check if re-crawl is due
                    next_crawl = last_crawled_dt + timedelta(hours=interval_hours)
                    if now >= next_crawl:
                        recrawl_sources.append(source)
                        print(f"Source {source['url']} is due for re-crawl "
                              f"(last crawled: {last_crawled_dt}, interval: {interval_hours}h)")

            # Combine both lists
            all_sources = pending_sources + recrawl_sources

            return all_sources

        except Exception as e:
            print(f"Error getting pending sources: {e}")
            traceback.print_exc()
            return []

    def _get_source_by_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get a web source by ID."""
        try:
            response = supabase.table("web_sources").select("*").eq("id", source_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error getting source {source_id}: {e}")
            return None

    def _update_source_status(self, source_id: str, status: str) -> None:
        """Update the status of a web source."""
        try:
            supabase.table("web_sources").update({
                "status": status,
                "error_message": None  # Clear any previous error
            }).eq("id", source_id).execute()
        except Exception as e:
            print(f"Error updating source status: {e}")

    def _update_source_error(self, source_id: str, error_message: str) -> None:
        """Update a web source with error status and message."""
        try:
            supabase.table("web_sources").update({
                "status": "error",
                "error_message": error_message[:500]  # Truncate long error messages
            }).eq("id", source_id).execute()
        except Exception as e:
            print(f"Error updating source error: {e}")

    def _update_source_completed(self, source_id: str, title: str, chunks_count: int) -> None:
        """Update a web source as successfully completed."""
        try:
            supabase.table("web_sources").update({
                "status": "completed",
                "title": title[:500] if title else None,  # Truncate long titles
                "chunks_count": chunks_count,
                "last_crawled_at": datetime.now(timezone.utc).isoformat(),
                "error_message": None
            }).eq("id", source_id).execute()
        except Exception as e:
            print(f"Error updating source completed status: {e}")

    def _insert_document_chunks(
        self,
        chunks: List[str],
        embeddings: List[List[float]],
        source_id: str,
        url: str,
        title: str,
        user_id: Optional[str] = None
    ) -> None:
        """
        Insert document chunks into the documents table.

        Args:
            chunks: List of text chunks
            embeddings: List of embedding vectors
            source_id: The web source UUID
            url: The source URL
            title: The page title
            user_id: Optional user ID for the source
        """
        try:
            if len(chunks) != len(embeddings):
                raise ValueError("Number of chunks and embeddings must match")

            # Prepare data for insertion
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Clean null bytes from chunk
                clean_chunk = chunk.replace('\x00', '')

                data = {
                    "content": clean_chunk,
                    "metadata": {
                        "source_id": source_id,
                        "source_type": "web",
                        "url": url,
                        "file_title": title,
                        "mime_type": "text/html",
                        "chunk_index": i,
                        **({"user_id": user_id} if user_id else {})
                    },
                    "embedding": embedding
                }

                supabase.table("documents").insert(data).execute()

            print(f"Inserted {len(chunks)} document chunks for source: {source_id}")

        except Exception as e:
            print(f"Error inserting document chunks: {e}")
            raise


# Convenience functions for easy usage

async def process_pending_web_sources(config: Optional[Dict[str, Any]] = None) -> ProcessingResult:
    """
    Convenience function to process all pending web sources.

    Args:
        config: Optional configuration dictionary

    Returns:
        ProcessingResult with statistics
    """
    processor = WebSourcesProcessor(config)
    return await processor.process_pending_sources()


async def process_web_source(source_id: str, config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Convenience function to process a single web source.

    Args:
        source_id: The UUID of the web source
        config: Optional configuration dictionary

    Returns:
        True if processing succeeded
    """
    processor = WebSourcesProcessor(config)
    return await processor.process_single_source(source_id)


async def delete_web_source_content(source_id: str) -> bool:
    """
    Convenience function to delete content for a web source.

    Args:
        source_id: The UUID of the web source

    Returns:
        True if deletion succeeded
    """
    processor = WebSourcesProcessor()
    return await processor.delete_source_content(source_id)


# Export public API
__all__ = [
    'ProcessingResult',
    'WebSourcesProcessor',
    'process_pending_web_sources',
    'process_web_source',
    'delete_web_source_content',
]
