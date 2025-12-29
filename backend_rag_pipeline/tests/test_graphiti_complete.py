"""
Comprehensive test script for Graphiti functionality.
Tests adding episodes and searching for them.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add the backend paths to sys.path
sys.path.insert(0, str(Path(__file__).parent / "backend_agent_api"))
sys.path.insert(0, str(Path(__file__).parent / "backend_rag_pipeline" / "common"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import after adding to path
from graph_utils import GraphitiClient, GRAPHITI_AVAILABLE

async def test_graphiti_complete():
    """Complete test of Graphiti functionality."""
    print("=" * 80)
    print("GRAPHITI COMPLETE TEST")
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
    print(f"\n3. Creating and initializing Graphiti client...")
    try:
        client = GraphitiClient(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password
        )
        await client.initialize()
        print("   [OK] Client created and initialized")
        print(f"   LLM: {client.llm_choice}")
        print(f"   Embedder: {client.embedding_model}")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return

    # Clear the graph (optional - comment out if you want to keep existing data)
    print(f"\n4. Clearing existing graph data...")
    try:
        from graphiti_core.utils.maintenance.graph_data_operations import clear_data
        await clear_data(client.graphiti.driver)
        print("   [OK] Graph cleared")
    except Exception as e:
        print(f"   ERROR clearing graph: {e}")

    # Add test episodes
    print(f"\n5. Adding test episodes to graph...")
    test_episodes = [
        {
            "id": "test_episode_1",
            "content": "Dynamous is growing rapidly. The company has big plans to reach 10,000 members by next year. These ambitious goals show the company's vision for expansion.",
            "source": "Company Strategy Document"
        },
        {
            "id": "test_episode_2",
            "content": "The knowledge graph system uses Neo4j and Graphiti to store and retrieve information. RAG pipelines process documents and extract entities and relationships.",
            "source": "Technical Documentation"
        },
        {
            "id": "test_episode_3",
            "content": "Building the best AI agent in the world requires advanced techniques like knowledge graphs, vector databases, and hybrid search capabilities.",
            "source": "AI Development Plan"
        }
    ]

    episodes_added = []
    for episode in test_episodes:
        try:
            # Import EpisodeType for proper source handling
            from graphiti_core.nodes import EpisodeType

            await client.graphiti.add_episode(
                name=episode["id"],
                episode_body=episode["content"],
                source=EpisodeType.text,
                source_description=episode["source"],
                reference_time=datetime.now(timezone.utc)
            )
            episodes_added.append(episode["id"])
            print(f"   [OK] Added episode: {episode['id']}")
        except Exception as e:
            print(f"   ERROR adding episode {episode['id']}: {e}")

    if not episodes_added:
        print("   ERROR: No episodes were added successfully")
        await client.close()
        return

    # Wait a moment for processing
    print(f"\n6. Waiting for graph processing...")
    await asyncio.sleep(3)

    # Check what was created in the graph
    print(f"\n7. Checking graph contents...")
    try:
        if hasattr(client.graphiti, 'driver'):
            async with client.graphiti.driver.session() as session:
                # Count nodes by type
                result = await session.run("""
                    MATCH (n)
                    RETURN labels(n)[0] as label, count(n) as count
                    ORDER BY count DESC
                """)
                records = await result.data()
                if records:
                    print("   Node counts by type:")
                    for record in records:
                        print(f"      {record['label']}: {record['count']}")

                # Get sample Entity nodes
                result = await session.run("""
                    MATCH (e:Entity)
                    RETURN e.name as name
                    ORDER BY e.name
                    LIMIT 10
                """)
                entities = await result.data()
                if entities:
                    print("   Entities found:")
                    for entity in entities:
                        print(f"      - {entity['name']}")

                # Get sample Fact nodes if they exist
                result = await session.run("""
                    MATCH (f:Fact)
                    RETURN f.fact as fact
                    LIMIT 5
                """)
                facts = await result.data()
                if facts:
                    print("   Facts found:")
                    for fact in facts:
                        print(f"      - {fact['fact'][:100]}...")
    except Exception as e:
        print(f"   ERROR checking graph: {e}")

    # Test various search methods
    print(f"\n8. Testing search functionality...")
    test_queries = [
        "Dynamous",
        "knowledge graph",
        "10000 members",
        "big plans",
        "AI agent",
        "Neo4j",
        "RAG pipeline",
        "What are the company's plans?",
        "How does the knowledge graph work?"
    ]

    for query in test_queries:
        print(f"\n   Query: '{query}'")
        try:
            # Try the standard search
            results = await client.graphiti.search(query)

            if results:
                print(f"   [FOUND] {len(results)} results")
                for i, result in enumerate(results[:2]):  # Show first 2
                    # Print whatever attributes the result has
                    if hasattr(result, 'fact'):
                        print(f"      {i+1}. Fact: {result.fact[:100]}...")
                    elif hasattr(result, '__dict__'):
                        print(f"      {i+1}. Result: {result.__dict__}")
                    else:
                        print(f"      {i+1}. Result: {result}")
            else:
                print(f"   [EMPTY] No results found")

        except Exception as e:
            print(f"   ERROR during search: {e}")

    # Try retrieve method if it exists
    print(f"\n9. Testing retrieve method...")
    try:
        if hasattr(client.graphiti, 'retrieve'):
            for query in ["Dynamous", "knowledge graph"]:
                print(f"\n   Retrieve query: '{query}'")
                results = await client.graphiti.retrieve(query)
                if results:
                    print(f"   [FOUND] {len(results)} results")
                else:
                    print(f"   [EMPTY] No results")
        else:
            print("   Retrieve method not available")
    except Exception as e:
        print(f"   ERROR: {e}")

    # Try a raw embedding search
    print(f"\n10. Testing raw embedding search...")
    try:
        # Get embedding for a test query
        test_query = "Dynamous company growth"

        # Try to use the embedder directly
        if hasattr(client.graphiti, 'embedder'):
            embedding = await client.graphiti.embedder.embed(test_query)
            print(f"   Generated embedding for: '{test_query}'")
            print(f"   Embedding dimensions: {len(embedding)}")

            # Search for similar nodes using embeddings
            async with client.graphiti.driver.session() as session:
                # Find nodes with embeddings
                result = await session.run("""
                    MATCH (n)
                    WHERE n.embedding IS NOT NULL
                    RETURN labels(n)[0] as label, count(*) as count
                """)
                records = await result.data()
                if records:
                    print("   Nodes with embeddings:")
                    for record in records:
                        print(f"      {record['label']}: {record['count']}")
        else:
            print("   Embedder not directly accessible")
    except Exception as e:
        print(f"   ERROR: {e}")

    # Clean up
    print(f"\n11. Closing client...")
    await client.close()
    print("   [OK] Client closed")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_graphiti_complete())