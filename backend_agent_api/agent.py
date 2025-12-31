from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerHTTP
from dataclasses import dataclass
from dotenv import load_dotenv
from openai import AsyncOpenAI
from httpx import AsyncClient
from supabase import Client
from pathlib import Path
from typing import List, Any
import os

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

from prompt import AGENT_SYSTEM_PROMPT
from tools import (
    web_search_tool,
    image_analysis_tool,
    retrieve_relevant_documents_tool,
    list_documents_tool,
    get_document_content_tool,
    execute_sql_query_tool,
    execute_safe_code_tool,
    graph_search_tool,
    entity_relationships_tool,
    entity_timeline_tool
)
from mcp_ui_tools import create_calendly_widget, create_github_widget

# ========== Helper function to get model configuration ==========
def get_model():
    llm = os.getenv('LLM_CHOICE') or 'gpt-4o-mini'
    base_url = os.getenv('LLM_BASE_URL') or 'https://api.openai.com/v1'
    api_key = os.getenv('LLM_API_KEY') or 'ollama'

    return OpenAIModel(llm, provider=OpenAIProvider(base_url=base_url, api_key=api_key))


def is_web_search_enabled() -> bool:
    """Toggle web search tool via env flag.

    WEB_SEARCH_ENABLED accepts: true/1/on/yes (default) or false/0/off/no.
    """
    raw = os.getenv("WEB_SEARCH_ENABLED")
    if raw is None:
        return True
    return raw.strip().lower() not in {"false", "0", "off", "no"}

# ========== Pydantic AI Agent ==========
@dataclass
class AgentDeps:
    supabase: Client
    embedding_client: AsyncOpenAI
    http_client: AsyncClient
    brave_api_key: str | None
    searxng_base_url: str | None
    memories: str
    web_search_enabled: bool = True
    graph_client: Any = None  # Optional GraphitiClient
    ui_resources: List[dict] = None  # Store UI resources generated during the conversation

    def __post_init__(self):
        if self.ui_resources is None:
            self.ui_resources = []

    def add_ui_resource(self, resource: dict):
        """Add a UI resource to be sent with the response."""
        self.ui_resources.append(resource)

# To use the code execution MCP server:
# First uncomment the line below that defines 'code_execution_server', then also uncomment 'mcp_servers=[code_execution_server]'
# Start this in a separate terminal with this command after installing Deno:
# deno run -N -R=node_modules -W=node_modules --node-modules-dir=auto jsr:@pydantic/mcp-run-python sse
# Instructions for installing Deno here: https://github.com/denoland/deno/
# Pydantic AI docs for this MCP server: https://ai.pydantic.dev/mcp/run-python/
# code_execution_server = MCPServerHTTP(url='http://localhost:3001/sse')  

agent = Agent(
    get_model(),
    system_prompt=AGENT_SYSTEM_PROMPT,
    deps_type=AgentDeps,
    retries=2,
    instrument=True,
    # mcp_servers=[code_execution_server]
)

@agent.system_prompt  
def add_memories(ctx: RunContext[str]) -> str:
    return f"\nUser Memories:\n{ctx.deps.memories}"

@agent.tool
async def web_search(ctx: RunContext[AgentDeps], query: str) -> str:
    """
    Search the web with a specific query and get a summary of the top search results.
    
    Args:
        ctx: The context for the agent including the HTTP client and optional Brave API key/SearXNG base url
        query: The query for the web search
        
    Returns:
        A summary of the web search.
        For Brave, this is a single paragraph.
        For SearXNG, this is a list of the top search results including the most relevant snippet from the page.
    """
    print("Calling web_search tool")
    if not ctx.deps.web_search_enabled:
        return "Web search is disabled by configuration."

    if not ctx.deps.brave_api_key and not ctx.deps.searxng_base_url:
        return "Web search is not configured (no Brave API key or SearXNG base URL)."

    return await web_search_tool(query, ctx.deps.http_client, ctx.deps.brave_api_key, ctx.deps.searxng_base_url)    

@agent.tool
async def retrieve_relevant_documents(ctx: RunContext[AgentDeps], user_query: str) -> str:
    """
    Retrieve relevant document chunks based on the query with RAG.
    Enhanced with knowledge graph search when available.

    Args:
        ctx: The context including the Supabase client and OpenAI client
        user_query: The user's question or query

    Returns:
        A formatted string containing the top 4 most relevant documents chunks plus graph context
    """
    print("Calling retrieve_relevant_documents tool")
    return await retrieve_relevant_documents_tool(
        ctx.deps.supabase,
        ctx.deps.embedding_client,
        user_query,
        ctx.deps.graph_client
    )

@agent.tool
async def list_documents(ctx: RunContext[AgentDeps]) -> List[str]:
    """
    Retrieve a list of all available documents.
    
    Returns:
        List[str]: List of documents including their metadata (URL/path, schema if applicable, etc.)
    """
    print("Calling list_documents tool")
    return await list_documents_tool(ctx.deps.supabase)

@agent.tool
async def get_document_content(ctx: RunContext[AgentDeps], document_id: str) -> str:
    """
    Retrieve the full content of a specific document by combining all its chunks.
    
    Args:
        ctx: The context including the Supabase client
        document_id: The ID (or file path) of the document to retrieve
        
    Returns:
        str: The full content of the document with all chunks combined in order
    """
    print("Calling get_document_content tool")
    return await get_document_content_tool(ctx.deps.supabase, document_id)

@agent.tool
async def execute_sql_query(ctx: RunContext[AgentDeps], sql_query: str) -> str:
    """
    Run a SQL query - use this to query from the document_rows table once you know the file ID you are querying. 
    dataset_id is the file_id and you are always using the row_data for filtering, which is a jsonb field that has 
    all the keys from the file schema given in the document_metadata table.

    Never use a placeholder file ID. Always use the list_documents tool first to get the file ID.

    Example query:

    SELECT AVG((row_data->>'revenue')::numeric)
    FROM document_rows
    WHERE dataset_id = '123';

    Example query 2:

    SELECT 
        row_data->>'category' as category,
        SUM((row_data->>'sales')::numeric) as total_sales
    FROM document_rows
    WHERE dataset_id = '123'
    GROUP BY row_data->>'category';
    
    Args:
        ctx: The context including the Supabase client
        sql_query: The SQL query to execute (must be read-only)
        
    Returns:
        str: The results of the SQL query in JSON format
    """
    print(f"Calling execute_sql_query tool with SQL: {sql_query }")
    return await execute_sql_query_tool(ctx.deps.supabase, sql_query)    

@agent.tool
async def image_analysis(ctx: RunContext[AgentDeps], document_id: str, query: str) -> str:
    """
    Analyzes an image based on the document ID of the image provided.
    This function pulls the binary of the image from the knowledge base
    and passes that into a subagent with a vision LLM
    Before calling this tool, call list_documents to see the images available
    and to get the exact document ID for the image.
    
    Args:
        ctx: The context including the Supabase client
        document_id: The ID (or file path) of the image to analyze
        query: What to extract from the image analysis
        
    Returns:
        str: An analysis of the image based on the query
    """
    print("Calling image_analysis tool")
    return await image_analysis_tool(ctx.deps.supabase, document_id, query)    

# Using the MCP server instead for code execution, but you can use this simple version
# if you don't want to use MCP for whatever reason! Just uncomment the line below:
@agent.tool
async def execute_code(ctx: RunContext[AgentDeps], code: str) -> str:
    """
    Executes a given Python code string in a protected environment.
    Use print to output anything that you need as a result of executing the code.

    Args:
        code: Python code to execute

    Returns:
        str: Anything printed out to standard output with the print command
    """
    print(f"executing code: {code}")
    print(f"Result is: {execute_safe_code_tool(code)}")
    return execute_safe_code_tool(code)

@agent.tool
async def graph_search(ctx: RunContext[AgentDeps], query: str) -> str:
    """
    Search the knowledge graph for facts, entities, and relationships.
    Useful for finding specific information about entities and their connections.

    Args:
        ctx: The context including the graph client
        query: Search query for the knowledge graph

    Returns:
        Formatted knowledge graph search results
    """
    print(f"Calling graph_search tool with query: {query}")
    if not ctx.deps.graph_client:
        return "Knowledge graph not available - please use retrieve_relevant_documents instead"
    return await graph_search_tool(ctx.deps.graph_client, query)

@agent.tool
async def entity_relationships(ctx: RunContext[AgentDeps], entity_name: str, depth: int = 2) -> str:
    """
    Get relationships and connections for a specific entity from the knowledge graph.
    Shows how entities are connected to other entities, concepts, and facts.

    Args:
        ctx: The context including the graph client
        entity_name: Name of the entity to find relationships for
        depth: How many relationship levels to traverse (default: 2)

    Returns:
        Formatted entity relationship information
    """
    print(f"Calling entity_relationships tool for entity: {entity_name}")
    if not ctx.deps.graph_client:
        return "Knowledge graph not available - please use retrieve_relevant_documents instead"
    return await entity_relationships_tool(ctx.deps.graph_client, entity_name, depth)

@agent.tool
async def entity_timeline(ctx: RunContext[AgentDeps], entity_name: str) -> str:
    """
    Get a temporal timeline of facts and events for a specific entity.
    Shows how information about an entity has evolved over time.

    Args:
        ctx: The context including the graph client
        entity_name: Name of the entity to get timeline for

    Returns:
        Formatted timeline of entity facts and events
    """
    print(f"Calling entity_timeline tool for entity: {entity_name}")
    if not ctx.deps.graph_client:
        return "Knowledge graph not available - please use retrieve_relevant_documents instead"
    return await entity_timeline_tool(ctx.deps.graph_client, entity_name)


# ============================================================================
# MCP-UI Widget Tools - Interactive UI components for the chat
# ============================================================================

@agent.tool
async def show_booking_widget(ctx: RunContext[AgentDeps]) -> str:
    """
    Display an interactive Calendly booking widget so users can schedule a call with Giuseppe.
    Use this tool when the user wants to book a meeting, schedule a call, or set up an interview.

    Returns:
        A confirmation message. The widget will be displayed automatically.
    """
    print("Calling show_booking_widget tool")
    widget = create_calendly_widget()
    # Store UI resource in deps to be sent with API response
    ctx.deps.add_ui_resource(widget.to_dict())
    return "The Calendly booking widget has been displayed. The user can now select a time slot to schedule a call with Giuseppe."


@agent.tool
async def show_github_projects(ctx: RunContext[AgentDeps]) -> str:
    """
    Display Giuseppe's GitHub profile and repositories widget.
    Use this tool when users want to see his code samples, GitHub projects, open source work, or technical portfolio.

    Returns:
        A confirmation message. The GitHub widget will be displayed automatically.
    """
    print("Calling show_github_projects tool")

    # Fetch real repos from GitHub API
    username = "pepperumo"
    repos = []

    try:
        response = await ctx.deps.http_client.get(
            f"https://api.github.com/users/{username}/repos",
            params={"sort": "updated", "per_page": 10},
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        print(f"GitHub API response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            repos = [
                {
                    "name": repo["name"],
                    "description": repo["description"] or "No description",
                    "language": repo["language"],
                    "stars": repo["stargazers_count"],
                    "url": repo["html_url"]
                }
                for repo in data
                if not repo["fork"]  # Exclude forks
            ][:6]
            print(f"Fetched {len(repos)} repos: {[r['name'] for r in repos]}")
    except Exception as e:
        print(f"Error fetching GitHub repos: {e}")

    widget = create_github_widget(username=username, repos=repos)
    print(f"Created GitHub widget with URI: {widget.uri}")
    ctx.deps.add_ui_resource(widget.to_dict())
    print(f"UI resources count after add: {len(ctx.deps.ui_resources)}")
    return f"Giuseppe's GitHub profile and {len(repos)} repositories have been displayed. Users can click on any repo to view it on GitHub."