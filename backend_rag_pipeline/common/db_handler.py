from typing import List, Dict, Any, Optional
import os
import io
import json
import traceback
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import base64
import sys
from pathlib import Path
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Handle both relative and absolute imports
try:
    from common.text_processor import chunk_text, create_embeddings, is_tabular_file, extract_schema_from_csv, extract_rows_from_csv
except ImportError:
    from text_processor import chunk_text, create_embeddings, is_tabular_file, extract_schema_from_csv, extract_rows_from_csv

# Import graph builder if available
GRAPH_AVAILABLE = False
try:
    from common.graph_builder import add_chunks_to_graph, delete_document_from_graph
    GRAPH_AVAILABLE = True
except ImportError:
    try:
        from graph_builder import add_chunks_to_graph, delete_document_from_graph
        GRAPH_AVAILABLE = True
    except ImportError:
        GRAPH_AVAILABLE = False
        print("Graph builder not available - running in vector-only mode")

# Import graph selector for intelligent graph usage
try:
    from common.graph_selector import should_use_graph_for_document
except ImportError:
    try:
        from graph_selector import should_use_graph_for_document
    except ImportError:
        # Fallback: always use graph if available
        def should_use_graph_for_document(text, chunks, file_title, mime_type, file_metadata=None) -> tuple[bool, str]:
            return (True, "Graph selector not available - using graph for all documents")

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

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

# Ensure credentials are available
if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

supabase: Client = create_client(supabase_url, supabase_key)

def delete_document_by_file_id(file_id: str) -> None:
    """
    Delete all records related to a specific file ID (documents, document_rows, document_metadata, and graph data).
    Uses batched deletion to avoid timeouts on large datasets.
    
    Args:
        file_id: The Google Drive file ID
    """
    try:
        # Delete graph data first if graph is available
        if GRAPH_AVAILABLE:
            try:
                print(f"🔄 Starting graph deletion for file ID: {file_id}")
                asyncio.run(delete_document_from_graph(file_id))
                print(f"✅ Graph data deletion completed for file ID: {file_id}")
            except Exception as e:
                print(f"❌ Error deleting graph data for {file_id}: {e}")
                print(f"   Error type: {type(e).__name__}")
                import traceback
                traceback.print_exc()
        else:
            print(f"ℹ️  Graph not available - skipping graph deletion for {file_id}")
        
        # Delete document chunks (embeddings) in small batches to avoid timeout
        # Vector embeddings make deletion very slow, so we use very small batches
        try:
            print(f"Deleting document chunks for file ID: {file_id}")
            
            # Get chunk IDs in batches
            batch_size = 10  # Very small batches to avoid timeout
            total_deleted = 0
            
            while True:
                # Fetch next batch of IDs
                select_response = supabase.table("documents").select("id").eq("metadata->>file_id", file_id).limit(batch_size).execute()
                
                if not select_response.data or len(select_response.data) == 0:
                    break  # No more chunks to delete
                
                chunk_ids = [doc['id'] for doc in select_response.data]
                
                # Delete this small batch
                try:
                    supabase.table("documents").delete().in_("id", chunk_ids).execute()
                    total_deleted += len(chunk_ids)
                    print(f"  Deleted batch: {len(chunk_ids)} chunks (total: {total_deleted})")
                except Exception as batch_error:
                    print(f"  Error deleting batch: {batch_error}")
                    # Continue with next batch
            
            print(f"Deleted {total_deleted} document chunks for file ID: {file_id}")
        except Exception as e:
            print(f"Error deleting documents: {e}")
        
        # Delete all document_rows with the specified dataset_id
        try:
            rows_response = supabase.table("document_rows").delete().eq("dataset_id", file_id).execute()
            print(f"Deleted {len(rows_response.data)} document rows for file ID: {file_id}")
        except Exception as e:
            print(f"Error deleting document rows: {e}")
            
        # Delete the document_metadata record
        try:
            metadata_response = supabase.table("document_metadata").delete().eq("id", file_id).execute()
            print(f"Deleted metadata for file ID: {file_id}")
        except Exception as e:
            print(f"Error deleting document metadata: {e}")
            
    except Exception as e:
        print(f"Error in delete_document_by_file_id: {e}")

def insert_document_chunks(chunks: List[str], embeddings: List[List[float]], file_id: str, 
                        file_url: str, file_title: str, mime_type: str, file_contents: bytes | None = None) -> None:
    """
    Insert document chunks with their embeddings into the Supabase database.
    
    Args:
        chunks: List of text chunks
        embeddings: List of embedding vectors for each chunk
        file_id: The Google Drive file ID
        file_url: The URL to access the file
        file_title: The title of the file
        mime_type: The mime type of the file
        file_contents: Optional binary of the file to store as metadata
    """
    try:
        # Ensure we have the same number of chunks and embeddings
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")
        
        # Prepare the data for insertion
        data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # Clean null bytes from chunk to prevent Unicode errors
            clean_chunk = chunk.replace('\x00', '')
            file_bytes_str = base64.b64encode(file_contents).decode('utf-8') if file_contents else None
            data.append({
                "content": clean_chunk,
                "metadata": {
                    "file_id": file_id,
                    "file_url": file_url,
                    "file_title": file_title,
                    "mime_type": mime_type,
                    "chunk_index": i,
                    **({"file_contents": file_bytes_str} if file_bytes_str else {})
                },
                "embedding": embedding
            })
        
        # Insert the data into the documents table
        for item in data:
            supabase.table("documents").insert(item).execute()
    except Exception as e:
        print(f"Error inserting/updating document chunks: {e}")

def insert_or_update_document_metadata(file_id: str, file_title: str, file_url: str, schema=None) -> None:
    """
    Insert or update a record in the document_metadata table.
    
    Args:
        file_id: The Google Drive file ID (used as primary key)
        file_title: The title of the file
        file_url: The URL to access the file
        schema: Optional schema for tabular files
               - For CSV: List[str] of column names
               - For Excel: Dict[str, List[str]] per-sheet schemas
               - For other formats: List[str] of column names
    """
    try:
        # Check if the record already exists
        response = supabase.table("document_metadata").select("*").eq("id", file_id).execute()
        
        # Prepare the data
        data = {
            "id": file_id,
            "title": file_title,
            "url": file_url
        }
        
        # Add schema if provided (handles both List and Dict)
        if schema:
            data["schema"] = json.dumps(schema)
            print(f"  Storing schema: {type(schema).__name__} with {len(schema)} {'sheets' if isinstance(schema, dict) else 'columns'}")
        
        if response.data and len(response.data) > 0:
            # Update existing record
            supabase.table("document_metadata").update(data).eq("id", file_id).execute()
            print(f"Updated metadata for file '{file_title}' (ID: {file_id})")
        else:
            # Insert new record
            supabase.table("document_metadata").insert(data).execute()
            print(f"Inserted metadata for file '{file_title}' (ID: {file_id})")
    except Exception as e:
        print(f"Error inserting/updating document metadata: {e}")

def insert_document_rows(file_id: str, rows: List[Dict[str, Any]]) -> None:
    """
    Insert rows from a tabular file into the document_rows table.
    
    Args:
        file_id: The Google Drive file ID (references document_metadata.id)
        rows: List of row data as dictionaries
    """
    try:
        # First, delete any existing rows for this file
        supabase.table("document_rows").delete().eq("dataset_id", file_id).execute()
        print(f"Deleted existing rows for file ID: {file_id}")
        
        # Insert new rows
        for row in rows:
            supabase.table("document_rows").insert({
                "dataset_id": file_id,
                "row_data": row
            }).execute()
        print(f"Inserted {len(rows)} rows for file ID: {file_id}")
    except Exception as e:
        print(f"Error inserting document rows: {e}")

def process_file_for_rag(file_content: bytes, text: str, file_id: str, file_url: str,
                        file_title: str, mime_type: Optional[str] = None, config: Optional[Dict[str, Any]] = None,
                        folder_path: Optional[str] = None) -> Optional[bool]:
    """
    Process a file for the RAG pipeline - delete existing records and insert new ones.

    Args:
        file_content: The binary content of the file
        text: The text content extracted from the file
        file_id: The Google Drive file ID
        file_url: The URL to access the file
        file_title: The title of the file
        mime_type: Mime type of the file
        config: Configuration for things like the chunk size and overlap
        folder_path: Path of the parent folder (for graph-rag folder detection)
    """
    try:
        # First, delete any existing records for this file
        delete_document_by_file_id(file_id)
        
        # Check if this is a tabular file
        is_tabular = False
        schema = None
        
        if mime_type:
            is_tabular = is_tabular_file(mime_type, config)
            
        if is_tabular:
            # Extract schema (column names) from CSV/Excel
            # Returns: Dict[str, List[str]] for Excel (per-sheet), List[str] for CSV
            schema = extract_schema_from_csv(file_content)
        
        # First, insert or update document metadata (needed for foreign key constraint)
        insert_or_update_document_metadata(file_id, file_title, file_url, schema)
        
        # Then, if it's a tabular file, insert the rows
        if is_tabular:
            # Extract and insert rows for tabular files
            rows = extract_rows_from_csv(file_content)
            if rows:
                insert_document_rows(file_id, rows)
        
        # BONUS: Extract tables from Docling-processed documents (PDFs, images, Word, PowerPoint, etc.)
        # This includes scanned images with tables!
        # NOTE: We do NOT store schemas for OCR-extracted tables (unreliable due to OCR errors)
        docling_table_formats = {
            'application/pdf',
            'image/png',
            'image/jpg',
            'image/jpeg',
            'image/svg',
            'image/svg+xml',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # DOCX
            'application/msword',  # DOC
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # PPTX
        }
        
        if mime_type and any(mime_type.startswith(fmt) or mime_type == fmt for fmt in docling_table_formats):
            try:
                from .docling_extractor import extract_tables_from_document
                doc_rows = extract_tables_from_document(file_content, file_title, mime_type)
                if doc_rows:
                    print(f"Storing {len(doc_rows)} table rows from {mime_type}: {file_title}")
                    print(f"ℹ️  Note: Schema not stored for OCR-extracted tables (OCR quality varies)")
                    insert_document_rows(file_id, doc_rows)
            except ImportError:
                print("Docling extractor not available, skipping table extraction")
            except Exception as e:
                print(f"Could not extract tables from {mime_type} {file_title}: {e}")
        
        # BONUS 2: Extract tables from Markdown and plain text files
        markdown_formats = {'text/markdown', 'text/plain', 'text/x-markdown'}
        if mime_type and any(mime_type.startswith(fmt) or mime_type == fmt for fmt in markdown_formats):
            try:
                from .text_processor import extract_tables_from_markdown, extract_schema_from_markdown
                # Use the extracted text content (already decoded)
                md_rows = extract_tables_from_markdown(text)
                if md_rows:
                    print(f"Storing {len(md_rows)} table rows from markdown: {file_title}")
                    insert_document_rows(file_id, md_rows)
                    
                    # Extract schema from markdown tables
                    md_schema = extract_schema_from_markdown(text)
                    if md_schema:
                        print(f"Extracted schema from markdown tables: {len(md_schema)} columns")
                        # Update the metadata with the extracted schema
                        insert_or_update_document_metadata(file_id, file_title, file_url, md_schema)
            except Exception as e:
                print(f"Could not extract tables from markdown {file_title}: {e}")

        # Get text processing settings from config
        if config is None:
            config = {}
        text_processing = config.get('text_processing', {})
        chunk_size = text_processing.get('default_chunk_size', 400)
        chunk_overlap = text_processing.get('default_chunk_overlap', 0)

        print(f"Chunking with size={chunk_size}, overlap={chunk_overlap}")

        # Chunk the text
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
        if not chunks:
            print(f"No chunks were created for file '{file_title}' (Path: {file_id})")
            return
        
        # Create embeddings for the chunks
        embeddings = create_embeddings(chunks)  

        # For images, don't chunk the image, just store the title for RAG and include the binary in the metadata
        if mime_type and mime_type.startswith("image"):
            # Decide if image should be added to knowledge graph (usually skip for simple images)
            if GRAPH_AVAILABLE:
                use_graph, reason = should_use_graph_for_document(
                    text=text,
                    chunks=chunks,
                    file_title=file_title,
                    mime_type=mime_type,
                    file_metadata={"url": file_url, "file_id": file_id, "type": "image", "folder_path": folder_path or ""}
                )
                
                print(f"📊 Graph decision for image '{file_title}': {'✓ USE GRAPH' if use_graph else '✗ SKIP GRAPH'} - {reason}")
                
                if use_graph:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        graph_result = loop.run_until_complete(
                            add_chunks_to_graph(
                                chunks=chunks,
                                document_title=file_title,
                                document_source=file_id,
                                document_metadata={
                                    "url": file_url,
                                    "mime_type": mime_type,
                                    "type": "image",
                                    "processed_at": datetime.now().isoformat(),
                                    "graph_reason": reason
                                }
                            )
                        )
                        if graph_result:
                            print(f"✓ Added image to knowledge graph: {graph_result.get('episodes_created', 0)} episodes created")
                    except Exception as e:
                        print(f"⚠ Failed to add image to knowledge graph (continuing with vector storage): {e}")
                    finally:
                        loop.close()

            # Insert chunks AFTER graph processing (so incomplete graph = no chunks saved)
            insert_document_chunks(chunks, embeddings, file_id, file_url, file_title, mime_type, file_content)
            return True
        
        # Intelligently decide if this document should use knowledge graph
        if GRAPH_AVAILABLE:
            use_graph, reason = should_use_graph_for_document(
                text=text,
                chunks=chunks,
                file_title=file_title,
                mime_type=mime_type,
                file_metadata={"url": file_url, "file_id": file_id, "folder_path": folder_path or ""}
            )
            
            print(f"📊 Graph decision for '{file_title}': {'✓ USE GRAPH' if use_graph else '✗ SKIP GRAPH'} - {reason}")
            
            if use_graph:
                try:
                    # Run graph building asynchronously
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    graph_result = loop.run_until_complete(
                        add_chunks_to_graph(
                            chunks=chunks,
                            document_title=file_title,
                            document_source=file_id,
                            document_metadata={
                                "url": file_url,
                                "mime_type": mime_type,
                                "processed_at": datetime.now().isoformat(),
                                "graph_reason": reason
                            }
                        )
                    )
                    if graph_result:
                        print(f"✓ Added document to knowledge graph: {graph_result.get('episodes_created', 0)} episodes created")
                    else:
                        print("ⓘ Knowledge graph not configured - using vector storage only")
                except Exception as e:
                    print(f"⚠ Failed to add document to knowledge graph (continuing with vector storage): {e}")
                    # Don't fail the entire process if graph building fails
                    pass
                finally:
                    loop.close()
            else:
                print(f"ⓘ Skipping knowledge graph for this document - using vector-only storage")

        # Insert chunks AFTER graph processing completes (or is skipped)
        # This ensures chunks are only saved if the entire pipeline succeeds
        insert_document_chunks(chunks, embeddings, file_id, file_url, file_title, mime_type or "text/plain")

        print(f"✓ Successfully processed document: {file_title} ({len(chunks)} chunks)")
        return True
    except Exception as e:
        traceback.print_exc()
        print(f"Error processing file for RAG: {e}")
        return False
