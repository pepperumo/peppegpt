#!/usr/bin/env python3
"""
Utility script to clean up Neo4j knowledge graph data.
Use this to manually remove orphaned entities or clear specific document data.
"""

import asyncio
import sys
from common.graph_utils import GraphitiClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def clear_all_graph_data():
    """Clear ALL data from the knowledge graph (USE WITH CAUTION!)"""
    print("⚠️  WARNING: This will delete ALL data from the Neo4j knowledge graph!")
    confirm = input("Type 'DELETE ALL' to confirm: ")
    
    if confirm != "DELETE ALL":
        print("❌ Aborted. No data was deleted.")
        return
    
    client = GraphitiClient()
    await client.initialize()
    
    try:
        await client.clear_graph()
        print("✅ Knowledge graph cleared successfully")
    except Exception as e:
        print(f"❌ Error clearing graph: {e}")
    finally:
        await client.close()


async def delete_document_data(file_id: str):
    """Delete all graph data for a specific document/file."""
    print(f"🔄 Deleting graph data for file: {file_id}")
    
    client = GraphitiClient()
    await client.initialize()
    
    try:
        await client.delete_episodes_by_metadata("document_source", file_id)
        print(f"✅ Graph data deleted for file: {file_id}")
    except Exception as e:
        print(f"❌ Error deleting graph data: {e}")
    finally:
        await client.close()


async def clean_orphaned_entities():
    """Remove Entity nodes that have no connections to any Episodic nodes."""
    print("🔄 Finding and removing orphaned entities...")
    
    client = GraphitiClient()
    await client.initialize()
    
    try:
        if not client.graphiti:
            print("❌ Graph client not initialized")
            return
            
        # Query to find and delete orphaned entities
        query = """
        MATCH (entity:Entity)
        WHERE NOT (entity)--(:Episodic)
        OPTIONAL MATCH (entity)-[r]-()
        DELETE r, entity
        RETURN count(entity) as deleted_count
        """
        
        async with client.graphiti.driver.session() as session:
            result = await session.run(query)
            record = await result.single()
            deleted = record["deleted_count"] if record else 0
            print(f"✅ Deleted {deleted} orphaned entities")
            
    except Exception as e:
        print(f"❌ Error cleaning orphaned entities: {e}")
    finally:
        await client.close()


async def list_graph_stats():
    """Show statistics about the knowledge graph."""
    client = GraphitiClient()
    await client.initialize()
    
    try:
        if not client.graphiti:
            print("❌ Graph client not initialized")
            return
            
        async with client.graphiti.driver.session() as session:
            # Count episodes
            result = await session.run("MATCH (e:Episodic) RETURN count(e) as count")
            episodes = (await result.single())["count"]
            
            # Count entities
            result = await session.run("MATCH (e:Entity) RETURN count(e) as count")
            entities = (await result.single())["count"]
            
            # Count relationships
            result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            relationships = (await result.single())["count"]
            
            # List document sources
            result = await session.run("""
                MATCH (e:Episodic)
                WHERE e.document_source IS NOT NULL
                RETURN DISTINCT e.document_source as source
                ORDER BY source
            """)
            sources = [record["source"] async for record in result]
            
            print("\n📊 Knowledge Graph Statistics:")
            print(f"   Episodes (chunks): {episodes}")
            print(f"   Entities: {entities}")
            print(f"   Relationships: {relationships}")
            print(f"\n📁 Document sources ({len(sources)}):")
            for source in sources:
                print(f"   - {source}")
                
    except Exception as e:
        print(f"❌ Error getting graph stats: {e}")
    finally:
        await client.close()


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("""
Usage: python cleanup_graph.py <command> [args]

Commands:
  stats                     - Show knowledge graph statistics
  clear                     - Clear ALL graph data (requires confirmation)
  delete <file_id>          - Delete graph data for specific document
  clean-orphans             - Remove orphaned Entity nodes
  
Examples:
  python cleanup_graph.py stats
  python cleanup_graph.py delete 163nzP5MW7SsUBZGJTerXL1pNMmA23h6W
  python cleanup_graph.py clean-orphans
  python cleanup_graph.py clear
""")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "stats":
        await list_graph_stats()
    elif command == "clear":
        await clear_all_graph_data()
    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ Error: file_id required")
            print("Usage: python cleanup_graph.py delete <file_id>")
            sys.exit(1)
        file_id = sys.argv[2]
        await delete_document_data(file_id)
    elif command == "clean-orphans":
        await clean_orphaned_entities()
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
