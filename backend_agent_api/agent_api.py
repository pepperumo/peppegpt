from typing import List, Optional, Dict, Any, AsyncIterator, Union, Tuple
from fastapi import FastAPI, HTTPException, Security, Depends, Request, Form
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager, nullcontext
from supabase import create_client, Client
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from dotenv import load_dotenv
from httpx import AsyncClient
from pathlib import Path
from mem0 import Memory
import asyncio
import base64
import time
import json
import sys
import os

# Import Langfuse configuration
from configure_langfuse import configure_langfuse

# Import database utility functions
from db_utils import (
    fetch_conversation_history,
    create_conversation,
    update_conversation_title,
    generate_session_id,
    generate_conversation_title,
    store_message,
    convert_history_to_pydantic_format,
    check_rate_limit,
    store_request
)

from pydantic_ai import Agent, BinaryContent
# Import all the message part classes from Pydantic AI
from pydantic_ai.messages import (
    ModelMessage, ModelRequest, ModelResponse, TextPart, ModelMessagesTypeAdapter,
    UserPromptPart, PartDeltaEvent, PartStartEvent, TextPartDelta
)

from agent import agent, AgentDeps, get_model
from clients import get_agent_clients, get_mem0_client_async, get_graph_client, initialize_graph_client

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

# Define clients as None initially
embedding_client = None
supabase = None
http_client = None
title_agent = None
mem0_client = None
tracer = None
graph_client = None

# Define the lifespan context manager for the application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application.
    
    Handles initialization and cleanup of resources.
    """
    global embedding_client, supabase, http_client, title_agent, mem0_client, tracer, graph_client

    # Initialize Langfuse tracer (returns None if not configured)
    tracer = configure_langfuse()

    # Startup: Initialize all clients
    embedding_client, supabase = get_agent_clients()
    http_client = AsyncClient()
    title_agent = Agent(model=get_model())
    mem0_client = await get_mem0_client_async()

    # Initialize graph client (optional - won't fail if not available)
    graph_client = get_graph_client()
    if graph_client:
        graph_client = await initialize_graph_client(graph_client)
        if graph_client:
            print("✓ Knowledge graph client initialized")
        else:
            print("⚠ Knowledge graph client failed to connect")
    else:
        print("ⓘ Knowledge graph not configured")
    
    yield  # This is where the app runs
    
    # Shutdown: Clean up resources
    if http_client:
        await http_client.aclose()

# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)
security = HTTPBearer()        

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """
    Verify the JWT token from Supabase and return the user information.
    
    Args:
        credentials: The HTTP Authorization credentials containing the bearer token
        
    Returns:
        Dict[str, Any]: The user information from Supabase
        
    Raises:
        HTTPException: If the token is invalid or the user cannot be verified
    """
    try:
        # Get the token from the Authorization header
        token = credentials.credentials
        
        # Access the global HTTP client
        global http_client # noqa: F824
        if not http_client:
            raise HTTPException(status_code=500, detail="HTTP client not initialized")
        
        # Get the Supabase URL and anon key from environment variables
        # These should match the environment variable names used in your project
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        # Make request to Supabase auth API to get user info using the global HTTP client
        response = await http_client.get(
            f"{supabase_url}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": supabase_key
            }
        )
        
        # Check if the request was successful
        if response.status_code != 200:
            print(f"Auth response error: {response.text}")
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        
        # Return the user information
        user_data = response.json()
        return user_data
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

# Request/Response Models
class FileAttachment(BaseModel):
    fileName: str
    content: str  # Base64 encoded content
    mimeType: str

class AgentRequest(BaseModel):
    query: str
    user_id: str
    request_id: str
    session_id: str
    files: Optional[List[FileAttachment]] = None


# Add this helper function to your backend code
async def stream_error_response(error_message: str, session_id: str):
    """
    Creates a streaming response for error messages.
    
    Args:
        error_message: The error message to display to the user
        session_id: The current session ID
        
    Yields:
        Encoded JSON chunks for the streaming response
    """
    # First yield the error message as text
    yield json.dumps({"text": error_message}).encode('utf-8') + b'\n'
    
    # Then yield a final chunk with complete flag
    final_data = {
        "text": error_message,
        "session_id": session_id,
        "error": error_message,
        "complete": True
    }
    yield json.dumps(final_data).encode('utf-8') + b'\n'

@app.post("/api/pydantic-agent")
async def pydantic_agent(request: AgentRequest, user: Dict[str, Any] = Depends(verify_token)):
    # Verify that the user ID in the request matches the user ID from the token
    if request.user_id != user.get("id"):
        return StreamingResponse(
            stream_error_response("User ID in request does not match authenticated user", request.session_id),
            media_type='text/plain'
        )
        
    try:
        # Check rate limit
        rate_limit_ok = await check_rate_limit(supabase, request.user_id)
        if not rate_limit_ok:
            return StreamingResponse(
                stream_error_response("Rate limit exceeded. Please try again later.", request.session_id),
                media_type='text/plain'
            )
        
        # Start request tracking in parallel
        request_tracking_task = asyncio.create_task(
            store_request(supabase, request.request_id, request.user_id, request.query)
        )
        
        session_id = request.session_id
        conversation_record = None
        conversation_title = None
        
        # Check if session_id is empty, create a new conversation if needed
        if not session_id:
            session_id = generate_session_id(request.user_id)
            # Create a new conversation record
            conversation_record = await create_conversation(supabase, request.user_id, session_id)
        
        # Store user's query immediately with any file attachments
        file_attachments = None
        if request.files:
            # Convert Pydantic models to dictionaries for storage
            file_attachments = [{
                "fileName": file.fileName,
                "content": file.content,
                "mimeType": file.mimeType
            } for file in request.files]
            
        await store_message(
            supabase=supabase,
            session_id=session_id,
            message_type="human",
            content=request.query,
            files=file_attachments
        )
        
        # Fetch conversation history from the DB
        conversation_history = await fetch_conversation_history(supabase, session_id)
        
        # Convert conversation history to Pydantic AI format
        pydantic_messages = await convert_history_to_pydantic_format(conversation_history)
        
        # Retrieve relevant memories with Mem0
        relevant_memories = {"results": []}
        try:
            relevant_memories = await mem0_client.search(query=request.query, user_id=request.user_id, limit=3)
        except:
            # Slight hack - retry again with a new connection pool
            time.sleep(1)
            relevant_memories = await mem0_client.search(query=request.query, user_id=request.user_id, limit=3)

        memories_str = "\n".join(f"- {entry['memory']}" for entry in relevant_memories["results"])
        
        # Create memory task to run in parallel
        memory_messages = [{"role": "user", "content": request.query}]
        memory_task = asyncio.create_task(mem0_client.add(memory_messages, user_id=request.user_id))
        
        # Start title generation in parallel if this is a new conversation
        title_task = None
        if conversation_record:
            title_task = asyncio.create_task(generate_conversation_title(title_agent, request.query))
        
        async def stream_response():
            # Process title result if it exists (in the background)
            nonlocal conversation_title

            # Use the global HTTP client
            agent_deps = AgentDeps(
                embedding_client=embedding_client,
                supabase=supabase,
                http_client=http_client,
                brave_api_key=os.getenv("BRAVE_API_KEY", ""),
                searxng_base_url=os.getenv("SEARXNG_BASE_URL", ""),
                memories=memories_str,
                graph_client=graph_client
            )
            
            # Process any file attachments for the agent
            binary_contents = []
            if request.files:
                for file in request.files:
                    try:
                        # Decode the base64 content
                        binary_data = base64.b64decode(file.content)
                        # Create a BinaryContent object
                        fileMimeType = "application/pdf" if file.mimeType == "text/plain" else file.mimeType
                        binary_content = BinaryContent(
                            data=binary_data,
                            media_type=fileMimeType
                        )
                        binary_contents.append(binary_content)
                    except Exception as e:
                        print(f"Error processing file {file.fileName}: {str(e)}")
            
            # Create input for the agent with the query and any binary contents
            agent_input = [request.query]
            if binary_contents:
                agent_input.extend(binary_contents)
            
            full_response = ""
            
            # Use tracer context if available, otherwise use nullcontext
            span_context = tracer.start_as_current_span("Pydantic-Ai-Trace") if tracer else nullcontext()
            
            with span_context as span:
                if tracer and span:
                    # Set user and session attributes for Langfuse
                    span.set_attribute("langfuse.user.id", request.user_id)
                    span.set_attribute("langfuse.session.id", session_id)
                    span.set_attribute("input.value", request.query)
                
                # Run the agent with the user prompt, binary contents, and the chat history
                async with agent.iter(agent_input, deps=agent_deps, message_history=pydantic_messages) as run:
                    async for node in run:
                        if Agent.is_model_request_node(node):
                            # A model request node => We can stream tokens from the model's request
                            async with node.stream(run.ctx) as request_stream:
                                async for event in request_stream:
                                    if isinstance(event, PartStartEvent) and event.part.part_kind == 'text':
                                        yield json.dumps({"text": event.part.content}).encode('utf-8') + b'\n'
                                        full_response += event.part.content
                                    elif isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                                        delta = event.delta.content_delta
                                        yield json.dumps({"text": full_response}).encode('utf-8') + b'\n'
                                        full_response += delta
                
                # Set the output value after completion if tracing
                if tracer and span:
                    span.set_attribute("output.value", full_response)
                    
            # After streaming is complete, store the full response in the database
            message_data = run.result.new_messages_json()
            
            # Store agent's response
            await store_message(
                supabase=supabase,
                session_id=session_id,
                message_type="ai",
                content=full_response,
                message_data=message_data,
                data={"request_id": request.request_id}
            )
            
            # Wait for title generation to complete if it's running
            if title_task:
                try:
                    title_result = await title_task
                    conversation_title = title_result
                    # Update the conversation title in the database
                    await update_conversation_title(supabase, session_id, conversation_title)
                    
                    # Send the final title in the last chunk
                    final_data = {
                        "text": full_response,
                        "session_id": session_id,
                        "conversation_title": conversation_title,
                        "complete": True
                    }
                    yield json.dumps(final_data).encode('utf-8') + b'\n'
                except Exception as e:
                    print(f"Error processing title: {str(e)}")
            else:
                yield json.dumps({"text": full_response, "complete": True}).encode('utf-8') + b'\n'

            # Wait for the memory task to complete if needed
            try:
                await memory_task
            except Exception as e:
                print(f"Error updating memories: {str(e)}")
                
            # Wait for request tracking task to complete
            try:
                await request_tracking_task
            except Exception as e:
                print(f"Error tracking request: {str(e)}")
            except asyncio.CancelledError:
                # This is expected if the task was cancelled
                pass
        
        return StreamingResponse(stream_response(), media_type='text/plain')

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        # Store error message in conversation if session_id exists
        if request.session_id:
            await store_message(
                supabase=supabase,
                session_id=request.session_id,
                message_type="ai",
                content="I apologize, but I encountered an error processing your request.",
                data={"error": str(e), "request_id": request.request_id}
            )
        # Return a streaming response with the error
        return StreamingResponse(
            stream_error_response(f"Error: {str(e)}", request.session_id),
            media_type='text/plain'
        )


# ============================================================================
# Web Sources API Models
# ============================================================================

class WebSourceCreate(BaseModel):
    """Request model for creating a new web source."""
    url: str
    crawl_depth: Optional[int] = 1
    crawl_interval_hours: Optional[int] = None


class WebSourceResponse(BaseModel):
    """Response model for a web source."""
    id: str
    user_id: str
    url: str
    title: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    chunks_count: int = 0
    last_crawled_at: Optional[str] = None
    created_at: str
    updated_at: str
    crawl_depth: int = 1
    crawl_interval_hours: Optional[int] = None


class WebSourceListResponse(BaseModel):
    """Response model for listing web sources."""
    sources: List[WebSourceResponse]
    total: int


# ============================================================================
# Web Sources API Endpoints
# ============================================================================

@app.get("/api/web-sources", response_model=WebSourceListResponse)
async def list_web_sources(user: Dict[str, Any] = Depends(verify_token)):
    """
    List all web sources for the authenticated user.

    Args:
        user: The authenticated user from the JWT token

    Returns:
        WebSourceListResponse: List of web sources with total count
    """
    try:
        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        # Query web_sources table for this user
        response = supabase.table("web_sources").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()

        sources = response.data if response.data else []

        return WebSourceListResponse(
            sources=[WebSourceResponse(**source) for source in sources],
            total=len(sources)
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error listing web sources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list web sources: {str(e)}")


@app.post("/api/web-sources", response_model=WebSourceResponse, status_code=201)
async def create_web_source(
    web_source: WebSourceCreate,
    user: Dict[str, Any] = Depends(verify_token)
):
    """
    Add a new URL to crawl for the authenticated user.

    Args:
        web_source: The web source data to create
        user: The authenticated user from the JWT token

    Returns:
        WebSourceResponse: The created web source
    """
    try:
        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        # Validate URL format
        if not web_source.url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Invalid URL format. URL must start with http:// or https://")

        # Check if URL already exists for this user
        existing = supabase.table("web_sources").select("id").eq("user_id", user_id).eq("url", web_source.url).execute()
        if existing.data:
            raise HTTPException(status_code=409, detail="This URL already exists in your web sources")

        # Create the web source record
        now = datetime.now(timezone.utc).isoformat()
        new_source = {
            "user_id": user_id,
            "url": web_source.url,
            "status": "pending",
            "crawl_depth": web_source.crawl_depth or 1,
            "crawl_interval_hours": web_source.crawl_interval_hours,
            "created_at": now,
            "updated_at": now
        }

        response = supabase.table("web_sources").insert(new_source).execute()

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create web source")

        created_source = response.data[0]
        return WebSourceResponse(**created_source)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating web source: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create web source: {str(e)}")


@app.delete("/api/web-sources/{source_id}", status_code=204)
async def delete_web_source(
    source_id: str,
    user: Dict[str, Any] = Depends(verify_token)
):
    """
    Remove a web source for the authenticated user.

    Args:
        source_id: The ID of the web source to delete
        user: The authenticated user from the JWT token

    Returns:
        None (204 No Content on success)
    """
    try:
        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        # Check if the web source exists and belongs to this user
        existing = supabase.table("web_sources").select("id").eq("id", source_id).eq("user_id", user_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Web source not found")

        # Delete the web source
        supabase.table("web_sources").delete().eq("id", source_id).eq("user_id", user_id).execute()

        return None

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting web source: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete web source: {str(e)}")


@app.post("/api/web-sources/{source_id}/recrawl", response_model=WebSourceResponse)
async def recrawl_web_source(
    source_id: str,
    user: Dict[str, Any] = Depends(verify_token)
):
    """
    Trigger a re-crawl of a web source for the authenticated user.

    This endpoint updates the status to 'pending' to trigger the crawl pipeline
    to re-process the URL.

    Args:
        source_id: The ID of the web source to re-crawl
        user: The authenticated user from the JWT token

    Returns:
        WebSourceResponse: The updated web source with pending status
    """
    try:
        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        # Check if the web source exists and belongs to this user
        existing = supabase.table("web_sources").select("*").eq("id", source_id).eq("user_id", user_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Web source not found")

        # Update the status to pending to trigger re-crawl
        now = datetime.now(timezone.utc).isoformat()
        update_data = {
            "status": "pending",
            "updated_at": now
        }

        response = supabase.table("web_sources").update(update_data).eq("id", source_id).eq("user_id", user_id).execute()

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to trigger re-crawl")

        updated_source = response.data[0]
        return WebSourceResponse(**updated_source)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error triggering re-crawl: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger re-crawl: {str(e)}")


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint for container orchestration and monitoring.

    Returns:
        Dict with status and service health information
    """
    # Check if critical dependencies are initialized
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "embedding_client": embedding_client is not None,
            "supabase": supabase is not None,
            "http_client": http_client is not None,
            "title_agent": title_agent is not None,
            "mem0_client": mem0_client is not None
        }
    }

    # If any critical service is not initialized, mark as unhealthy
    if not all(health_status["services"].values()):
        health_status["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail=health_status)

    return health_status


# ============================================================================
# Public Chat API (No Authentication Required)
# ============================================================================

class PublicChatRequest(BaseModel):
    """Request model for public chat endpoint."""
    query: str


class PublicChatResponse(BaseModel):
    """Response model for public chat endpoint."""
    response: str
    rate_limit_remaining: Optional[Dict[str, int]] = None


def get_client_ip(request: Request) -> str:
    """
    Extract the client IP address from the request.
    Handles X-Forwarded-For header for reverse proxy setups.

    Args:
        request: FastAPI Request object

    Returns:
        str: Client IP address
    """
    # Check for X-Forwarded-For header (common with reverse proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        return forwarded_for.split(",")[0].strip()

    # Check for X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"


@app.post("/api/public/chat", response_model=PublicChatResponse)
async def public_chat(chat_request: PublicChatRequest, request: Request):
    """
    Public chat endpoint for portfolio website integration.

    This endpoint does NOT require authentication and is rate-limited by IP address.
    Designed for embedding PeppeGPT as a side chat widget.

    Uses the existing requests table with IP as user_id for rate limiting.

    Args:
        chat_request: The chat request containing the user's query
        request: FastAPI Request object for IP extraction

    Returns:
        PublicChatResponse with the AI response

    Raises:
        HTTPException 429: If rate limit is exceeded
        HTTPException 400: If query is invalid
    """
    # Get client IP address (used as user_id for rate limiting)
    client_ip = get_client_ip(request)
    public_user_id = f"public:{client_ip}"  # Prefix to distinguish from real users

    # Validate query
    query = chat_request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Check rate limit using existing function (IP as user_id)
    rate_limit = int(os.getenv("PUBLIC_API_RATE_LIMIT_MINUTE", "10"))
    rate_limit_ok = await check_rate_limit(supabase, public_user_id, rate_limit)

    if not rate_limit_ok:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait a minute before trying again."
        )

    try:
        # Store request using existing function (IP as user_id)
        request_id = f"pub-{client_ip}-{int(time.time())}"
        await store_request(supabase, request_id, public_user_id, query[:500])

        # Create agent dependencies (no user-specific memories for public API)
        agent_deps = AgentDeps(
            embedding_client=embedding_client,
            supabase=supabase,
            http_client=http_client,
            brave_api_key=os.getenv("BRAVE_API_KEY", ""),
            searxng_base_url=os.getenv("SEARXNG_BASE_URL", ""),
            memories="",  # No personalized memories for public API
            graph_client=graph_client
        )

        # Run the agent without streaming (simpler for public API)
        result = await agent.run(query, deps=agent_deps)

        return PublicChatResponse(response=result.data)

    except Exception as e:
        print(f"Error in public chat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your request. Please try again."
        )


@app.post("/api/public/chat/stream")
async def public_chat_stream(chat_request: PublicChatRequest, request: Request):
    """
    Public chat endpoint with streaming response for portfolio website.

    Same as /api/public/chat but returns a streaming response for real-time display.
    Uses the existing requests table with IP as user_id for rate limiting.

    Args:
        chat_request: The chat request containing the user's query
        request: FastAPI Request object for IP extraction

    Returns:
        StreamingResponse with chunked AI response
    """
    # Get client IP address (used as user_id for rate limiting)
    client_ip = get_client_ip(request)
    public_user_id = f"public:{client_ip}"

    # Validate query
    query = chat_request.query.strip()
    if not query:
        return StreamingResponse(
            stream_error_response("Query cannot be empty", "public"),
            media_type='text/plain'
        )

    # Check rate limit using existing function
    rate_limit = int(os.getenv("PUBLIC_API_RATE_LIMIT_MINUTE", "10"))
    rate_limit_ok = await check_rate_limit(supabase, public_user_id, rate_limit)

    if not rate_limit_ok:
        return StreamingResponse(
            stream_error_response("Rate limit exceeded. Please wait a minute.", "public"),
            media_type='text/plain'
        )

    # Store request using existing function
    request_id = f"pub-{client_ip}-{int(time.time())}"
    await store_request(supabase, request_id, public_user_id, query[:500])

    async def stream_response():
        try:
            agent_deps = AgentDeps(
                embedding_client=embedding_client,
                supabase=supabase,
                http_client=http_client,
                brave_api_key=os.getenv("BRAVE_API_KEY", ""),
                searxng_base_url=os.getenv("SEARXNG_BASE_URL", ""),
                memories="",
                graph_client=graph_client
            )

            full_response = ""

            async with agent.iter([query], deps=agent_deps) as run:
                async for node in run:
                    if Agent.is_model_request_node(node):
                        async with node.stream(run.ctx) as request_stream:
                            async for event in request_stream:
                                if isinstance(event, PartStartEvent) and event.part.part_kind == 'text':
                                    yield json.dumps({"text": event.part.content}).encode('utf-8') + b'\n'
                                    full_response += event.part.content
                                elif isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                                    delta = event.delta.content_delta
                                    yield json.dumps({"text": full_response}).encode('utf-8') + b'\n'
                                    full_response += delta

            # Send final chunk
            yield json.dumps({"text": full_response, "complete": True}).encode('utf-8') + b'\n'

        except Exception as e:
            print(f"Error in public chat stream: {str(e)}")
            yield json.dumps({"error": "An error occurred", "complete": True}).encode('utf-8') + b'\n'

    return StreamingResponse(stream_response(), media_type='text/plain')


if __name__ == "__main__":
    import uvicorn
    # Feel free to change the port here if you need
    uvicorn.run(app, host="0.0.0.0", port=8001)
