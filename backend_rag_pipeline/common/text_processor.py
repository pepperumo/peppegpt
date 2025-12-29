import os
import io
import csv
import re
import json
import tempfile
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

# Import from specialized modules
from .text_chunker import chunk_text
from .docling_extractor import extract_text_with_docling

# Try to import python-docx for DOCX support
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("Warning: python-docx not installed. DOCX files will use OCR fallback.")

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

# Initialize OpenAI client
api_key = os.getenv("EMBEDDING_API_KEY", "") or "ollama"
openai_client = OpenAI(api_key=api_key, base_url=os.getenv("EMBEDDING_BASE_URL"))

# Re-export chunk_text for backward compatibility
__all__ = [
    'chunk_text',
    'extract_text_from_pdf',
    'extract_text_with_docling',
    'extract_text_from_file',
    'create_embeddings',
    'is_tabular_file',
    'extract_schema_from_csv',
    'extract_rows_from_csv',
]

def extract_text_from_pdf(file_content: bytes, file_name: str = "document.pdf") -> str:
    """
    Extract text from a PDF file using Docling (local processing).
    
    Args:
        file_content: Binary content of the PDF file
        file_name: Name of the PDF file
        
    Returns:
        Extracted text from the PDF
    """
    # Use Docling for all PDF extraction (handles both text and OCR)
    return extract_text_with_docling(file_content, file_name, "application/pdf")

def extract_text_from_docx(file_content: bytes, file_name: str = "document.docx") -> str:
    """
    Extract text from a DOCX file using Docling (local processing).
    
    Args:
        file_content: Binary content of the DOCX file
        file_name: Name of the DOCX file
        
    Returns:
        Extracted text from the DOCX
    """
    # Use Docling for DOCX extraction (no external dependencies needed)
    return extract_text_with_docling(file_content, file_name, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

def extract_text_from_file(file_content: bytes, mime_type: str, file_name: str, config: Optional[Dict[str, Any]] = None) -> str:
    """
    Extract text from a file based on its MIME type.
    
    SIMPLIFIED: Routes to Docling for all document formats.
    PRESERVED: CSV/XLSX tabular handling for row storage.
    
    Args:
        file_content: Binary content of the file
        mime_type: MIME type of the file
        file_name: Name of the file
        config: Configuration dictionary with supported_mime_types
        
    Returns:
        Extracted text from the file
    """
    supported_mime_types = []
    if config and 'supported_mime_types' in config:
        supported_mime_types = config['supported_mime_types']
    
    # UNIFIED: Docling-supported document formats
    docling_formats = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # DOCX
        'application/msword',  # DOC
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # PPTX (NEW!)
        'image/png',
        'image/jpg', 
        'image/jpeg',
        'image/svg',
        'image/svg+xml'
    }
    
    # Route to Docling for all supported formats
    if any(mime_type.startswith(fmt) or mime_type == fmt for fmt in docling_formats):
        return extract_text_with_docling(file_content, file_name, mime_type)
    
    # PRESERVED: CSV/XLSX tabular handling (no change)
    # These need structured row storage, not just text extraction
    elif config and any(mime_type.startswith(t) for t in supported_mime_types):
        return file_content.decode('utf-8', errors='replace')
    
    # Plain text fallback
    else:
        return file_content.decode('utf-8', errors='replace')

def create_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Create embeddings for a list of text chunks using OpenAI.
    
    Args:
        texts: List of text chunks to embed
        
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    model = os.getenv("EMBEDDING_MODEL_CHOICE", "text-embedding-3-small")
    response = openai_client.embeddings.create(
        model=model,
        input=texts
    )
    
    # Extract the embedding vectors from the response
    embeddings = [item.embedding for item in response.data]
    
    return embeddings

def is_tabular_file(mime_type: str, config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Check if a file is tabular based on its MIME type.
    
    Args:
        mime_type: The MIME type of the file
        config: Optional configuration dictionary
        
    Returns:
        bool: True if the file is tabular (CSV or Excel), False otherwise
    """
    # Default tabular MIME types if config is not provided
    tabular_mime_types = [
        'csv',
        'xlsx',
        'text/csv',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.google-apps.spreadsheet'
    ]
    
    # Use tabular_mime_types from config if available
    if config and 'tabular_mime_types' in config:
        tabular_mime_types = config['tabular_mime_types']
    
    return any(mime_type.startswith(t) for t in tabular_mime_types)

def extract_schema_from_csv(file_content: bytes):
    """
    Extract column names from a CSV or Excel file.
    For Excel files with multiple sheets, returns per-sheet schemas as a dictionary.
    For CSV files, returns a simple list of column names.
    
    Args:
        file_content: The binary content of the CSV or Excel file
        
    Returns:
        For Excel: Dict[str, List[str]] - Per-sheet schemas
        For CSV: List[str] - Column names
    """
    try:
        # Try to detect if this is an Excel file (starts with PK signature)
        if file_content[:4] == b'PK\x03\x04':
            # This is an Excel file (xlsx format)
            try:
                import pandas as pd
                excel_file = io.BytesIO(file_content)
                
                # Read all sheets to get per-sheet schemas
                excel_data = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl')
                
                # Store per-sheet schemas
                per_sheet_schemas = {}
                
                for sheet_name, df in excel_data.items():
                    # Clean column names: strip whitespace and convert to string
                    cleaned_columns = [str(col).strip() for col in df.columns]
                    df.columns = cleaned_columns
                    
                    # Add _sheet_name to each sheet's schema
                    per_sheet_schemas[sheet_name] = cleaned_columns + ['_sheet_name']
                    print(f"  Sheet '{sheet_name}': {len(df)} rows, columns: {cleaned_columns}")
                
                print(f"Extracted per-sheet schemas from Excel: {len(excel_data)} sheets")
                print(f"Schemas: {json.dumps(per_sheet_schemas, indent=2)}")
                
                # Return per-sheet schemas as dictionary
                return per_sheet_schemas
                
            except ImportError:
                print("pandas or openpyxl not available for Excel schema extraction")
                return []
            except Exception as e:
                print(f"Error reading Excel schema: {e}")
                return []
        
        # CSV file processing
        text_content = file_content.decode('utf-8', errors='replace')
        csv_reader = csv.reader(io.StringIO(text_content))
        # Get the header row (first row)
        header = next(csv_reader)
        return header
        
    except Exception as e:
        print(f"Error extracting schema: {e}")
        return []

def extract_rows_from_csv(file_content: bytes) -> List[Dict[str, Any]]:
    """
    Extract rows from a CSV or Excel file as a list of dictionaries.
    For Excel files with multiple sheets, extracts all sheets and combines them.
    
    Args:
        file_content: The binary content of the CSV or Excel file
        
    Returns:
        List[Dict[str, Any]]: List of row data as dictionaries with added metadata
    """
    try:
        # Try to detect if this is an Excel file (starts with PK signature)
        if file_content[:4] == b'PK\x03\x04':
            # This is an Excel file (xlsx format)
            try:
                import pandas as pd
                excel_file = io.BytesIO(file_content)
                
                # Read all sheets
                excel_data = pd.read_excel(excel_file, sheet_name=None, engine='openpyxl')
                
                all_rows = []
                for sheet_name, df in excel_data.items():
                    # Clean column names: strip whitespace and convert to string
                    cleaned_columns = [str(col).strip() for col in df.columns]
                    df.columns = cleaned_columns
                    
                    print(f"  Processing sheet '{sheet_name}': {len(df)} rows, columns: {cleaned_columns}")
                    
                    # Convert DataFrame to list of dicts
                    sheet_rows = df.to_dict('records')
                    
                    # Add sheet metadata to each row
                    for row in sheet_rows:
                        row['_sheet_name'] = sheet_name
                    
                    all_rows.extend(sheet_rows)
                    print(f"  Extracted {len(sheet_rows)} rows from sheet '{sheet_name}'")
                
                print(f"Total rows extracted from Excel: {len(all_rows)} across {len(excel_data)} sheets")
                return all_rows
                
            except ImportError:
                print("pandas or openpyxl not available, falling back to CSV parsing")
                # Fall through to CSV parsing
            except Exception as e:
                print(f"Error reading Excel file: {e}")
                return []
        
        # CSV file processing
        text_content = file_content.decode('utf-8', errors='replace')
        csv_reader = csv.DictReader(io.StringIO(text_content))
        return list(csv_reader)
        
    except Exception as e:
        print(f"Error extracting rows from file: {e}")
        return []


def extract_tables_from_markdown(text_content: str) -> List[Dict[str, Any]]:
    """
    Extract tables from markdown text content.
    
    Parses markdown table syntax:
    | Column1 | Column2 | Column3 |
    |---------|---------|---------|
    | value1  | value2  | value3  |
    | value4  | value5  | value6  |
    
    Args:
        text_content: The text content containing markdown tables
        
    Returns:
        List of dictionaries, each representing a table row
        Empty list if no tables found
    """
    try:
        all_rows = []
        
        # Split content into lines
        lines = text_content.split('\n')
        
        i = 0
        table_index = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check if this line looks like a table header (contains |)
            if '|' in line and line.count('|') >= 2:
                # Extract header
                header_parts = [col.strip() for col in line.split('|')]
                header_parts = [col for col in header_parts if col]  # Remove empty strings
                
                if not header_parts:
                    i += 1
                    continue
                
                # Check next line for separator (---|---|---)
                if i + 1 < len(lines):
                    separator_line = lines[i + 1].strip()
                    if '|' in separator_line and re.search(r'-+', separator_line):
                        # This is a valid markdown table!
                        i += 2  # Skip header and separator
                        
                        # Extract table rows
                        while i < len(lines):
                            row_line = lines[i].strip()
                            if not row_line or '|' not in row_line:
                                break  # End of table
                            
                            # Parse row
                            row_parts = [col.strip() for col in row_line.split('|')]
                            row_parts = [col for col in row_parts if col is not None]  # Keep empty strings as values
                            
                            # Create row dict (match header to values)
                            if len(row_parts) > 0:
                                row_dict = {}
                                for idx, header in enumerate(header_parts):
                                    value = row_parts[idx] if idx < len(row_parts) else ""
                                    row_dict[header] = value
                                
                                # Add metadata
                                row_dict['_table_index'] = table_index
                                row_dict['_source_type'] = 'markdown'
                                
                                all_rows.append(row_dict)
                            
                            i += 1
                        
                        table_index += 1
                        continue
            
            i += 1
        
        if all_rows:
            print(f"Extracted {len(all_rows)} rows from {table_index} markdown table(s)")
        
        return all_rows
        
    except Exception as e:
        print(f"Error extracting markdown tables: {e}")
        return []


def extract_schema_from_markdown(text_content: str) -> List[str]:
    """
    Extract column names from markdown tables.
    
    Args:
        text_content: The text content containing markdown tables
        
    Returns:
        List of unique column names from all tables
    """
    try:
        rows = extract_tables_from_markdown(text_content)
        if not rows:
            return []
        
        # Get all unique column names (excluding metadata)
        all_columns = set()
        for row in rows:
            all_columns.update(k for k in row.keys() if not k.startswith('_'))
        
        return sorted(list(all_columns))
        
    except Exception as e:
        print(f"Error extracting markdown schema: {e}")
        return []

