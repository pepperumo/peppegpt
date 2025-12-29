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
    project_root = Path(__file__).resolve().parent.parent
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
            # Suppress Neo4j informational notifications about existing indexes
            import logging
            neo4j_logger = logging.getLogger('neo4j.notifications')
            original_level = neo4j_logger.level
            neo4j_logger.setLevel(logging.WARNING)
            try:
                await self.graphiti.build_indices_and_constraints()
            finally:
                neo4j_logger.setLevel(original_level)

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
        metadata: Optional[Dict[str, Any]] = None,
        display_name: Optional[str] = None
    ):
        """
        Add an episode to the knowledge graph.

        Args:
            episode_id: Unique episode identifier (for internal tracking)
            content: Episode content
            source: Source of the content
            timestamp: Episode timestamp
            metadata: Additional metadata
            display_name: Human-readable name for graph visualization (defaults to episode_id)
        """
        if not self._initialized:
            await self.initialize()

        if not self.graphiti:
            raise RuntimeError("Graphiti client not initialized")

        episode_timestamp = timestamp or datetime.now(timezone.utc)

        # Import EpisodeType for proper source handling
        from graphiti_core.nodes import EpisodeType

        # Use display_name for visualization, fallback to episode_id
        name_for_graph = display_name or episode_id

        await self.graphiti.add_episode(
            name=name_for_graph,
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

        if not self.graphiti:
            raise RuntimeError("Graphiti client not initialized")

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

        if not self.graphiti:
            raise RuntimeError("Graphiti client not initialized")

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

        if not self.graphiti:
            raise RuntimeError("Graphiti client not initialized")

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

        if not self.graphiti:
            return {
                "graphiti_initialized": False,
                "error": "Graphiti client not initialized"
            }

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

    async def delete_episodes_by_metadata(self, metadata_key: str, metadata_value: str):
        """
        Delete all episodes (and their associated nodes/edges) that match the given metadata.
        Also deletes Entity nodes that are only connected to these episodes (orphaned entities).

        Args:
            metadata_key: The metadata key to filter by (e.g., "document_source")
            metadata_value: The metadata value to match (e.g., file_id)
        """
        if not self._initialized:
            await self.initialize()

        if not self.graphiti:
            raise RuntimeError("Graphiti client not initialized")

        try:
            async with self.graphiti.driver.session() as session:
                # Step 1: Find and collect Entity nodes connected to episodes we're about to delete
                find_entities_query = """
                MATCH (e:Episodic)-[r]-(entity:Entity)
                WHERE e.`{key}` = $value
                WITH entity, collect(DISTINCT e) as connected_episodes
                RETURN entity.uuid as entity_uuid,
                       size(connected_episodes) as episode_count
                """.format(key=metadata_key)

                result = await session.run(find_entities_query, value=metadata_value)
                entities_to_check = []
                async for record in result:
                    entities_to_check.append({
                        'uuid': record['entity_uuid'],
                        'episode_count': record['episode_count']
                    })

                logger.info(f"Found {len(entities_to_check)} entities connected to episodes with {metadata_key}={metadata_value}")

                # Step 2: Delete episodes with matching metadata and their direct relationships
                delete_episodes_query = """
                MATCH (e:Episodic)
                WHERE e.`{key}` = $value
                OPTIONAL MATCH (e)-[r]-()
                DELETE r, e
                RETURN count(e) as deleted_count
                """.format(key=metadata_key)

                result = await session.run(delete_episodes_query, value=metadata_value)
                record = await result.single()
                deleted_episodes = record["deleted_count"] if record else 0
                logger.info(f"Deleted {deleted_episodes} episodes for {metadata_key}={metadata_value}")

                # Step 3: Delete Entity nodes that are now orphaned (no remaining connections)
                deleted_entities = 0
                for entity_info in entities_to_check:
                    # Check if entity still has connections to other episodes
                    check_query = """
                    MATCH (entity:Entity {uuid: $uuid})
                    OPTIONAL MATCH (entity)--(other:Episodic)
                    WITH entity, count(other) as remaining_connections
                    WHERE remaining_connections = 0
                    OPTIONAL MATCH (entity)-[r]-()
                    DELETE r, entity
                    RETURN count(entity) as deleted
                    """

                    result = await session.run(check_query, uuid=entity_info['uuid'])
                    record = await result.single()
                    if record and record['deleted'] > 0:
                        deleted_entities += 1

                logger.info(f"Deleted {deleted_entities} orphaned entities for {metadata_key}={metadata_value}")
                logger.info(f"Total cleanup: {deleted_episodes} episodes + {deleted_entities} entities")

        except Exception as e:
            logger.error(f"Failed to delete episodes by metadata: {e}")
            raise

    async def delete_episodes_by_source_id(self, source_id: str):
        """
        Delete all episodes that have the given source_id in their source_description.
        The source_description format is: "source_id:{file_id}|Document: {title} (Chunk: {i})"

        Args:
            source_id: The file_id/document_source to delete
        """
        if not self._initialized:
            await self.initialize()

        if not self.graphiti:
            raise RuntimeError("Graphiti client not initialized")

        search_pattern = f"source_id:{source_id}|"

        try:
            async with self.graphiti.driver.session() as session:
                # Step 1: Find entities connected to episodes we're about to delete
                find_entities_query = """
                MATCH (e:Episodic)-[r]-(entity:Entity)
                WHERE e.source_description STARTS WITH $pattern
                WITH entity, collect(DISTINCT e) as connected_episodes
                RETURN entity.uuid as entity_uuid,
                       size(connected_episodes) as episode_count
                """

                result = await session.run(find_entities_query, pattern=search_pattern)
                entities_to_check = []
                async for record in result:
                    entities_to_check.append({
                        'uuid': record['entity_uuid'],
                        'episode_count': record['episode_count']
                    })

                logger.info(f"Found {len(entities_to_check)} entities connected to episodes with source_id={source_id}")

                # Step 2: Delete episodes with matching source_description
                delete_episodes_query = """
                MATCH (e:Episodic)
                WHERE e.source_description STARTS WITH $pattern
                OPTIONAL MATCH (e)-[r]-()
                DELETE r, e
                RETURN count(e) as deleted_count
                """

                result = await session.run(delete_episodes_query, pattern=search_pattern)
                record = await result.single()
                deleted_episodes = record["deleted_count"] if record else 0
                logger.info(f"Deleted {deleted_episodes} episodes for source_id={source_id}")

                # Step 3: Delete orphaned Entity nodes
                deleted_entities = 0
                for entity_info in entities_to_check:
                    check_query = """
                    MATCH (entity:Entity {uuid: $uuid})
                    OPTIONAL MATCH (entity)--(other:Episodic)
                    WITH entity, count(other) as remaining_connections
                    WHERE remaining_connections = 0
                    OPTIONAL MATCH (entity)-[r]-()
                    DELETE r, entity
                    RETURN count(entity) as deleted
                    """

                    result = await session.run(check_query, uuid=entity_info['uuid'])
                    record = await result.single()
                    if record and record['deleted'] > 0:
                        deleted_entities += 1

                logger.info(f"Deleted {deleted_entities} orphaned entities for source_id={source_id}")
                logger.info(f"Total cleanup: {deleted_episodes} episodes + {deleted_entities} entities")

        except Exception as e:
            logger.error(f"Failed to delete episodes by source_id: {e}")
            raise

    async def get_all_source_ids(self) -> List[str]:
        """
        Get all unique source_ids from Neo4j episodes.
        Extracts file_id from source_description format: "source_id:{file_id}|..."

        Returns:
            List of unique source_ids (file_ids)
        """
        if not self._initialized:
            await self.initialize()

        if not self.graphiti:
            raise RuntimeError("Graphiti client not initialized")

        try:
            async with self.graphiti.driver.session() as session:
                query = """
                MATCH (e:Episodic)
                WHERE e.source_description STARTS WITH 'source_id:'
                WITH e.source_description as desc
                WITH split(desc, '|')[0] as source_part
                WITH replace(source_part, 'source_id:', '') as source_id
                RETURN DISTINCT source_id
                """
                result = await session.run(query)
                source_ids = []
                async for record in result:
                    if record['source_id']:
                        source_ids.append(record['source_id'])
                return source_ids

        except Exception as e:
            logger.error(f"Failed to get source_ids from Neo4j: {e}")
            return []

    async def cleanup_orphaned_episodes(self, valid_source_ids: List[str]) -> Dict[str, int]:
        """
        Delete episodes whose source_id is not in the valid_source_ids list.
        This cleans up orphan data when files are deleted from the main database.

        Args:
            valid_source_ids: List of source_ids that should remain (from Supabase)

        Returns:
            Dict with deleted_episodes and deleted_entities counts
        """
        if not self._initialized:
            await self.initialize()

        if not self.graphiti:
            raise RuntimeError("Graphiti client not initialized")

        # Get all source_ids currently in Neo4j
        neo4j_source_ids = await self.get_all_source_ids()
        logger.info(f"Found {len(neo4j_source_ids)} source_ids in Neo4j")

        # Find orphaned source_ids (in Neo4j but not in valid list)
        orphaned_ids = set(neo4j_source_ids) - set(valid_source_ids)
        logger.info(f"Found {len(orphaned_ids)} orphaned source_ids to clean up")

        total_deleted_episodes = 0
        total_deleted_entities = 0

        for source_id in orphaned_ids:
            try:
                logger.info(f"Cleaning up orphaned data for source_id: {source_id}")
                await self.delete_episodes_by_source_id(source_id)
                # Count is logged inside delete_episodes_by_source_id
            except Exception as e:
                logger.error(f"Failed to cleanup source_id {source_id}: {e}")

        return {
            "orphaned_source_ids": len(orphaned_ids),
            "source_ids_cleaned": list(orphaned_ids)
        }

    async def clear_graph(self):
        """Clear all data from the graph (USE WITH CAUTION)."""
        if not self._initialized:
            await self.initialize()

        if not self.graphiti:
            raise RuntimeError("Graphiti client not initialized")

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


async def cleanup_orphaned_graph_data(valid_file_ids: List[str]) -> Optional[Dict[str, Any]]:
    """
    Clean up orphaned graph data that no longer has corresponding entries in Supabase.
    Call this on pipeline startup to sync Neo4j with the main database.

    Args:
        valid_file_ids: List of file_ids that exist in Supabase document_metadata

    Returns:
        Cleanup results or None if graph unavailable
    """
    try:
        client = await get_graph_client()
        if not client:
            logger.info("Graph client not available - skipping orphan cleanup")
            return None

        logger.info("Starting orphaned graph data cleanup...")
        result = await client.cleanup_orphaned_episodes(valid_file_ids)
        logger.info(f"Orphan cleanup complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Failed to cleanup orphaned graph data: {e}")
        return None