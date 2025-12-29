"""
Graph utilities for Neo4j/Graphiti integration.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

# Check if we're in production
is_production = os.getenv("ENVIRONMENT") == "production"

if not is_production:
    # Development: prioritize .env file
    project_root = Path(__file__).resolve().parent
    dotenv_path = project_root / '.env'
    load_dotenv(dotenv_path, override=True)
else:
    # Production: use cloud platform env vars only
    load_dotenv()

# Try to import Graphiti components
try:
    from graphiti_core import Graphiti
    from graphiti_core.utils.maintenance.graph_data_operations import clear_data
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.llm_client.openai_client import OpenAIClient
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
    from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
    GRAPHITI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Graphiti not available: {e}")
    GRAPHITI_AVAILABLE = False

class GraphitiClient:
    """Manages Graphiti knowledge graph operations."""

    def __init__(
        self,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None
    ):
        """
        Initialize Graphiti client.

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        if not GRAPHITI_AVAILABLE:
            raise ImportError("Graphiti is not installed. Please install graphiti-core and neo4j packages.")

        # Neo4j configuration
        self.neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = neo4j_user or os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD")

        if not self.neo4j_password:
            raise ValueError("NEO4J_PASSWORD environment variable not set")

        # Reuse existing LLM configuration from environment
        self.llm_base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.llm_api_key = os.getenv("LLM_API_KEY")
        self.llm_choice = os.getenv("LLM_CHOICE", "gpt-4o-mini")

        if not self.llm_api_key:
            raise ValueError("LLM_API_KEY environment variable not set")

        # Reuse existing embedding configuration from environment
        self.embedding_base_url = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")
        self.embedding_api_key = os.getenv("EMBEDDING_API_KEY")
        self.embedding_model = os.getenv("EMBEDDING_MODEL_CHOICE", "text-embedding-3-small")

        # Determine embedding dimensions based on model
        if "text-embedding-3-small" in self.embedding_model:
            self.embedding_dimensions = 1536
        elif "text-embedding-3-large" in self.embedding_model:
            self.embedding_dimensions = 3072
        elif "nomic" in self.embedding_model.lower():
            self.embedding_dimensions = 768
        else:
            self.embedding_dimensions = int(os.getenv("VECTOR_DIMENSION", "1536"))

        if not self.embedding_api_key:
            raise ValueError("EMBEDDING_API_KEY environment variable not set")

        self.graphiti: Optional[Any] = None
        self._initialized = False

    async def initialize(self):
        """Initialize Graphiti client."""
        if self._initialized:
            return

        if not GRAPHITI_AVAILABLE:
            raise ImportError("Graphiti is not available")

        try:
            # Create LLMConfig with both model and small_model
            llm_config = LLMConfig(
                api_key=self.llm_api_key,
                model=self.llm_choice,
                small_model=self.llm_choice,  # Use same model for small operations
                base_url=self.llm_base_url
            )

            # Create OpenAI LLM client
            llm_client = OpenAIClient(config=llm_config)

            # Create OpenAI embedder with explicit API key
            embedder = OpenAIEmbedder(
                config=OpenAIEmbedderConfig(
                    api_key=self.embedding_api_key,
                    embedding_model=self.embedding_model,
                    embedding_dim=self.embedding_dimensions,
                    base_url=self.embedding_base_url
                )
            )

            # Create cross encoder for reranking
            cross_encoder = OpenAIRerankerClient(client=llm_client, config=llm_config)

            # Initialize Graphiti with custom clients including cross encoder
            self.graphiti = Graphiti(
                self.neo4j_uri,
                self.neo4j_user,
                self.neo4j_password,
                llm_client=llm_client,
                embedder=embedder,
                cross_encoder=cross_encoder
            )

            # Build indices and constraints
            await self.graphiti.build_indices_and_constraints()

            self._initialized = True
            logger.info(f"Graphiti client initialized successfully with LLM: {self.llm_choice} and embedder: {self.embedding_model}")

        except Exception as e:
            logger.error(f"Failed to initialize Graphiti: {e}")
            raise

    async def close(self):
        """Close Graphiti connection."""
        if self.graphiti:
            await self.graphiti.close()
            self.graphiti = None
            self._initialized = False
            logger.info("Graphiti client closed")

    async def add_episode(
        self,
        episode_id: str,
        content: str,
        source: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add an episode to the knowledge graph.

        Args:
            episode_id: Unique episode identifier
            content: Episode content
            source: Source of the content
            timestamp: Episode timestamp
            metadata: Additional metadata
        """
        if not self._initialized:
            await self.initialize()

        episode_timestamp = timestamp or datetime.now(timezone.utc)

        # Import EpisodeType for proper source handling
        from graphiti_core.nodes import EpisodeType

        await self.graphiti.add_episode(
            name=episode_id,
            episode_body=content,
            source=EpisodeType.text,  # Always use text type for our content
            source_description=source,
            reference_time=episode_timestamp
        )

        logger.info(f"Added episode {episode_id} to knowledge graph")

    async def search(
        self,
        query: str,
        center_node_distance: int = 2,
        use_hybrid_search: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge graph.

        Args:
            query: Search query
            center_node_distance: Distance from center nodes
            use_hybrid_search: Whether to use hybrid search

        Returns:
            Search results
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Use Graphiti's search method
            results = await self.graphiti.search(query)

            # Convert results to dictionaries
            return [
                {
                    "fact": result.fact,
                    "uuid": str(result.uuid),
                    "valid_at": str(result.valid_at) if hasattr(result, 'valid_at') and result.valid_at else None,
                    "invalid_at": str(result.invalid_at) if hasattr(result, 'invalid_at') and result.invalid_at else None,
                    "source_node_uuid": str(result.source_node_uuid) if hasattr(result, 'source_node_uuid') and result.source_node_uuid else None
                }
                for result in results
            ]

        except Exception as e:
            logger.error(f"Graph search failed: {e}")
            return []

    async def get_related_entities(
        self,
        entity_name: str,
        relationship_types: Optional[List[str]] = None,
        depth: int = 1
    ) -> Dict[str, Any]:
        """
        Get entities related to a given entity using Graphiti search.

        Args:
            entity_name: Name of the entity
            relationship_types: Types of relationships to follow (not used with Graphiti)
            depth: Maximum depth to traverse (not used with Graphiti)

        Returns:
            Related entities and relationships
        """
        if not self._initialized:
            await self.initialize()

        # Use Graphiti search to find related information about the entity
        results = await self.graphiti.search(f"relationships involving {entity_name}")

        # Extract entity information from the search results
        related_entities = set()
        facts = []

        for result in results:
            facts.append({
                "fact": result.fact,
                "uuid": str(result.uuid),
                "valid_at": str(result.valid_at) if hasattr(result, 'valid_at') and result.valid_at else None
            })

            # Simple entity extraction from fact text (could be enhanced)
            if entity_name.lower() in result.fact.lower():
                related_entities.add(entity_name)

        return {
            "central_entity": entity_name,
            "related_facts": facts,
            "search_method": "graphiti_semantic_search"
        }

    async def get_entity_timeline(
        self,
        entity_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get timeline of facts for an entity using Graphiti.

        Args:
            entity_name: Name of the entity
            start_date: Start of time range (not currently used)
            end_date: End of time range (not currently used)

        Returns:
            Timeline of facts
        """
        if not self._initialized:
            await self.initialize()

        # Search for temporal information about the entity
        results = await self.graphiti.search(f"timeline history of {entity_name}")

        timeline = []
        for result in results:
            timeline.append({
                "fact": result.fact,
                "uuid": str(result.uuid),
                "valid_at": str(result.valid_at) if hasattr(result, 'valid_at') and result.valid_at else None,
                "invalid_at": str(result.invalid_at) if hasattr(result, 'invalid_at') and result.invalid_at else None
            })

        # Sort by valid_at if available
        timeline.sort(key=lambda x: x.get('valid_at') or '', reverse=True)

        return timeline

    async def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Get basic statistics about the knowledge graph.

        Returns:
            Graph statistics
        """
        if not self._initialized:
            await self.initialize()

        # For now, return a simple search to verify the graph is working
        # More detailed statistics would require direct Neo4j access
        try:
            test_results = await self.graphiti.search("test")
            return {
                "graphiti_initialized": True,
                "sample_search_results": len(test_results),
                "note": "Detailed statistics require direct Neo4j access"
            }
        except Exception as e:
            return {
                "graphiti_initialized": False,
                "error": str(e)
            }

    async def clear_graph(self):
        """Clear all data from the graph (USE WITH CAUTION)."""
        if not self._initialized:
            await self.initialize()

        try:
            # Use Graphiti's proper clear_data function with the driver
            await clear_data(self.graphiti.driver)
            logger.warning("Cleared all data from knowledge graph")
        except Exception as e:
            logger.error(f"Failed to clear graph: {e}")
            raise

# Factory function for creating graph client
def create_graph_client() -> Optional[GraphitiClient]:
    """
    Create a GraphitiClient instance if possible.

    Returns:
        GraphitiClient instance or None if unavailable
    """
    if not GRAPHITI_AVAILABLE:
        logger.warning("Graphiti not available - graph features disabled")
        return None

    try:
        # Check for required environment variables
        if not os.getenv("NEO4J_PASSWORD"):
            logger.warning("NEO4J_PASSWORD not set - graph features disabled")
            return None

        return GraphitiClient()
    except Exception as e:
        logger.warning(f"Failed to create graph client: {e}")
        return None

# Global graph client instance (initialized lazily)
_graph_client = None

async def get_graph_client() -> Optional[GraphitiClient]:
    """
    Get or create the global graph client instance.

    Returns:
        GraphitiClient instance or None if unavailable
    """
    global _graph_client

    if _graph_client is None:
        _graph_client = create_graph_client()
        if _graph_client:
            try:
                await _graph_client.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize graph client: {e}")
                _graph_client = None

    return _graph_client

# Convenience functions for common operations
async def add_to_knowledge_graph(
    content: str,
    source: str,
    episode_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Add content to the knowledge graph.

    Args:
        content: Content to add
        source: Source of the content
        episode_id: Optional episode ID
        metadata: Optional metadata

    Returns:
        Episode ID or None if graph unavailable
    """
    client = await get_graph_client()
    if not client:
        return None

    if not episode_id:
        episode_id = f"episode_{datetime.now(timezone.utc).isoformat()}"

    await client.add_episode(
        episode_id=episode_id,
        content=content,
        source=source,
        metadata=metadata
    )

    return episode_id

async def search_knowledge_graph(query: str) -> List[Dict[str, Any]]:
    """
    Search the knowledge graph.

    Args:
        query: Search query

    Returns:
        Search results or empty list if graph unavailable
    """
    client = await get_graph_client()
    if not client:
        return []

    return await client.search(query)

async def get_entity_relationships(
    entity: str,
    depth: int = 2
) -> Optional[Dict[str, Any]]:
    """
    Get relationships for an entity.

    Args:
        entity: Entity name
        depth: Maximum traversal depth

    Returns:
        Entity relationships or None if graph unavailable
    """
    client = await get_graph_client()
    if not client:
        return None

    return await client.get_related_entities(entity, depth=depth)

async def test_graph_connection() -> bool:
    """
    Test graph database connection.

    Returns:
        True if connection successful
    """
    try:
        client = await get_graph_client()
        if not client:
            return False

        stats = await client.get_graph_statistics()
        logger.info(f"Graph connection successful. Stats: {stats}")
        return stats.get("graphiti_initialized", False)
    except Exception as e:
        logger.error(f"Graph connection test failed: {e}")
        return False