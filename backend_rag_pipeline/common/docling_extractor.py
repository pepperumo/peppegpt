"""
Document text extraction using Docling library.
Supports PDFs, images (PNG, JPG, JPEG, SVG), and Office documents with local processing.
"""

import os
import warnings
from io import BytesIO
from typing import Optional, List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass, field

# Suppress PyTorch warnings about pin_memory without GPU
warnings.filterwarnings('ignore', message='.*pin_memory.*no accelerator.*')
warnings.filterwarnings('ignore', category=UserWarning, module='torch.utils.data.dataloader')

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas not available for advanced table processing")

# Global cache for Docling conversion results to avoid processing files twice
# Key: (file_name, file_size_bytes), Value: (doc, text)
_docling_cache = {}

# Environment loading pattern (from text_processor.py)
is_production = os.getenv("ENVIRONMENT") == "production"
if not is_production:
    project_root = Path(__file__).resolve().parent.parent
    dotenv_path = project_root / '.env'
    load_dotenv(dotenv_path, override=True)
else:
    load_dotenv()

# Docling imports
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling_core.types.io import DocumentStream
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    EasyOcrOptions,
    TableFormerMode,
)
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions


@dataclass
class DoclingConfig:
    """Configuration for Docling processing from environment variables."""
    
    do_ocr: bool = True
    ocr_languages: list = field(default_factory=lambda: ["en"])
    ocr_confidence: float = 0.5
    
    do_table_structure: bool = True
    table_mode: str = "accurate"
    do_cell_matching: bool = True
    
    accelerator_device: str = "auto"
    num_threads: int = 4
    
    @classmethod
    def from_env(cls) -> 'DoclingConfig':
        """Load configuration from environment variables."""
        config = cls()
        
        # Parse OCR languages from env (comma-separated)
        lang_env = os.getenv("DOCLING_OCR_LANGUAGES", "en")
        config.ocr_languages = [lang.strip() for lang in lang_env.split(",")]
        
        # Table extraction mode
        table_mode = os.getenv("DOCLING_TABLE_MODE", "accurate").lower()
        config.table_mode = table_mode if table_mode in ["fast", "accurate"] else "accurate"
        
        # Hardware device
        device = os.getenv("DOCLING_DEVICE", "auto").lower()
        config.accelerator_device = device
        
        # Thread count
        try:
            config.num_threads = int(os.getenv("DOCLING_NUM_THREADS", "4"))
        except ValueError:
            config.num_threads = 4
        
        return config


def _create_document_converter(config: Optional[DoclingConfig] = None) -> DocumentConverter:
    """
    Create and configure DocumentConverter with pipeline options.
    
    CRITICAL: All options must be set BEFORE creating converter.
    Cannot modify options after initialization.
    """
    if config is None:
        config = DoclingConfig.from_env()
    
    # Configure PDF pipeline options
    pipeline_options = PdfPipelineOptions()
    
    # OCR configuration
    pipeline_options.do_ocr = config.do_ocr
    pipeline_options.ocr_options = EasyOcrOptions(
        lang=config.ocr_languages,
        # Note: EasyOcrOptions doesn't have confidence_threshold in current API
    )
    
    # Table extraction
    pipeline_options.do_table_structure = config.do_table_structure
    if config.table_mode == "accurate":
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    else:
        pipeline_options.table_structure_options.mode = TableFormerMode.FAST
    pipeline_options.table_structure_options.do_cell_matching = config.do_cell_matching
    
    # Hardware acceleration
    device_map = {
        "auto": AcceleratorDevice.AUTO,
        "cpu": AcceleratorDevice.CPU,
        "cuda": AcceleratorDevice.CUDA,
        "mps": AcceleratorDevice.MPS,
    }
    device = device_map.get(config.accelerator_device, AcceleratorDevice.AUTO)
    
    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=config.num_threads,
        device=device
    )
    
    # Create converter with options
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options
            )
        }
    )
    
    return converter


def _process_with_docling(file_content: bytes, file_name: str, mime_type: str):
    """
    Internal function to process document with Docling once and cache the result.
    Returns (doc, extracted_text) tuple.
    """
    # Create cache key based on file name and size
    cache_key = (file_name, len(file_content))
    
    # Check cache first
    if cache_key in _docling_cache:
        return _docling_cache[cache_key]
    
    # Process with Docling
    buf = BytesIO(file_content)
    source = DocumentStream(name=file_name, stream=buf)
    
    print(f"Processing {mime_type} file with Docling: {file_name}")
    converter = _create_document_converter()
    result = converter.convert(source)
    doc = result.document
    
    # Extract text
    extracted_text = doc.export_to_markdown()
    
    if not extracted_text or len(extracted_text.strip()) < 10:
        print(f"Warning: Very little text extracted from {file_name}")
        extracted_text = file_name
    else:
        print(f"Docling extraction successful: {len(extracted_text)} characters from {file_name}")
    
    # Cache the result (both doc and text)
    _docling_cache[cache_key] = (doc, extracted_text)
    
    # Limit cache size to avoid memory issues (keep last 10 documents)
    if len(_docling_cache) > 10:
        # Remove oldest entry
        oldest_key = next(iter(_docling_cache))
        del _docling_cache[oldest_key]
    
    return doc, extracted_text

def extract_text_with_docling(
    file_content: bytes,
    file_name: str = "document",
    mime_type: str = "application/pdf"
) -> str:
    """
    Extract text from PDF or image using Docling.
    
    This is a drop-in replacement for extract_text_with_ocr().
    Maintains same signature for backward compatibility.
    
    CRITICAL: Never raises exceptions - always returns string.
    Fallback to file_name on errors (same pattern as ocr_extractor.py).
    
    Args:
        file_content: Binary content of the file
        file_name: Name of the file (for metadata and fallback)
        mime_type: MIME type of the file
        
    Returns:
        Extracted text from the document, or file_name on error
    """
    try:
        _, extracted_text = _process_with_docling(file_content, file_name, mime_type)
        return extracted_text
        
    except Exception as e:
        # ERROR HANDLING PATTERN: Log but don't raise (from ocr_extractor.py:156-162)
        print(f"Error during Docling extraction for {file_name}: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Fallback to filename (maintains existing behavior)
        return file_name


def extract_text_from_pdf(file_content: bytes, file_name: str = "document.pdf") -> str:
    """
    Legacy wrapper for PDF extraction. Use extract_text_with_docling() instead.
    
    Args:
        file_content: Binary content of the PDF file
        file_name: Name of the PDF file
        
    Returns:
        Extracted text from the PDF
    """
    return extract_text_with_docling(file_content, file_name, "application/pdf")


def extract_tables_from_document(file_content: bytes, file_name: str = "document", mime_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract all tables from ANY Docling-supported document as structured row data.
    
    Works with PDFs, images (scanned documents), Word docs, PowerPoint, etc.
    This enables SQL queries on tables embedded in visual documents,
    similar to CSV/XLSX tabular file handling.
    
    Args:
        file_content: Binary content of the document file
        file_name: Name of the document file
        mime_type: MIME type (optional, for logging)
        
    Returns:
        List of dictionaries, each representing a table row
        Empty list if no tables found or on error
        
    Example return value:
        [
            {"Column1": "value1", "Column2": "value2", "Column3": "value3"},
            {"Column1": "value4", "Column2": "value5", "Column3": "value6"},
            ...
        ]
    """
    try:
        # Use cached Docling result if available (avoid reprocessing)
        file_type = mime_type or "document"
        print(f"Attempting table extraction from {file_type}: {file_name}")
        
        doc, _ = _process_with_docling(file_content, file_name, file_type)
        
        # Step 2: Check if any tables found
        if not doc.tables:
            print(f"No tables found in {file_type}: {file_name}")
            return []
        
        print(f"Found {len(doc.tables)} table(s) in {file_type}: {file_name}")
        
        # Step 3: Extract all tables as DataFrames
        all_rows = []
        
        for table_idx, table in enumerate(doc.tables):
            # Export table to pandas DataFrame
            df = table.export_to_dataframe()
            
            # ENHANCEMENT: Detect if columns are unnamed (integers or generic names)
            # This happens when OCR doesn't detect headers properly
            columns_are_generic = (
                all(isinstance(col, int) for col in df.columns) or  # [0, 1, 2, 3...]
                all(str(col).startswith('Unnamed') for col in df.columns)  # [Unnamed: 0, Unnamed: 1...]
            )
            
            if PANDAS_AVAILABLE and columns_are_generic and len(df) > 0:
                # Try to use first row as column headers
                first_row = df.iloc[0]
                non_empty_count = sum(1 for val in first_row if pd.notna(val) and str(val).strip())
                
                # If first row has at least 30% non-empty values, treat it as headers
                if non_empty_count >= len(df.columns) * 0.3:  # At least 30% filled
                    new_columns = []
                    for i, val in enumerate(first_row):
                        if pd.notna(val) and str(val).strip():
                            # Clean and use the header text
                            header = str(val).strip()
                            # Remove special characters that might break SQL
                            header = header.replace('\n', ' ').replace('\r', '')
                            new_columns.append(header)
                        else:
                            # Fallback to generic name if empty
                            new_columns.append(f"Column_{i}")
                    
                    # Apply new column names and remove the header row from data
                    df.columns = new_columns
                    df = df.iloc[1:].reset_index(drop=True)
            
            # Convert DataFrame to list of row dictionaries
            # This matches the format expected by insert_document_rows()
            table_rows = df.to_dict('records')
            
            # Add table metadata to each row
            for row in table_rows:
                row['_table_index'] = table_idx  # Track which table this came from
                row['_source_file'] = file_name
            
            all_rows.extend(table_rows)
        
        print(f"Extracted {len(all_rows)} rows from {len(doc.tables)} table(s) in {file_type}")
        return all_rows
        
    except Exception as e:
        print(f"Error extracting tables from {file_type} {file_name}: {e}")
        print(f"Error type: {type(e).__name__}")
        return []  # Return empty list on error (consistent with fallback pattern)


# Legacy alias for backward compatibility
def extract_tables_from_pdf(file_content: bytes, file_name: str = "document.pdf") -> List[Dict[str, Any]]:
    """
    Legacy wrapper. Use extract_tables_from_document() instead.
    """
    return extract_tables_from_document(file_content, file_name, "application/pdf")
