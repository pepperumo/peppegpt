"""
Knowledge graph builder for extracting entities and relationships.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import asyncio

from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

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

class DocumentChunk:
    """Simple document chunk class for compatibility."""
    def __init__(self, content: str, index: int, metadata: Optional[Dict] = None):
        self.content = content
        self.index = index
        self.metadata = metadata or {}

class GraphBuilder:
    """Builds knowledge graph from document chunks."""

    def __init__(self):
        """Initialize graph builder."""
        self.graph_client = None
        self._initialized = False
        self._graph_available = False

    async def initialize(self):
        """Initialize graph client."""
        if self._initialized:
            return

        try:
            # Try to import and initialize the graph client
            from graph_utils import GraphitiClient

            self.graph_client = GraphitiClient()
            await self.graph_client.initialize()
            self._initialized = True
            self._graph_available = True
            logger.info("Graph builder initialized successfully")
        except ImportError as e:
            logger.warning(f"Graph utilities not available: {e}")
            self._graph_available = False
        except Exception as e:
            logger.warning(f"Failed to initialize graph builder: {e}")
            self._graph_available = False

    async def close(self):
        """Close graph client."""
        if self._initialized and self.graph_client:
            await self.graph_client.close()
            self._initialized = False
            self._graph_available = False

    async def add_document_to_graph(
        self,
        chunks: List[str],
        document_title: str,
        document_source: str,
        document_metadata: Optional[Dict[str, Any]] = None,
        batch_size: int = 3  # Reduced batch size for Graphiti
    ) -> Dict[str, Any]:
        """
        Add document chunks to the knowledge graph.

        Args:
            chunks: List of text chunks (strings)
            document_title: Title of the document
            document_source: Source of the document (file_id)
            document_metadata: Additional metadata
            batch_size: Number of chunks to process in each batch

        Returns:
            Processing results
        """
        if not self._graph_available:
            return {"episodes_created": 0, "errors": ["Graph not available"]}

        if not self._initialized:
            await self.initialize()

        if not self._graph_available:
            return {"episodes_created": 0, "errors": ["Graph initialization failed"]}

        if not self.graph_client:
            return {"episodes_created": 0, "errors": ["Graph client not initialized"]}

        if not chunks:
            return {"episodes_created": 0, "errors": []}

        logger.info(f"Adding {len(chunks)} chunks to knowledge graph for document: {document_title}")
        logger.info("⚠️ Large chunks will be truncated to avoid Graphiti token limits.")

        # Check for oversized chunks and warn
        oversized_chunks = [i for i, chunk in enumerate(chunks) if len(chunk) > 6000]
        if oversized_chunks:
            logger.warning(f"Found {len(oversized_chunks)} chunks over 6000 chars that will be truncated: {oversized_chunks}")

        episodes_created = 0
        errors = []

        # Process chunks one by one to avoid overwhelming Graphiti
        for i, chunk_content in enumerate(chunks):
            try:
                # Create episode ID
                episode_id = f"{document_source}_{i}_{datetime.now().timestamp()}"

                # Prepare episode content with size limits
                episode_content = self._prepare_episode_content(
                    chunk_content,
                    i,
                    document_title,
                    document_metadata
                )

                # Create source description - includes file_id for deletion tracking
                # Format: "source_id:{file_id}|Document: {title} (Chunk: {i})"
                source_description = f"source_id:{document_source}|Document: {document_title} (Chunk: {i})"

                # Create human-readable display name for graph visualization
                # Format: "Document Title (Chunk N)" - truncated if too long
                display_name = document_title[:50] if len(document_title) > 50 else document_title
                if len(chunks) > 1:
                    display_name = f"{display_name} ({i+1}/{len(chunks)})"

                # Add episode to graph
                await self.graph_client.add_episode(
                    episode_id=episode_id,
                    content=episode_content,
                    source=source_description,
                    timestamp=datetime.now(timezone.utc),
                    metadata={
                        "document_title": document_title,
                        "document_source": document_source,
                        "chunk_index": i,
                        "original_length": len(chunk_content),
                        "processed_length": len(episode_content)
                    },
                    display_name=display_name
                )

                episodes_created += 1
                logger.info(f"✓ Added episode {episode_id} to knowledge graph ({episodes_created}/{len(chunks)})")

                # Small delay between each episode to reduce API pressure
                if i < len(chunks) - 1:
                    await asyncio.sleep(0.2)

            except Exception as e:
                error_msg = f"Failed to add chunk {i} to graph: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

                # Continue processing other chunks even if one fails
                continue

        result = {
            "episodes_created": episodes_created,
            "total_chunks": len(chunks),
            "errors": errors
        }

        logger.info(f"Graph building complete: {episodes_created} episodes created, {len(errors)} errors")
        return result

    def _prepare_episode_content(
        self,
        chunk_content: str,
        chunk_index: int,
        document_title: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Prepare episode content with minimal context to avoid token limits.

        Args:
            chunk_content: Text content of the chunk
            chunk_index: Index of the chunk
            document_title: Title of the document
            document_metadata: Additional metadata

        Returns:
            Formatted episode content (optimized for Graphiti)
        """
        # Limit chunk content to avoid Graphiti's 8192 token OUTPUT limit
        # Graphiti generates extensive entity/relationship analysis which can exceed 8192 tokens
        # Reduce input to 1500 chars (~375 tokens) to keep total output well under limit
        # This significantly speeds up processing by avoiding retries
        max_content_length = 1500

        content = chunk_content
        if len(content) > max_content_length:
            # Truncate content but try to end at a sentence boundary
            truncated = content[:max_content_length]
            last_sentence_end = max(
                truncated.rfind('. '),
                truncated.rfind('! '),
                truncated.rfind('? ')
            )

            if last_sentence_end > max_content_length * 0.7:  # If we can keep 70% and end cleanly
                content = truncated[:last_sentence_end + 1] + " [TRUNCATED]"
            else:
                content = truncated + "... [TRUNCATED]"

            logger.warning(f"Truncated chunk {chunk_index} from {len(chunk_content)} to {len(content)} chars for Graphiti")

        # Add minimal context (just document title for now)
        if document_title and len(content) < max_content_length - 100:
            episode_content = f"[Doc: {document_title[:50]}]\n\n{content}"
        else:
            episode_content = content

        return episode_content

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate of token count (4 chars per token)."""
        return len(text) // 4

    def _is_content_too_large(self, content: str, max_tokens: int = 7000) -> bool:
        """Check if content is too large for Graphiti processing."""
        return self._estimate_tokens(content) > max_tokens

    async def delete_document_from_graph(self, document_source: str):
        """
        Delete all graph data associated with a specific document.
        
        Args:
            document_source: The document source/file_id to delete
        """
        if not self._graph_available:
            logger.info(f"Graph not available - skipping deletion for {document_source}")
            return

        if not self._initialized:
            await self.initialize()

        if self._graph_available and self.graph_client:
            try:
                logger.info(f"Deleting graph data for document: {document_source}")

                # Delete episodes by source_id (stored in source_description field)
                # Format: "source_id:{file_id}|Document: {title} (Chunk: {i})"
                await self.graph_client.delete_episodes_by_source_id(document_source)

                logger.info(f"Successfully deleted graph data for document: {document_source}")
            except Exception as e:
                logger.error(f"Error deleting graph data for {document_source}: {e}")
        else:
            logger.warning("Graph client not available for deletion")

    async def clear_graph(self):
        """Clear all data from the knowledge graph."""
        if not self._graph_available:
            logger.warning("Graph not available - cannot clear")
            return

        if not self._initialized:
            await self.initialize()

        if self._graph_available and self.graph_client:
            logger.warning("Clearing knowledge graph...")
            await self.graph_client.clear_graph()
            logger.info("Knowledge graph cleared")
        else:
            logger.warning("Graph client not available for clearing")

# Factory function
def create_graph_builder() -> GraphBuilder:
    """Create graph builder instance."""
    return GraphBuilder()

# Helper function for easy integration
async def add_chunks_to_graph(
    chunks: List[str],
    document_title: str,
    document_source: str,
    document_metadata: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Helper function to add chunks to graph with proper error handling.

    Args:
        chunks: List of text chunks
        document_title: Title of the document
        document_source: Source/ID of the document
        document_metadata: Optional metadata

    Returns:
        Result dictionary or None if graph unavailable
    """
    try:
        builder = create_graph_builder()
        await builder.initialize()

        if not builder._graph_available:
            logger.info("Graph builder not available - skipping graph processing")
            return None

        result = await builder.add_document_to_graph(
            chunks=chunks,
            document_title=document_title,
            document_source=document_source,
            document_metadata=document_metadata
        )

        await builder.close()
        return result

    except Exception as e:
        logger.error(f"Error in graph processing: {e}")
        return None

async def delete_document_from_graph(document_source: str) -> None:
    """
    Helper function to delete document graph data with proper error handling.

    Args:
        document_source: Source/ID of the document to delete
    """
    try:
        builder = create_graph_builder()
        await builder.initialize()

        if not builder._graph_available:
            logger.info("Graph builder not available - skipping graph deletion")
            return

        await builder.delete_document_from_graph(document_source)
        await builder.close()

    except Exception as e:
        logger.error(f"Error deleting graph data for {document_source}: {e}")