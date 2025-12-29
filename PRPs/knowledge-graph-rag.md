name: "Knowledge Graph Enhancement for RAG Pipeline"
description: |

## Purpose
Implement a production-ready knowledge graph enhancement to the existing RAG pipeline using Neo4j and Graphiti, enabling entity extraction, relationship mapping, and hybrid vector-graph search capabilities while maintaining backward compatibility with the current vector-only system.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Enhance the existing RAG pipeline with knowledge graph capabilities to provide structured entity relationships, temporal reasoning, and hybrid vector-graph search while maintaining full backward compatibility with the current vector-only implementation.

## Why
- **Business value**: Improved answer accuracy through entity relationships and multi-hop reasoning
- **User impact**: Better context understanding and more relevant document retrieval
- **Integration**: Seamlessly enhances existing RAG without breaking current functionality
- **Problems solved**: Addresses limitations of pure vector search for relationship queries, temporal reasoning, and entity-specific questions

## What
Implement a parallel knowledge graph processing pipeline alongside existing vector embeddings, adding:
- Entity extraction during document processing (companies, people, technologies, locations)
- Relationship mapping with temporal tracking using Graphiti's bi-temporal model
- Hybrid search combining vector similarity with graph traversal
- New agent tools for entity relationships and timeline queries

### Success Criteria
- [ ] Documents processed through both vector and graph pipelines successfully
- [ ] Agent can query both vector and graph stores for enhanced retrieval
- [ ] System gracefully handles Neo4j unavailability (fallback to vector-only)
- [ ] All existing tests pass with new implementation
- [ ] New graph-specific tests validate entity extraction and retrieval

## All Needed Context

### Documentation & References
```yaml
# MUST USE
- Use the Archon MCP server to search Graphiti and Pydantic AI documentation and use the project AI Agent Mastery Knowledge Graph for task management

# MUST READ - Include these in your context window
- url: https://github.com/getzep/graphiti
  why: Official Graphiti repository with examples and API documentation

- url: https://help.getzep.com/graphiti/getting-started/welcome
  why: Graphiti documentation for configuration and usage patterns

- file: PRPs/planning/knowledge-graph-analysis.md
  why: Comprehensive codebase analysis with integration points and file modifications

- file: PRPs/examples/ingestion/graph_builder.py
  why: Template for GraphBuilder class with proper token limit handling (8192 tokens)

- file: PRPs/examples/agent/graph_utils.py
  why: GraphitiClient wrapper with OpenAI-compatible configuration pattern

- file: backend_rag_pipeline/common/text_processor.py
  why: Existing chunking workflow to extend with entity extraction

- file: backend_agent_api/tools.py
  why: Tool registration patterns and retrieve_relevant_documents_tool to enhance

- file: backend_agent_api/agent.py
  why: Agent dependency injection and tool registration patterns

- docfile: CLAUDE.md
  why: Project conventions and requirements to follow
```

### Current Codebase tree (relevant portions)
```bash
backend_rag_pipeline/
├── common/
│   ├── text_processor.py       # Chunking and embedding generation
│   ├── db_handler.py           # Document processing and storage
│   └── state_manager.py        # Processing state tracking
├── Local_Files/
│   └── main.py                 # Local file watcher entry point
├── Google_Drive/
│   └── main.py                 # Google Drive watcher entry point
├── docker_entrypoint.py        # Docker container initialization
└── requirements.txt            # Python dependencies

backend_agent_api/
├── agent.py                    # Pydantic AI agent with tools
├── tools.py                    # Tool implementations
├── clients.py                  # Client configurations
├── agent_api.py               # FastAPI wrapper
└── requirements.txt           # Python dependencies
```

### Desired Codebase tree with files to be added
```bash
backend_rag_pipeline/
├── common/
│   ├── text_processor.py       # ENHANCED: Add entity extraction methods
│   ├── db_handler.py           # ENHANCED: Add graph building step
│   ├── graph_builder.py        # NEW: Knowledge graph construction
│   └── state_manager.py        # Existing
├── Local_Files/
│   └── main.py                 # ENHANCED: Initialize graph builder
├── Google_Drive/
│   └── main.py                 # ENHANCED: Initialize graph builder
├── docker_entrypoint.py        # ENHANCED: Neo4j initialization
└── requirements.txt            # ENHANCED: Add graphiti-core, neo4j

backend_agent_api/
├── agent.py                    # ENHANCED: Register graph tools
├── tools.py                    # ENHANCED: Add graph search tools
├── clients.py                  # ENHANCED: Add graph client config
├── graph_utils.py              # NEW: Graphiti client wrapper
├── agent_api.py                # ENHANCED: Initialize graph client
└── requirements.txt            # ENHANCED: Add graphiti-core, neo4j
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Graphiti has 8192 token limit per episode
# Solution: Chunk content to max 6000 characters before adding to graph
# Example: See PRPs/examples/ingestion/graph_builder.py lines 98-100

# CRITICAL: All Graphiti operations must be async
# Solution: Use consistent async/await patterns throughout
# Example: await graphiti.add_episode() not graphiti.add_episode()

# CRITICAL: Neo4j connection must be optional for backward compatibility
# Solution: Try/catch around graph initialization, continue if fails
# Example: if neo4j_available: init_graph() else: log.warning("Graph unavailable")

# CRITICAL: Use existing LLM/Embedding environment variables for Graphiti
# Solution: Reuse LLM_API_KEY, EMBEDDING_API_KEY, etc. from .env
# Example: See PRPs/examples/agent/graph_utils.py lines 53-68

# CRITICAL: Pydantic AI agent tools require specific registration pattern
# Solution: Use @agent.tool decorator with proper dependency injection
# Example: See backend_agent_api/agent.py lines 180-204

# CRITICAL: Graphiti automatically extracts entities and relationships
# Solution: Simply pass document chunks to add_episode() - no manual extraction needed
# Example: await graphiti.add_episode(name="doc_1", episode_body=chunk_text, source_description="Document")

# CRITICAL: Token usage optimization for LLM-based extraction
# Each episode uses tokens for: 1) Entity extraction 2) Relationship identification 3) Embeddings
# Solution: Balance chunk size at ~1000-2000 chars for optimal extraction quality vs token cost
# Larger chunks = better context for relationships but higher token usage
# Smaller chunks = lower cost but may miss cross-sentence relationships
```

## Implementation Blueprint

### Episode Processing Clarification

When adding document chunks to Graphiti, the system automatically:
1. **Extracts entities** from the text using the configured LLM (no manual NER needed)
2. **Identifies relationships** between entities within and across episodes
3. **Creates/updates graph nodes** with temporal tracking
4. **Generates embeddings** for semantic search

Simply pass document chunks directly to `add_episode()`:
```python
# Graphiti handles ALL entity extraction automatically
await graphiti.add_episode(
    name=f"{document_source}_{chunk_index}",
    episode_body=chunk.content,  # Just pass the raw text
    source_description=document_title
)
# No need for manual entity extraction - Graphiti's LLM does it all
```

### List of tasks to be completed to fulfill the PRP in order

```yaml
Task 1:
CREATE backend_rag_pipeline/common/graph_builder.py:
  - COPY from: PRPs/examples/ingestion/graph_builder.py
  - MODIFY import paths to match project structure
  - KEEP token limit handling at 6000 characters
  - PRESERVE async patterns throughout

Task 2:
CREATE backend_agent_api/graph_utils.py:
  - COPY from: PRPs/examples/agent/graph_utils.py
  - ADAPT environment variable names to match existing pattern
  - REUSE LLM_API_KEY, EMBEDDING_API_KEY from existing .env
  - KEEP OpenAIClient configuration pattern

Task 3:
MODIFY backend_rag_pipeline/common/db_handler.py:
  - FIND pattern: "async def process_file_for_rag"
  - INJECT after vector storage (around line 180)
  - ADD graph building call: await add_chunks_to_graph()
  - WRAP in try/except for graceful fallback
  - LOG success/failure of graph operations

Task 4:
MODIFY backend_rag_pipeline/Local_Files/main.py:
  - FIND pattern: "async def main()"
  - INJECT after watcher initialization (line 31)
  - INITIALIZE graph_builder = GraphBuilder()
  - ADD to file processing pipeline
  - ENSURE proper async context management

Task 5:
MODIFY backend_rag_pipeline/Google_Drive/main.py:
  - MIRROR changes from Local_Files/main.py
  - SAME initialization pattern
  - SAME error handling approach

Task 6:
MODIFY backend_agent_api/tools.py:
  - FIND pattern: end of file (after line 421)
  - ADD graph_search_tool() for semantic graph search
  - ADD entity_relationships_tool() for relationship queries
  - ADD entity_timeline_tool() for temporal queries
  - ENHANCE retrieve_relevant_documents_tool() with graph context

Task 7:
MODIFY backend_agent_api/agent.py:
  - FIND pattern: "class AgentDeps" (line 47)
  - ADD graph_client: Optional[GraphitiClient] = None
  - FIND pattern: tool registrations (after line 204)
  - REGISTER new graph tools with @agent.tool decorator
  - INJECT graph_client into tool dependencies

Task 8:
MODIFY backend_agent_api/clients.py:
  - FIND pattern: end of client configurations
  - ADD GraphitiClient initialization
  - FOLLOW existing client pattern
  - HANDLE connection errors gracefully

Task 9:
MODIFY backend_agent_api/agent_api.py:
  - FIND pattern: startup initialization
  - ADD graph client initialization
  - INJECT into AgentDeps
  - LOG initialization status

Task 10:
UPDATE backend_rag_pipeline/requirements.txt:
  - ADD graphiti-core>=0.3.0
  - ADD neo4j>=5.0.0
  - VERIFY no version conflicts

Task 11:
UPDATE backend_agent_api/requirements.txt:
  - MIRROR requirements from RAG pipeline
  - SAME versions for consistency

Task 12:
UPDATE backend_rag_pipeline/.env.example:
  - ADD Neo4j configuration variables
  - DOCUMENT required settings
  - PROVIDE sensible defaults

Task 13:
UPDATE backend_agent_api/.env.example:
  - MIRROR Neo4j configuration
  - SAME variable names
```

### Per task pseudocode

```python
# Task 1: graph_builder.py structure
class GraphBuilder:
    def __init__(self):
        self.graph_client = GraphitiClient()  # from graph_utils.py
        self._initialized = False

    async def add_document_to_graph(chunks, title, source, metadata):
        # CRITICAL: Optimize chunk size for token usage
        # Graphiti uses LLM for extraction, so balance quality vs cost
        for chunk in chunks:
            # Sweet spot: 1000-2000 chars for good context without excessive tokens
            if len(chunk.content) > 2000:
                chunk.content = chunk.content[:2000]

        # PATTERN: Process in small batches (3 chunks max) to manage token usage
        for batch in chunk_batches(chunks, 3):
            # Graphiti automatically extracts entities and relationships
            await graphiti.add_episode(
                name=f"{source}_{chunk.index}",
                episode_body=chunk.content,  # Just pass text - Graphiti does the rest
                source_description=title
            )
            # No manual entity extraction needed - LLM handles it internally

# Task 6: Graph search tool
async def graph_search_tool(
    ctx: RunContext[AgentDeps],
    query: str,
    search_type: str = "hybrid"
) -> str:
    """Search knowledge graph for entities and relationships."""
    # PATTERN: Check graph availability
    if not ctx.deps.graph_client:
        return "Graph search unavailable, using vector search only"

    # PATTERN: Try/catch for resilience
    try:
        # PATTERN: Use Graphiti's built-in hybrid search
        results = await ctx.deps.graph_client.search(
            query=query,
            search_type=search_type,  # "semantic", "bm25", or "hybrid"
            limit=10
        )

        # PATTERN: Format results for agent consumption
        return format_graph_results(results)
    except Exception as e:
        logger.error(f"Graph search failed: {e}")
        # FALLBACK: Return vector results
        return await retrieve_relevant_documents_tool(ctx, query)
```

### Integration Points
```yaml
DATABASE:
  - Neo4j: "bolt://localhost:7687" for graph storage
  - PostgreSQL/Supabase: Existing vector storage (unchanged)
  - Parallel storage: Both systems receive processed documents

CONFIG:
  - add to: backend_rag_pipeline/.env
  - pattern: "NEO4J_URI=bolt://localhost:7687"
  - pattern: "NEO4J_USER=neo4j"
  - pattern: "NEO4J_PASSWORD=your_password"

ROUTES:
  - NO new routes needed
  - Existing: POST /api/pydantic-agent enhanced with graph tools

INITIALIZATION:
  - Graph client: Initialize during startup
  - Fallback: Continue without graph if Neo4j unavailable
  - Logging: Clear status messages for debugging
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
cd backend_rag_pipeline
python -m ruff check common/graph_builder.py --fix
python -m mypy common/graph_builder.py

cd ../backend_agent_api
python -m ruff check graph_utils.py --fix
python -m mypy graph_utils.py

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests
```python
# CREATE backend_rag_pipeline/tests/test_graph_builder.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from common.graph_builder import GraphBuilder
from common.chunker import DocumentChunk

@pytest.mark.asyncio
async def test_graph_builder_initialization():
    """Graph builder initializes correctly"""
    builder = GraphBuilder()
    await builder.initialize()
    assert builder._initialized is True
    await builder.close()

@pytest.mark.asyncio
async def test_add_document_to_graph():
    """Documents are added to graph successfully"""
    builder = GraphBuilder()
    builder.graph_client = AsyncMock()

    chunks = [
        DocumentChunk(index=0, content="Test content", metadata={}),
        DocumentChunk(index=1, content="More content", metadata={})
    ]

    result = await builder.add_document_to_graph(
        chunks=chunks,
        document_title="Test Doc",
        document_source="test_source"
    )

    assert result["episodes_created"] == 2
    assert len(result["errors"]) == 0

@pytest.mark.asyncio
async def test_graph_unavailable_fallback():
    """System continues when graph is unavailable"""
    builder = GraphBuilder()
    builder.graph_client = None

    # Should not raise exception
    result = await builder.add_document_to_graph([], "Test", "source")
    assert result["episodes_created"] == 0

# CREATE backend_agent_api/tests/test_graph_tools.py
import pytest
from unittest.mock import AsyncMock
from tools import graph_search_tool, entity_relationships_tool
from agent import AgentDeps

@pytest.mark.asyncio
async def test_graph_search_with_results():
    """Graph search returns formatted results"""
    deps = AgentDeps()
    deps.graph_client = AsyncMock()
    deps.graph_client.search.return_value = [
        {"entity": "Python", "relationship": "USED_BY", "target": "Project"}
    ]

    ctx = AsyncMock()
    ctx.deps = deps

    result = await graph_search_tool(ctx, "Python usage")
    assert "Python" in result
    assert "USED_BY" in result

@pytest.mark.asyncio
async def test_graph_search_fallback():
    """Falls back to vector search when graph unavailable"""
    deps = AgentDeps()
    deps.graph_client = None

    ctx = AsyncMock()
    ctx.deps = deps

    result = await graph_search_tool(ctx, "test query")
    assert "Graph search unavailable" in result
```

```bash
# Run and iterate until passing:
cd backend_rag_pipeline
pytest tests/test_graph_builder.py -v

cd ../backend_agent_api
pytest tests/test_graph_tools.py -v

# If failing: Read error, understand root cause, fix code, re-run
```

## Final Validation Checklist
- [ ] All existing tests pass: `pytest backend_rag_pipeline/tests/ -v`
- [ ] All existing tests pass: `pytest backend_agent_api/tests/ -v`
- [ ] New graph tests pass: `pytest tests/test_graph_*.py -v`
- [ ] No linting errors: `ruff check backend_rag_pipeline/common/`
- [ ] No type errors: `mypy backend_rag_pipeline/common/`
- [ ] Fallback works: System continues without Neo4j
- [ ] Logs show clear graph initialization status
- [ ] Hybrid search combines vector and graph results

---

## Anti-Patterns to Avoid
- ❌ Don't break existing vector pipeline - graph is additive only
- ❌ Don't require Neo4j - system must work without it
- ❌ Don't exceed 6000 chars per Graphiti episode - token limit
- ❌ Don't use sync operations with Graphiti - all must be async
- ❌ Don't create new environment variables when existing ones work
- ❌ Don't skip error handling - every graph operation needs try/catch

## Performance Considerations
- Batch size: Process max 3 chunks at once for Graphiti (token limits)
- Rate limiting: Add 1-second delay between batches if needed
- Connection pooling: Reuse single GraphitiClient instance
- Caching: Consider caching entity extractions for repeated content

## Docker Deployment

The knowledge graph implementation requires configuration updates for Docker Compose:

### Docker Configuration
1. **Neo4j Deployment**: Neo4j must be deployed separately (not included in docker-compose.yml)
   - Can be run locally, in cloud, or as a separate Docker container
   - Default connection: bolt://localhost:7687
   - Configure credentials in .env file

2. **Environment Variables**: The docker-compose.yml has been updated to include:
   - `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` for both agent-api and rag-pipeline services
   - LLM credentials (already present) are reused by Graphiti for entity extraction
   - Services default to `bolt://localhost:7687` when Neo4j vars not set

3. **Setup Steps**:
   ```bash
   # Deploy Neo4j separately (example using Docker)
   docker run -d --name neo4j \
     -p 7474:7474 -p 7687:7687 \
     -e NEO4J_AUTH=neo4j/your_password \
     neo4j:latest

   # Configure connection in .env
   echo "NEO4J_URI=bolt://localhost:7687" >> .env
   echo "NEO4J_USER=neo4j" >> .env
   echo "NEO4J_PASSWORD=your_password" >> .env

   # Start application services
   docker compose up -d
   ```

4. **Graceful Fallback**: Services automatically run in vector-only mode if Neo4j is unavailable

## Confidence Score: 9/10
This PRP provides comprehensive context for successful implementation including:
- Complete file modification specifications with line numbers
- Working example code from PRPs/examples/ templates
- Specific error handling patterns for production resilience
- Validation tests at multiple levels
- Clear fallback behavior for backward compatibility

The implementation should succeed in one pass with this level of detail and context.