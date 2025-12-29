# FEATURE: Knowledge Graph Integration for Enhanced RAG

This feature enhances the existing RAG AI agent and pipeline by integrating Neo4j-based knowledge graphs using the Graphiti library. The knowledge graph will work alongside the existing vector database to provide structured entity relationships, temporal reasoning, and semantic graph search capabilities.

## Backend RAG Pipeline (backend_rag_pipeline/ folder)
We will need to implement:
- Knowledge graph builder module that processes document chunks to extract entities and relationships using Graphiti
- Integration with the existing text processing pipeline to build knowledge graph episodes alongside vector embeddings
- Graph utilities for managing Neo4j connections and Graphiti client initialization
- Entity extraction during chunking phase to identify companies, technologies, people, and locations
- Batch processing for efficient knowledge graph construction with proper token limit handling for Graphiti

### Key Integration Points:
- **common/text_processor.py**: Add entity extraction post-processing after chunking
- **common/db_handler.py**: Add parallel knowledge graph ingestion alongside vector storage
- **NEW: common/graph_builder.py**: Create module for Graphiti integration and episode management
- **docker_entrypoint.py**: Initialize graph client during pipeline startup
- **Local_Files/main.py & Google_Drive/main.py**: Add graph building step after document processing

## Backend Agent API (backend_agent_api/ folder)
We will need to implement:
- Knowledge graph search tools for the Pydantic AI agent to query entity relationships and facts
- Graph utilities module to manage Graphiti client and Neo4j connections
- Integration of graph search results with existing RAG context for enhanced responses
- Tools for entity timeline queries, relationship exploration, and semantic graph search

### Key Integration Points:
- **tools.py**: Add new graph search tools (graph_search_tool, entity_relationships_tool, entity_timeline_tool)
- **agent.py**: Register new graph tools with the Pydantic agent
- **clients.py**: Add Graphiti/Neo4j client initialization
- **NEW: graph_utils.py**: Create module for graph operations and Graphiti wrapper
- **agent_api.py**: Initialize graph client on API startup

### API Tools Required:
- CREATE: `graph_search_tool` - Semantic search across knowledge graph facts
- CREATE: `entity_relationships_tool` - Get related entities and their connections
- CREATE: `entity_timeline_tool` - Query temporal information about entities
- UPDATE: `retrieve_relevant_documents_tool` - Enhance with graph context alongside vector results

## Database Schema Updates
No SQL schema changes required - Neo4j operates as a separate graph database alongside the existing PostgreSQL/Supabase setup. The knowledge graph maintains its own structure through Graphiti's schema management.

## DOCUMENTATION
- Use the Archon MCP server to search Graphiti and Pydantic AI documentation
- Use web search (supplemental) for Graphiti best practices

## EXAMPLES

### Critical Implementation Reference from PRPs/examples/

The examples folder contains a complete working implementation that serves as our blueprint:

#### 1. **Graph Building Pipeline (PRPs/examples/ingestion/graph_builder.py)**
- **GraphBuilder class**: Manages Graphiti client and episode creation
- **add_document_to_graph()**: Processes chunks into knowledge graph episodes with proper token limits
- **Entity extraction methods**: Extract companies, technologies, people, and locations
- **Key pattern**: Batch processing with 6000 character limit per episode to avoid Graphiti token limits
- **Error handling**: Continue processing even if individual chunks fail

#### 2. **Graph Utilities (PRPs/examples/agent/graph_utils.py)**
- **GraphitiClient class**: Wrapper for Graphiti operations with OpenAI-compatible configuration
- **Custom LLM/Embedder setup**: Shows how to configure Graphiti with our existing OpenAI/Ollama providers
- **Core methods**: add_episode(), search(), get_related_entities(), get_entity_timeline()
- **Initialization pattern**: Lazy initialization with proper client configuration

#### 3. **Agent Tools Integration (PRPs/examples/agent/tools.py)**
- **graph_search_tool**: Semantic search returning facts with UUIDs and validity periods
- **entity_relationship_tool**: Query entity connections with configurable depth
- **entity_timeline_tool**: Temporal queries for entity evolution
- **Tool registration pattern**: Pydantic BaseModel inputs with proper field descriptions

#### 4. **Environment Configuration (PRPs/examples/.env.example)**
- **NEO4J_URI**: bolt://localhost:7687 (standard Neo4j connection)
- **NEO4J_USER/PASSWORD**: Neo4j authentication credentials
- **Reuse existing LLM/Embedding configs**: Share providers between vector and graph systems

## OTHER CONSIDERATIONS
- Output a setup guide in planning/knowledge-graph-setup.md after implementation detailing Neo4j installation steps, Graphiti requirements, and configuration
- Add NEO4J environment variables to all .env.example files (backend_agent_api and backend_rag_pipeline)
- Implement proper error handling for graph operations to prevent pipeline failures
- Maintain backward compatibility - the system should work without Neo4j if not configured
- Use async/await patterns consistently for all graph operations
- Implement connection pooling for Neo4j to handle concurrent requests
- Refrain from editing the requirements.txt files - instead just output at the end the packages that need to be added - let's use Graphiti 0.18.0

## Environment Variables Needed
### Backend RAG Pipeline & Agent API
```
# Neo4j Configuration (for Knowledge Graph)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# Reuse existing LLM and embedding configurations
# The graph will use the same providers configured for the main system
```

## Docker Deployment

The knowledge graph feature requires updates to Docker Compose configuration:

### Docker Configuration
- **Neo4j Service**: Must be deployed separately (not included in docker-compose.yml)
  - Can run as standalone Docker container, cloud service, or local installation
  - Connection defaults to bolt://localhost:7687
  - Configure credentials via environment variables

- **Environment Variables**: Updated in docker-compose.yml
  - Add `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` to both services
  - Existing LLM credentials should be reused by Graphiti for entity extraction
  - Services gracefully fallback to vector-only mode if Neo4j unavailable

## Implementation Priority
1. First implement graph utilities and Graphiti client wrapper in both backend folders
2. Add graph building to RAG pipeline with entity extraction
3. Integrate graph search tools into the agent
4. Test end-to-end with sample documents
5. Add monitoring and optimization