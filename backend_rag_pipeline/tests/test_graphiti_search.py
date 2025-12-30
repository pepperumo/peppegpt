"""
Test script for Graphiti search functionality.
Tests basic connection and search capabilities.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import pytest

if not os.getenv("ENABLE_GRAPHITI_TESTS"):
    pytest.skip("Graphiti tests disabled by default. Set ENABLE_GRAPHITI_TESTS=1 to run.", allow_module_level=True)

# Add the backend paths to sys.path
sys.path.insert(0, str(Path(__file__).parent / "backend_agent_api"))
sys.path.insert(0, str(Path(__file__).parent / "backend_rag_pipeline" / "common"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import after adding to path
from graph_utils import GraphitiClient, GRAPHITI_AVAILABLE


@pytest.mark.asyncio
@pytest.mark.skipif(not GRAPHITI_AVAILABLE, reason="Graphiti not available in this environment")
async def test_graphiti_search():
    """Test Graphiti search functionality."""
    print("=" * 80)
    print("GRAPHITI SEARCH TEST")
    print("=" * 80)

    # Check if Graphiti is available
    print(f"\n1. Checking Graphiti availability...")
    print(f"   Graphiti available: {GRAPHITI_AVAILABLE}")

    if not GRAPHITI_AVAILABLE:
        print("   ERROR: Graphiti is not installed!")
        return

    # Check environment variables
    print(f"\n2. Checking environment variables...")
    # Use localhost for local testing (not host.docker.internal)
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    if "host.docker.internal" in neo4j_uri:
        neo4j_uri = neo4j_uri.replace("host.docker.internal", "localhost")
        print(f"   Note: Replaced host.docker.internal with localhost for local testing")

    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    llm_api_key = os.getenv("LLM_API_KEY")

    print(f"   NEO4J_URI: {neo4j_uri}")
    print(f"   NEO4J_USER: {neo4j_user}")
    print(f"   NEO4J_PASSWORD: {'***' if neo4j_password else 'NOT SET'}")
    print(f"   LLM_API_KEY: {'***' if llm_api_key else 'NOT SET'}")

    if not all([neo4j_uri, neo4j_user, neo4j_password, llm_api_key]):
        print("   ERROR: Missing required environment variables!")
        return

    # Create and initialize client
    print(f"\n3. Creating Graphiti client...")
    try:
        client = GraphitiClient(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password
        )
        print("   [OK] Client created")
    except Exception as e:
        print(f"   ERROR creating client: {e}")
        return

    print(f"\n4. Initializing Graphiti client...")
    try:
        await client.initialize()
        print("   [OK] Client initialized")
        print(f"   LLM: {client.llm_choice}")
        print(f"   Embedder: {client.embedding_model}")
    except Exception as e:
        print(f"   ERROR initializing client: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test direct Graphiti search
    print(f"\n5. Testing direct Graphiti search...")
    test_queries = [
        "Dynamous",
        "big plans",
        "knowledge graph",
        "agent",
        "RAG",
        "test",
        ""  # Empty query to see what happens
    ]

    for query in test_queries:
        print(f"\n   Query: '{query}'")
        try:
            # Direct Graphiti search
            results = await client.graphiti.search(query) if query else []

            if results:
                print(f"   [FOUND] {len(results)} results:")
                for i, result in enumerate(results[:3]):  # Show first 3
                    print(f"      {i+1}. {result}")
                    # Try to access different attributes
                    if hasattr(result, '__dict__'):
                        print(f"         Attributes: {result.__dict__.keys()}")
            else:
                print(f"   [EMPTY] No results found")

            import pytest
        except Exception as e:
            print(f"   ERROR during search: {e}")
            import traceback
            traceback.print_exc()

    # Test wrapper search method
    print(f"\n6. Testing wrapper search method...")
    for query in ["Dynamous", "big plans"]:
        print(f"\n   Query: '{query}'")
        try:
            results = await client.search(query)

            if results:
                print(f"   [FOUND] {len(results)} results:")
                for i, result in enumerate(results[:3]):
                    print(f"      {i+1}. Fact: {result.get('fact', 'N/A')}")
                    print(f"         UUID: {result.get('uuid', 'N/A')}")
            else:
                print(f"   [EMPTY] No results found")
        except Exception as e:
            print(f"   ERROR: {e}")

    # Test getting graph statistics
    print(f"\n7. Testing graph statistics...")
    try:
        stats = await client.get_graph_statistics()
        print(f"   Graph stats: {stats}")
    except Exception as e:
        print(f"   ERROR getting stats: {e}")

    # Test raw Neo4j query to see if there's any data
    print(f"\n8. Testing raw Neo4j query...")
    try:
        # Access the Neo4j driver directly
        if hasattr(client.graphiti, 'driver'):
            async with client.graphiti.driver.session() as session:
                # Count all nodes by type
                result = await session.run("""
                    MATCH (n)
                    RETURN labels(n)[0] as label, count(n) as count
                    ORDER BY count DESC
                """)
                records = await result.data()
                if records:
                    print(f"   Node counts by type:")
                    for record in records:
                        print(f"      {record['label']}: {record['count']}")

                # Check for Fact nodes specifically (what Graphiti searches for)
                result = await session.run("MATCH (f:Fact) RETURN count(f) as fact_count")
                record = await result.single()
                if record:
                    print(f"   Total Fact nodes: {record['fact_count']}")

                    # Get sample Fact nodes if they exist
                    if record['fact_count'] > 0:
                        result = await session.run("MATCH (f:Fact) RETURN f LIMIT 3")
                        facts = await result.data()
                        print(f"   Sample Fact nodes:")
                        for fact in facts:
                            print(f"      {fact}")

                # Check for Episode nodes
                result = await session.run("MATCH (e:Episode) RETURN count(e) as episode_count")
                record = await result.single()
                if record:
                    print(f"   Total Episode nodes: {record['episode_count']}")

                    # Get sample Episode nodes if they exist
                    if record['episode_count'] > 0:
                        result = await session.run("MATCH (e:Episode) RETURN e.name, e.content LIMIT 3")
                        episodes = await result.data()
                        print(f"   Sample Episode nodes:")
                        for episode in episodes:
                            print(f"      Name: {episode['e.name']}")
                            print(f"      Content preview: {episode['e.content'][:200] if episode['e.content'] else 'No content'}...")

                # Check for Entity nodes
                result = await session.run("MATCH (en:Entity) RETURN count(en) as entity_count")
                record = await result.single()
                if record:
                    print(f"   Total Entity nodes: {record['entity_count']}")

                    if record['entity_count'] > 0:
                        result = await session.run("MATCH (en:Entity) RETURN en.name, en.summary LIMIT 5")
                        entities = await result.data()
                        print(f"   Sample Entity nodes:")
                        for entity in entities:
                            print(f"      - {entity['en.name']}: {entity['en.summary'][:100] if entity.get('en.summary') else 'No summary'}...")

                # Check for edges/relationships
                result = await session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
                records = await result.data()
                if records:
                    print(f"   Relationship counts:")
                    for record in records:
                        print(f"      {record['type']}: {record['count']}")
                else:
                    print(f"   No nodes found in graph")
        else:
            print("   Cannot access Neo4j driver directly")
    except Exception as e:
        print(f"   ERROR with raw query: {e}")
        import traceback
        traceback.print_exc()

    # Clean up
    print(f"\n9. Closing client...")
    await client.close()
    print("   [OK] Client closed")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_graphiti_search())