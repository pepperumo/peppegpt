# Replace Mistral OCR with Unified Docling Document Extraction

## Goal

Replace the current multi-tier extraction system (pypdf + python-docx + Mistral OCR API) with a unified Docling-based document processor for local, efficient, and comprehensive text extraction across all document types.

**Specific End State:**
- Remove dependencies on Mistral OCR API (`LLM_OCR_API_KEY`, `LLM_OCR_URL`), `pypdf`, and `python-docx`
- Implement unified Docling-based extraction for PDFs, DOCX, PPTX, Images
- Extract tables from PDFs as structured data (pandas DataFrames) for optional row storage
- Maintain backward compatibility with existing function signatures
- Improve extraction quality with Docling's TableFormer and advanced OCR
- Support file types: PDFs, DOCX, PPTX (NEW), XLSX (improved), Images (PNG, JPG, JPEG, SVG)
- Update Docker configuration with Tesseract OCR system dependencies

## Why

**Business Value:**

- **Cost Reduction**: Eliminate ALL Mistral API costs for OCR operations
- **Privacy**: All document processing happens locally, no data leaves infrastructure
- **Reliability**: No dependency on external API availability or rate limits
- **Performance**: Faster processing with local execution and GPU/MPS acceleration
- **Quality**: Superior table extraction with TableFormer (93.6% accuracy on complex tables)
- **Simplicity**: One extraction pipeline instead of multiple fallback chains
- **New Capabilities**: PPTX support, structured table extraction from PDFs

**Problems This Solves:**

- External API dependency and associated costs (Mistral)
- Complex multi-tier fallback logic (pypdf → Mistral, python-docx → Mistral)
- Network latency for document processing
- API rate limiting during batch processing
- Data privacy concerns with cloud-based OCR
- Poor table extraction from PDFs (tables currently converted to plain text)
- Missing PPTX support
- Fragmented extraction code across multiple libraries

## What

- Fragmented extraction code across multiple libraries

### User-Visible Behavior

- Documents are processed identically from user perspective
- No configuration changes required (except removing Mistral API keys)
- Better quality text extraction, especially for tables and structured content
- Faster processing for batch document ingestion
- **NEW**: PPTX files now supported
- **NEW**: Tables in PDFs can be queried like CSV files (optional feature)

### Technical Requirements

- Install `docling` library with all necessary dependencies (torch, torchvision, easyocr)
- Update Docker configuration with Tesseract OCR system dependencies
- Replace `ocr_extractor.py` with `docling_extractor.py` for unified extraction
- Update `text_processor.py` to use Docling for all document types
- Remove dependencies: `pypdf`, `python-docx`, Mistral API keys
- Add optional Docling configuration for OCR languages and table modes
- Implement table extraction from PDFs as pandas DataFrames (optional row storage)
- Update requirements.txt with Docling dependencies
- Keep CSV/XLSX direct parsing for tabular files (no change)

### Success Criteria

- [ ] All PDF files extract text successfully with Docling
- [ ] DOCX files extract without python-docx dependency
- [ ] PPTX files extract successfully (new capability)
- [ ] Image files (PNG, JPG, SVG) process with Docling OCR
- [ ] Tables in PDFs extracted as DataFrames with >90% accuracy
- [ ] Table extraction can optionally store rows in document_rows table
- [ ] No external API calls for OCR operations
- [ ] All existing tests pass with new implementation
- [ ] Processing speed is equal or faster than Mistral API
- [ ] Memory usage stays within acceptable limits (<2GB per document)
- [ ] Docker builds successfully with Tesseract dependencies
- [ ] Docker container can perform OCR operations
- [ ] Documentation updated with Docling configuration

## All Needed Context

### Primary Source: Archon Knowledge Base (RAG)

**CRITICAL: Use Archon MCP server for all Docling research and code examples.**

```yaml
# Archon RAG Workflow
BEFORE_IMPLEMENTATION:
  step_1_get_sources:
    tool: rag_get_available_sources()
    action: Find Docling knowledge base
    expected: Source with title "Docling"
    capture: source_id for the "Docling" knowledge base
  
  step_2_search_knowledge:
    tool: rag_search_knowledge_base(query="...", source_id="src_xxx", match_count=5)
    queries:
      - "DocumentConverter pipeline options"
      - "PDF OCR table extraction"
      - "DocumentStream binary processing"
      - "EasyOCR configuration"
      - "TableFormer accurate mode"
      - "hardware acceleration GPU MPS"
      - "export markdown DataFrame"
    why: Get real Docling code examples and patterns
  
  step_3_search_code_examples:
    tool: rag_search_code_examples(query="...", source_id="src_xxx", match_count=3)
    queries:
      - "DocumentConverter convert"
      - "PdfPipelineOptions OCR"
      - "table export dataframe"
    why: Find actual implementation patterns

# Example Usage Pattern
research_docling_ocr:
  query: "PDF OCR configuration EasyOCR"
  source_name: "Docling"
  source_filter: Use source_id from "Docling" knowledge base
  expected_results:
    - PdfPipelineOptions initialization
    - EasyOcrOptions configuration
    - OCR language settings
    - Confidence threshold setup

research_table_extraction:
  query: "table extraction DataFrame"
  source_name: "Docling"
  source_filter: Use source_id from "Docling" knowledge base
  expected_results:
    - TableFormer mode configuration
    - result.document.tables iteration
    - export_to_dataframe() usage
    - Cell matching options

research_docker_dependencies:
  query: "Tesseract installation Docker"
  source_name: "Docling"
  source_filter: Use source_id from "Docling" knowledge base
  expected_results:
    - apt-get install commands
    - TESSDATA_PREFIX configuration
    - System dependency list
```

### Fallback: Direct Documentation (if Archon unavailable)

```yaml
# Only use if Archon RAG is unavailable

# Core Docling Documentation
- url: https://github.com/docling-project/docling
  why: Main repository with examples and API reference
  critical: Understanding DocumentConverter and PdfPipelineOptions

# Docling API Patterns from Context7 MCP
- doc: /docling-project/docling
  tool: mcp_upstash_conte_get-library-docs
  sections:
    - "Configure Advanced PDF Processing Pipeline"
    - "Convert PDF from Binary Stream"
    - "Access Parsed Document Structure"
  critical: |
    - PdfPipelineOptions for OCR and table extraction
    - DocumentStream for in-memory binary processing
    - Iterate over document structure for text extraction
```

### Existing Codebase Context

```yaml
# Current Implementation to Replace
- file: backend_rag_pipeline/common/ocr_extractor.py
  why: Current Mistral OCR implementation (3-step API workflow)
  pattern: extract_text_with_ocr() function signature
  critical: Must maintain same function signature for compatibility

- file: backend_rag_pipeline/common/text_processor.py
  why: Orchestrates text extraction based on MIME types
  pattern: extract_text_from_pdf(), extract_text_from_file()
  critical: Integration points for new Docling implementation

- file: backend_rag_pipeline/common/db_handler.py
  lines: ~207-220
  why: Tabular file handling and row insertion
  critical: Integration point for PDF table extraction (Task 10)

# Example Implementation
- file: PRPs/examples/docling/docling_hybrid_chunking.py
  why: Shows DocumentConverter usage pattern
  pattern: |
    converter = DocumentConverter()
    result = converter.convert(file_path)
    doc = result.document
  critical: How to access document text and structure

# Environment Configuration Patterns
- file: backend_rag_pipeline/common/text_processor.py
  lines: 13-28
  pattern: Environment detection (development vs production)
  critical: |
    is_production = os.getenv("ENVIRONMENT") == "production"
    load_dotenv() strategy

# Testing Patterns
- file: backend_rag_pipeline/tests/test_text_processor.py
  why: Existing test patterns for PDF extraction
  critical: Mock patterns and test structure to follow
```

### Current Codebase Tree

```bash
backend_rag_pipeline/
├── common/
│   ├── ocr_extractor.py        # ← TO BE REPLACED
│   ├── text_processor.py       # ← TO BE UPDATED
│   ├── text_chunker.py
│   ├── embeddings.py
│   ├── csv_handler.py
│   ├── db_handler.py
│   ├── graph_builder.py
│   └── graph_utils.py
├── tests/
│   ├── test_text_processor.py  # ← TO BE UPDATED
│   └── conftest.py
├── requirements.txt            # ← TO BE UPDATED
├── .env.example               # ← TO BE UPDATED
└── README.md                   # ← TO BE UPDATED
```

### Desired Codebase Tree

```bash
backend_rag_pipeline/
├── common/
│   ├── docling_extractor.py    # ← NEW: Docling-based extraction
│   ├── text_processor.py       # ← UPDATED: Use docling_extractor
│   ├── text_chunker.py
│   └── (... rest unchanged)
├── tests/
│   ├── test_docling_extractor.py  # ← NEW: Docling extraction tests
│   ├── test_text_processor.py     # ← UPDATED: Test with Docling
│   └── conftest.py
├── requirements.txt              # ← UPDATED: Add docling
├── .env.example                 # ← UPDATED: Remove Mistral, add Docling config
└── README.md                     # ← UPDATED: Document Docling usage
```

### Known Gotchas & Library Quirks

```python
# CRITICAL: Docling Processing
# 1. Docling requires specific dependencies for full functionality
#    - easyocr or tesseract for OCR
#    - transformers for table detection
#    - torch for GPU acceleration (optional but recommended)

# 2. Binary stream processing requires DocumentStream wrapper
#    - Cannot pass raw bytes directly to converter.convert()
#    - Must wrap in: DocumentStream(name="file.pdf", stream=BytesIO(bytes))

# 3. PdfPipelineOptions must be configured BEFORE conversion
#    - OCR: pipeline_options.do_ocr = True
#    - Tables: pipeline_options.do_table_structure = True
#    - Cannot change options after DocumentConverter is initialized

# 4. Text extraction from DoclingDocument
#    - Use doc.export_to_markdown() for full text
#    - OR iterate: doc.iterate_items() for structured access
#    - Tables available via: doc.tables (can export to DataFrame)

# 5. Hardware acceleration
#    - Auto-detects GPU/MPS with AcceleratorDevice.AUTO
#    - Fallback to CPU is automatic
#    - No error if GPU unavailable

# 6. OCR Language Configuration
#    - EasyOcrOptions accepts list: lang=["en", "de", "fr"]
#    - Default is English only
#    - Must install language packs for easyocr

# CRITICAL: Project-Specific Patterns
# 1. Environment variable loading (text_processor.py:13-28)
#    - Development: override=True with .env file
#    - Production: cloud platform env vars only

# 2. Error handling pattern (ocr_extractor.py:156-162)
#    - Always return string, never raise
#    - Fallback to file_name on errors
#    - Log errors with print() for pipeline visibility

# 3. MIME type handling (text_processor.py:95-118)
#    - Exact matches: 'application/pdf'
#    - Prefix matches: mime_type.startswith('image/')
#    - List of supported: ['image/png', 'image/jpg', 'image/jpeg', 'image/svg']

# 4. Function signature compatibility (ocr_extractor.py:25-45)
#    - extract_text_with_ocr(file_content: bytes, file_name: str, mime_type: str) -> str
#    - Must maintain this exact signature for drop-in replacement
```

## Implementation Blueprint

### Data Models and Structure

```python
# Configuration model for Docling pipeline options
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class DoclingConfig:
    """Configuration for Docling document processing."""
    
    # OCR Configuration
    do_ocr: bool = True
    ocr_languages: List[str] = None  # Default: ["en"]
    ocr_confidence_threshold: float = 0.5
    
    # Table Extraction
    do_table_structure: bool = True
    table_mode: str = "accurate"  # "fast" or "accurate"
    do_cell_matching: bool = True
    
    # Content Enrichment
    do_code_enrichment: bool = False
    do_formula_enrichment: bool = False
    
    # Image Processing
    generate_page_images: bool = False
    generate_picture_images: bool = False
    
    # Hardware Acceleration
    accelerator_device: str = "auto"  # "auto", "cpu", "cuda", "mps"
    num_threads: int = 4
    
    def __post_init__(self):
        if self.ocr_languages is None:
            self.ocr_languages = ["en"]

# Document metadata from Docling conversion
@dataclass
class DoclingResult:
    """Result from Docling document conversion."""
    text: str
    page_count: int
    tables_count: int
    file_size: int
    success: bool
    error_message: Optional[str] = None
```

### Implementation Tasks (Ordered by Dependency)

```yaml
Task 0: Research Docling patterns using Archon RAG
  TOOL: Archon MCP server
  ACTION: Gather implementation context from knowledge base
  KNOWLEDGE_BASE: "Docling"
  
  STEP 1 - Get Docling source:
    - Call: rag_get_available_sources()
    - Find: Source with title exactly "Docling"
    - Capture: source_id for subsequent queries
    - Example: If source has id "src_abc123" and title "Docling", use "src_abc123"
  
  STEP 2 - Research core patterns:
    queries:
      - "DocumentConverter PdfPipelineOptions initialization"
      - "binary stream DocumentStream processing"
      - "OCR EasyOcrOptions configuration languages"
      - "TableFormer accurate mode table extraction"
      - "export markdown DataFrame tables"
      - "hardware acceleration GPU MPS AUTO"
      - "Tesseract Docker installation dependencies"
    
    for_each_query:
      - Call: rag_search_knowledge_base(query=query, source_id=source_id, match_count=5)
      - Review: Code examples and documentation snippets
      - Note: API patterns, gotchas, configuration options
  
  STEP 3 - Find code examples:
    - Call: rag_search_code_examples(query="DocumentConverter convert", source_id=source_id)
    - Call: rag_search_code_examples(query="PdfPipelineOptions OCR table", source_id=source_id)
    - Call: rag_search_code_examples(query="table export_to_dataframe", source_id=source_id)
  
  OUTPUT:
    - Save code patterns to reference during implementation
    - Document any Docling-specific quirks or requirements
    - Validate approach against actual Docling examples
  
  VALIDATION:
    - Found at least 10 relevant documentation snippets
    - Found at least 5 code examples showing DocumentConverter usage
    - Understand PdfPipelineOptions configuration pattern
    - Know how to process binary streams with DocumentStream
    - Understand table extraction and DataFrame export

---

Task 1: Update dependencies
  FILE: backend_rag_pipeline/requirements.txt
  ACTION: ADD
  DEPENDENCIES:
    - docling>=1.0.0
    - docling-core>=1.0.0
    - easyocr>=1.7.0  # For OCR capabilities
    - pytesseract>=0.3.10  # Alternative OCR engine
    - torch>=2.0.0  # For GPU acceleration (optional)
    - transformers>=4.30.0  # For table detection models
  
  AFTER: |
    # Existing dependencies remain
    graphiti-core==0.18.0
    pytest-asyncio==0.21.0
    
    # NEW: Docling and dependencies
    docling>=1.0.0
    docling-core>=1.0.0
    easyocr>=1.7.0
    pytesseract>=0.3.10
    torch>=2.0.0
    transformers>=4.30.0

---

Task 2: Create Docling extraction module
  FILE: backend_rag_pipeline/common/docling_extractor.py
  ACTION: CREATE
  PATTERN: Mirror from PRPs/examples/docling/docling_hybrid_chunking.py
  PRESERVE: Same error handling pattern as ocr_extractor.py
  
  STRUCTURE:
    1. Imports and environment loading (same pattern as text_processor.py:1-30)
    2. DoclingConfig dataclass
    3. _get_docling_config() -> DoclingConfig
    4. _create_document_converter() -> DocumentConverter
    5. extract_text_with_docling(file_content: bytes, file_name: str, mime_type: str) -> str
    6. Backward compatibility wrappers

---

Task 3: Update text processor integration
  FILE: backend_rag_pipeline/common/text_processor.py
  ACTION: MODIFY
  
  FIND pattern: "from .ocr_extractor import extract_text_with_ocr"
  REPLACE with: "from .docling_extractor import extract_text_with_docling"
  
  FIND pattern: "extract_text_with_ocr(file_content, file_name, "application/pdf")"
  REPLACE with: "extract_text_with_docling(file_content, file_name, "application/pdf")"
  
  FIND pattern: "extract_text_with_ocr(file_content, file_name, mime_type)"
  REPLACE with: "extract_text_with_docling(file_content, file_name, mime_type)"
  
  PRESERVE: All existing fallback logic and error handling

---

Task 4: Update environment configuration
  FILE: backend_rag_pipeline/.env.example
  ACTION: MODIFY
  
  REMOVE:
    - LLM_OCR_API_KEY=your_mistral_key
    - LLM_OCR_URL=https://api.mistral.ai/v1
  
  ADD:
    - # Docling OCR Configuration (optional - uses local processing)
    - DOCLING_OCR_LANGUAGES=en  # Comma-separated: en,de,fr
    - DOCLING_TABLE_MODE=accurate  # fast or accurate
    - DOCLING_DEVICE=auto  # auto, cpu, cuda, mps
    - DOCLING_NUM_THREADS=4

---

Task 5: Create comprehensive tests
  FILE: backend_rag_pipeline/tests/test_docling_extractor.py
  ACTION: CREATE
  PATTERN: Follow test_text_processor.py structure
  
  TEST CASES:
    1. test_extract_pdf_with_text()
    2. test_extract_scanned_pdf_with_ocr()
    3. test_extract_pdf_with_tables()
    4. test_extract_image_png()
    5. test_extract_image_jpg()
    6. test_extract_with_custom_config()
    7. test_fallback_on_error()
    8. test_binary_stream_processing()
    9. test_gpu_acceleration_available()
    10. test_multiple_languages_config()

---

Task 6: Update existing tests
  FILE: backend_rag_pipeline/tests/test_text_processor.py
  ACTION: MODIFY
  
  FIND: Mock patches for Mistral API
  REPLACE: Mock patches for Docling converter
  
  PRESERVE: All test logic and assertions
  UPDATE: Mock DocumentConverter instead of requests

---

Task 7: Update documentation
  FILE: backend_rag_pipeline/README.md
  ACTION: MODIFY
  
  SECTIONS TO UPDATE:
    - "Features" section: Replace "Mistral OCR" with "Docling"
    - "Environment Configuration": Update OCR config variables
    - "How It Works": Update step 3 to describe Docling processing
    - "Supported File Types": Add note about improved table extraction
  
  ADD NEW SECTION:
    - "Docling Configuration": Document all DOCLING_* env vars
    - "Hardware Acceleration": Document GPU/MPS support

---

Task 8: Update Docker configuration
  FILE: backend_rag_pipeline/Dockerfile
  ACTION: MODIFY
  
  FIND pattern in apt-get install section:
    RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        && rm -rf /var/lib/apt/lists/*
  
  REPLACE with:
    RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        tesseract-ocr \
        tesseract-ocr-eng \
        libtesseract-dev \
        libleptonica-dev \
        pkg-config \
        && rm -rf /var/lib/apt/lists/*
  
  ADD after FROM statement:
    ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/
  
  NOTES:
    - tesseract-ocr: Core OCR engine for Docling
    - tesseract-ocr-eng: English language data (add more as needed)
    - libtesseract-dev: Development headers
    - libleptonica-dev: Image processing library
    - TESSDATA_PREFIX: Required environment variable for Tesseract
  
  OPTIONAL (for multi-language):
    - Add tesseract-ocr-fra, tesseract-ocr-deu, etc. for other languages

---

Task 9: Implement unified document extraction
  FILE: backend_rag_pipeline/common/text_processor.py
  ACTION: MAJOR REFACTOR
  
  GOAL: Unify extraction for PDF, DOCX, PPTX, Images through Docling
  
  CHANGES:
    1. Remove extract_text_from_pdf() function
    2. Remove extract_text_from_docx() function
    3. Update extract_text_from_file() to route based on file type:
       - Docling-supported formats: Use extract_text_with_docling()
       - CSV/XLSX/tabular: Keep current decode logic
       - Plain text: Keep current decode logic
    
  DOCLING_SUPPORTED_FORMATS:
    - 'application/pdf'
    - 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'  # DOCX
    - 'application/vnd.openxmlformats-officedocument.presentationml.presentation'  # PPTX
    - 'image/png', 'image/jpeg', 'image/jpg'
  
  PRESERVE CSV/XLSX HANDLING:
    - Keep tabular_mime_types detection
    - Keep extract_schema_from_csv()
    - Keep extract_rows_from_csv()
    - Reason: These store structured rows in document_rows table

---

Task 10: Implement table extraction from PDFs (BONUS)
  FILE: backend_rag_pipeline/common/docling_extractor.py
  ACTION: ADD FUNCTION
  
  NEW FUNCTION:
    def extract_tables_from_pdf(file_content: bytes, file_name: str) -> List[Dict[str, Any]]:
        """
        Extract tables from PDF as pandas DataFrames.
        Returns list of dicts with table data for row storage.
        """
        # 1. Convert PDF with Docling
        # 2. Iterate through result.document.tables
        # 3. For each table: export_to_dataframe()
        # 4. Convert DataFrame to list of row dicts
        # 5. Return all rows from all tables
  
  INTEGRATION POINT:
    FILE: backend_rag_pipeline/common/db_handler.py
    LOCATION: insert_or_update_document() function around line 207
    
    AFTER tabular file handling:
      if is_tabular:
          schema = extract_schema_from_csv(file_content)
          rows = extract_rows_from_csv(file_content)
          insert_document_rows(file_id, rows)
    
    ADD PDF table extraction:
      # Extract tables from PDFs
      if mime_type == 'application/pdf':
          try:
              from common.docling_extractor import extract_tables_from_pdf
              pdf_rows = extract_tables_from_pdf(file_content, file_title)
              if pdf_rows:
                  insert_document_rows(file_id, pdf_rows)
          except Exception as e:
              print(f"Could not extract tables from PDF {file_title}: {e}")

---

Task 11: Remove deprecated dependencies
  FILE: backend_rag_pipeline/requirements.txt
  ACTION: REMOVE
  
  DEPENDENCIES TO REMOVE:
    - pypdf==5.4.0
    - python-docx>=1.1.0
  
  REASON: Replaced by Docling's unified extraction
  CRITICAL: Only remove after all tests pass

---

Task 12: Remove old Mistral OCR module
  FILE: backend_rag_pipeline/common/ocr_extractor.py
  ACTION: DELETE (or rename to ocr_extractor.py.deprecated)
  
  REASON: No longer needed, replaced by docling_extractor.py
  CRITICAL: Only delete after all tests pass with new implementation
```

### Task 2 Detailed Pseudocode

```python
# backend_rag_pipeline/common/docling_extractor.py

"""
Document text extraction using Docling library.
Supports PDFs, images (PNG, JPG, JPEG, SVG), and Office documents with local processing.
"""

import os
from io import BytesIO
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass, field

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
from docling.datamodel.base_models import InputFormat, DocumentStream
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
        confidence_threshold=config.ocr_confidence
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
        # Step 1: Wrap binary content in DocumentStream
        # GOTCHA: Cannot pass raw bytes to converter - must use DocumentStream
        buf = BytesIO(file_content)
        source = DocumentStream(name=file_name, stream=buf)
        
        # Step 2: Create configured converter
        print(f"Processing {mime_type} file with Docling: {file_name}")
        converter = _create_document_converter()
        
        # Step 3: Convert document
        result = converter.convert(source)
        doc = result.document
        
        # Step 4: Extract text
        # PATTERN: Use export_to_markdown() for full text with structure
        extracted_text = doc.export_to_markdown()
        
        # Alternative for plain text without markdown formatting:
        # extracted_text = "\n\n".join([item.text for item in doc.iterate_items()])
        
        # Step 5: Validate extraction
        if not extracted_text or len(extracted_text.strip()) < 10:
            print(f"Warning: Very little text extracted from {file_name}")
            return file_name
        
        print(f"Docling extraction successful: {len(extracted_text)} characters from {file_name}")
        return extracted_text
        
    except Exception as e:
        # ERROR HANDLING PATTERN: Log but don't raise (from ocr_extractor.py:156-162)
        print(f"Error during Docling extraction for {file_name}: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Fallback to filename (maintains existing behavior)
        return file_name


# Backward compatibility wrapper for PDFs
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
```

### Task 3 Detailed Changes

```python
# backend_rag_pipeline/common/text_processor.py

# BEFORE (lines 13-16):
from .ocr_extractor import extract_text_from_pdf as extract_text_from_pdf_ocr, extract_text_with_ocr

# AFTER:
from .docling_extractor import extract_text_from_pdf as extract_text_from_pdf_docling, extract_text_with_docling

# ---

# BEFORE (line 60):
        return extract_text_from_pdf_ocr(file_content, file_name)

# AFTER:
        return extract_text_from_pdf_docling(file_content, file_name)

# ---

# BEFORE (lines 87-88):
        if os.getenv('LLM_OCR_API_KEY'):
            print(f"PDF has little/no text. Using Mistral OCR for {file_name}")
            return extract_text_with_ocr(file_content, file_name, "application/pdf")

# AFTER:
        # Always use Docling for PDFs with little text (local processing, no API key needed)
        print(f"PDF has little/no text. Using Docling OCR for {file_name}")
        return extract_text_with_docling(file_content, file_name, "application/pdf")

# ---

# BEFORE (lines 112-116):
        if os.getenv('LLM_OCR_API_KEY'):
            print(f"python-docx not available. Using Mistral OCR for {file_name}")
            return extract_text_with_ocr(file_content, file_name, mime_type)
        else:
            print(f"Cannot extract text from {file_name}: python-docx not installed and OCR not configured")
            return ""

# AFTER:
        # Fallback to Docling for DOCX (always available, no API key needed)
        print(f"python-docx not available. Using Docling for {file_name}")
        return extract_text_with_docling(file_content, file_name, mime_type)

# ---

# BEFORE (lines 107-111):
        if os.getenv('LLM_OCR_API_KEY'):
            print(f"Processing image {file_name} with Mistral OCR")
            return extract_text_with_ocr(file_content, file_name, mime_type)
        else:
            return file_name

# AFTER:
        # Always use Docling for images (local OCR, no API key needed)
        print(f"Processing image {file_name} with Docling OCR")
        return extract_text_with_docling(file_content, file_name, mime_type)
```

### Integration Points

```yaml
ENVIRONMENT VARIABLES:
  REMOVE:
    - LLM_OCR_API_KEY (no longer needed)
    - LLM_OCR_URL (no longer needed)
  
  ADD to .env and .env.example:
    - DOCLING_OCR_LANGUAGES=en  # Optional, defaults to "en"
    - DOCLING_TABLE_MODE=accurate  # Optional, "fast" or "accurate"
    - DOCLING_DEVICE=auto  # Optional, auto/cpu/cuda/mps
    - DOCLING_NUM_THREADS=4  # Optional, defaults to 4

DOCKER CONFIGURATION:
  UPDATE: docker-compose.yml
    REMOVE environment variables:
      - LLM_OCR_API_KEY=${LLM_OCR_API_KEY}
      - LLM_OCR_URL=${LLM_OCR_URL:-https://api.mistral.ai/v1}
    
    ADD environment variables:
      - DOCLING_OCR_LANGUAGES=${DOCLING_OCR_LANGUAGES:-en}
      - DOCLING_TABLE_MODE=${DOCLING_TABLE_MODE:-accurate}
      - DOCLING_DEVICE=${DOCLING_DEVICE:-auto}
      - DOCLING_NUM_THREADS=${DOCLING_NUM_THREADS:-4}

README UPDATES:
  FILE: backend_rag_pipeline/README.md
  
  SECTION "Features":
    FIND: "Advanced OCR with Mistral AI"
    REPLACE: "Advanced OCR with Docling (local processing)"
  
  SECTION "Environment Configuration":
    REMOVE: Instructions for LLM_OCR_API_KEY and LLM_OCR_URL
    ADD: New section "Docling Configuration" with all DOCLING_* variables
  
  ADD NEW SECTION: "Hardware Acceleration"
    Content: Explain GPU/MPS support, how to configure, performance benefits

REQUIREMENTS.TXT:
  FILE: backend_rag_pipeline/requirements.txt
  
  ADD after line 30 (after existing dependencies):
    # Document processing with Docling (replaces Mistral OCR)
    docling>=1.0.0
    docling-core>=1.0.0
    easyocr>=1.7.0
    pytesseract>=0.3.10
    torch>=2.0.0
    transformers>=4.30.0
```

### Task 9 Detailed Changes (Unified Extraction)

```python
# backend_rag_pipeline/common/text_processor.py

# MAJOR REFACTOR: Simplify to unified Docling extraction

# STEP 1: Update imports
# REMOVE:
from .ocr_extractor import extract_text_with_ocr

# ADD:
from .docling_extractor import extract_text_with_docling

# STEP 2: Remove extract_text_from_pdf() function entirely
# Lines ~48-95 - DELETE whole function
# Reason: Docling handles PDFs directly, no pypdf fallback needed

# STEP 3: Remove extract_text_from_docx() function entirely  
# Lines ~97-145 - DELETE whole function
# Reason: Docling handles DOCX natively

# STEP 4: Rewrite extract_text_from_file() for unified routing

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
        'application/msword',  # DOC (if supported)
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # PPTX (NEW!)
        'image/png',
        'image/jpg', 
        'image/jpeg',
        'image/svg',
        'image/svg+xml'
    }
    
    # Route to Docling for all supported formats
    if any(mime_type.startswith(fmt) or mime_type == fmt for fmt in docling_formats):
        print(f"Processing {mime_type} file with Docling: {file_name}")
        return extract_text_with_docling(file_content, file_name, mime_type)
    
    # PRESERVED: CSV/XLSX tabular handling (no change)
    # These need structured row storage, not just text extraction
    elif config and any(mime_type.startswith(t) for t in supported_mime_types):
        return file_content.decode('utf-8', errors='replace')
    
    # Plain text fallback
    else:
        return file_content.decode('utf-8', errors='replace')

# RESULT: 
# - BEFORE: ~120 lines with pypdf, python-docx, Mistral fallback chains
# - AFTER: ~40 lines with unified Docling routing
# - REMOVED: 2 functions, 3 fallback layers
# - ADDED: PPTX support (bonus!)
```

### Task 10 Detailed Pseudocode (Table Extraction)

```python
# backend_rag_pipeline/common/docling_extractor.py

# ADD new function for table extraction from PDFs

from typing import List, Dict, Any
import pandas as pd

def extract_tables_from_pdf(file_content: bytes, file_name: str = "document.pdf") -> List[Dict[str, Any]]:
    """
    Extract all tables from a PDF as structured row data.
    
    This enables SQL queries on tables embedded in PDFs,
    similar to CSV/XLSX tabular file handling.
    
    Args:
        file_content: Binary content of the PDF file
        file_name: Name of the PDF file
        
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
        # Step 1: Convert PDF with Docling
        buf = BytesIO(file_content)
        source = DocumentStream(name=file_name, stream=buf)
        
        converter = _create_document_converter()
        result = converter.convert(source)
        doc = result.document
        
        # Step 2: Check if any tables found
        if not doc.tables:
            print(f"No tables found in PDF: {file_name}")
            return []
        
        print(f"Found {len(doc.tables)} table(s) in {file_name}")
        
        # Step 3: Extract all tables as DataFrames
        all_rows = []
        
        for table_idx, table in enumerate(doc.tables):
            # Export table to pandas DataFrame
            df = table.export_to_dataframe()
            
            # Convert DataFrame to list of row dictionaries
            # This matches the format expected by insert_document_rows()
            table_rows = df.to_dict('records')
            
            # Add table metadata to each row
            for row in table_rows:
                row['_table_index'] = table_idx  # Track which table this came from
                row['_source_file'] = file_name
            
            all_rows.extend(table_rows)
            
            print(f"Extracted table {table_idx + 1}: {len(df)} rows × {len(df.columns)} columns")
        
        print(f"Total rows extracted from all tables: {len(all_rows)}")
        return all_rows
        
    except Exception as e:
        print(f"Error extracting tables from PDF {file_name}: {e}")
        print(f"Error type: {type(e).__name__}")
        return []  # Return empty list on error (consistent with fallback pattern)


# INTEGRATION into db_handler.py

# backend_rag_pipeline/common/db_handler.py
# Location: insert_or_update_document() function, around line 220

# FIND:
        # Then, if it's a tabular file, insert the rows
        if is_tabular:
            # Extract and insert rows for tabular files
            rows = extract_rows_from_csv(file_content)
            if rows:
                insert_document_rows(file_id, rows)

# ADD AFTER (new block):
        # BONUS: Extract tables from PDFs for SQL queries
        if mime_type == 'application/pdf':
            try:
                from common.docling_extractor import extract_tables_from_pdf
                pdf_rows = extract_tables_from_pdf(file_content, file_title)
                if pdf_rows:
                    print(f"Storing {len(pdf_rows)} table rows from PDF: {file_title}")
                    insert_document_rows(file_id, pdf_rows)
            except ImportError:
                print("Docling extractor not available, skipping PDF table extraction")
            except Exception as e:
                print(f"Could not extract tables from PDF {file_title}: {e}")

# RESULT:
# - PDFs with tables now queryable like CSV files
# - Supports financial reports, data tables in research papers, etc.
# - Optional feature - doesn't break if extraction fails
```

## Validation Loop

### Level 1: Dependency Installation & Import Check

```bash
# Step 1: Install new dependencies
cd backend_rag_pipeline
pip install -r requirements.txt

# Expected: Successful installation of docling and dependencies
# Look for: "Successfully installed docling-1.x.x"

# Step 2: Verify imports work
python -c "from docling.document_converter import DocumentConverter; print('✓ Docling imports OK')"
python -c "from docling.datamodel.pipeline_options import PdfPipelineOptions; print('✓ Pipeline options OK')"
python -c "import easyocr; print('✓ EasyOCR OK')"

# Expected: All three commands print success messages
# If import errors: Check Python version (3.11+ required), reinstall dependencies
```

### Level 2: Module-Level Tests

```python
# File: backend_rag_pipeline/tests/test_docling_extractor.py

import pytest
from pathlib import Path
from common.docling_extractor import (
    extract_text_with_docling,
    DoclingConfig,
    _create_document_converter
)

def test_config_from_env(monkeypatch):
    """Test configuration loads from environment"""
    monkeypatch.setenv("DOCLING_OCR_LANGUAGES", "en,de,fr")
    monkeypatch.setenv("DOCLING_TABLE_MODE", "fast")
    monkeypatch.setenv("DOCLING_DEVICE", "cpu")
    
    config = DoclingConfig.from_env()
    
    assert config.ocr_languages == ["en", "de", "fr"]
    assert config.table_mode == "fast"
    assert config.accelerator_device == "cpu"

def test_extract_text_pdf_success():
    """Test basic PDF text extraction"""
    # Use a simple test PDF
    test_pdf_path = Path("tests/fixtures/sample.pdf")
    with open(test_pdf_path, "rb") as f:
        pdf_content = f.read()
    
    result = extract_text_with_docling(pdf_content, "sample.pdf", "application/pdf")
    
    assert isinstance(result, str)
    assert len(result) > 0
    assert result != "sample.pdf"  # Should extract actual text, not filename

def test_extract_text_error_fallback():
    """Test fallback to filename on error"""
    # Pass invalid binary content
    invalid_content = b"This is not a valid PDF"
    
    result = extract_text_with_docling(invalid_content, "invalid.pdf", "application/pdf")
    
    # Should fallback to filename, not raise exception
    assert result == "invalid.pdf"

def test_extract_image_with_ocr():
    """Test image OCR extraction"""
    test_image_path = Path("tests/fixtures/sample.png")
    with open(test_image_path, "rb") as f:
        image_content = f.read()
    
    result = extract_text_with_docling(image_content, "sample.png", "image/png")
    
    assert isinstance(result, str)
    assert len(result) > 0

def test_table_extraction():
    """Test PDF with tables extracts structure"""
    test_pdf_path = Path("tests/fixtures/table_document.pdf")
    with open(test_pdf_path, "rb") as f:
        pdf_content = f.read()
    
    result = extract_text_with_docling(pdf_content, "table_doc.pdf", "application/pdf")
    
    # Should contain table markers or structured data
    assert "|" in result or "Table" in result or len(result) > 100
```

```bash
# Run module tests
cd backend_rag_pipeline
pytest tests/test_docling_extractor.py -v

# Expected: All tests pass
# If failing:
#   - Check fixtures exist in tests/fixtures/
#   - Verify PDF/image files are valid
#   - Check Docling installation with import test
```

### Level 3: Integration Tests

```python
# File: backend_rag_pipeline/tests/test_text_processor.py
# UPDATE existing tests to work with Docling

import pytest
from common.text_processor import extract_text_from_pdf, extract_text_from_file

class TestDoclingIntegration:
    """Integration tests for text processor with Docling"""
    
    def test_pdf_extraction_integration(self):
        """Test PDF extraction through text_processor"""
        test_pdf_path = Path("tests/fixtures/sample.pdf")
        with open(test_pdf_path, "rb") as f:
            pdf_content = f.read()
        
        result = extract_text_from_pdf(pdf_content, "sample.pdf")
        
        assert isinstance(result, str)
        assert len(result) > 50  # Should have meaningful content
    
    def test_extract_text_from_file_pdf(self):
        """Test extract_text_from_file dispatches to Docling for PDFs"""
        test_pdf_path = Path("tests/fixtures/sample.pdf")
        with open(test_pdf_path, "rb") as f:
            pdf_content = f.read()
        
        result = extract_text_from_file(
            pdf_content,
            "application/pdf",
            "sample.pdf"
        )
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_extract_text_from_file_image(self):
        """Test image extraction through text_processor"""
        test_image_path = Path("tests/fixtures/sample.png")
        with open(test_image_path, "rb") as f:
            image_content = f.read()
        
        result = extract_text_from_file(
            image_content,
            "image/png",
            "sample.png"
        )
        
        assert isinstance(result, str)
        # Either extracted text or filename fallback
        assert len(result) > 0
```

```bash
# Run integration tests
pytest tests/test_text_processor.py -v

# Expected: All tests pass with Docling integration
# If failing:
#   - Check imports updated correctly (docling_extractor not ocr_extractor)
#   - Verify function names changed (extract_text_with_docling)
#   - Run with -v -s to see print statements for debugging
```

### Level 4: End-to-End Pipeline Test

```bash
# Test the full RAG pipeline with Docling

# Step 1: Prepare test document
mkdir -p backend_rag_pipeline/test_data
# Place a test PDF in test_data/

# Step 2: Run pipeline in single-run mode
cd backend_rag_pipeline
python docker_entrypoint.py --pipeline local --mode single --directory ./test_data

# Expected output:
#   "Processing application/pdf file with Docling: test.pdf"
#   "Docling extraction successful: XXXX characters from test.pdf"
#   "Processing completed successfully"

# Step 3: Verify in database
# Check that documents table has entries with extracted text

# If errors:
#   - Check SUPABASE_URL and SUPABASE_SERVICE_KEY set
#   - Verify test_data directory has readable PDF
#   - Check logs for Docling-specific errors
#   - Ensure sufficient memory (Docling can use 1-2GB per document)
```

### Level 5: Performance Validation

```python
# File: backend_rag_pipeline/tests/test_performance.py

import time
import pytest
from pathlib import Path
from common.docling_extractor import extract_text_with_docling, extract_tables_from_pdf

def test_extraction_performance():
    """Verify Docling extraction performance"""
    test_pdf_path = Path("tests/fixtures/sample.pdf")  # ~5 page PDF
    with open(test_pdf_path, "rb") as f:
        pdf_content = f.read()
    
    start_time = time.time()
    result = extract_text_with_docling(pdf_content, "sample.pdf", "application/pdf")
    duration = time.time() - start_time
    
    assert len(result) > 0
    assert duration < 10.0  # Should complete within 10 seconds
    
    print(f"\n✓ Extraction took {duration:.2f}s for {len(result)} characters")

def test_table_extraction_performance():
    """Verify table extraction from PDFs"""
    test_pdf_path = Path("tests/fixtures/document_with_tables.pdf")
    with open(test_pdf_path, "rb") as f:
        pdf_content = f.read()
    
    start_time = time.time()
    rows = extract_tables_from_pdf(pdf_content, "tables.pdf")
    duration = time.time() - start_time
    
    assert isinstance(rows, list)
    assert len(rows) > 0  # Should extract at least some rows
    assert all(isinstance(row, dict) for row in rows)
    assert duration < 15.0  # Should complete within 15 seconds
    
    print(f"\n✓ Table extraction took {duration:.2f}s, extracted {len(rows)} rows")

def test_memory_usage():
    """Ensure memory usage is reasonable"""
    import tracemalloc
    
    test_pdf_path = Path("tests/fixtures/large_document.pdf")  # 50+ page PDF
    with open(test_pdf_path, "rb") as f:
        pdf_content = f.read()
    
    tracemalloc.start()
    
    result = extract_text_with_docling(pdf_content, "large.pdf", "application/pdf")
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    peak_mb = peak / 1024 / 1024
    
    assert len(result) > 0
    assert peak_mb < 2000  # Should use less than 2GB
    
    print(f"\n✓ Peak memory: {peak_mb:.2f} MB")

def test_unified_extraction_coverage():
    """Test all supported file types extract successfully"""
    test_files = {
        "sample.pdf": "application/pdf",
        "document.docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "presentation.pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "image.png": "image/png",
        "photo.jpg": "image/jpeg",
    }
    
    for filename, mime_type in test_files.items():
        test_path = Path(f"tests/fixtures/{filename}")
        if not test_path.exists():
            pytest.skip(f"Test file {filename} not found")
        
        with open(test_path, "rb") as f:
            content = f.read()
        
        result = extract_text_with_docling(content, filename, mime_type)
        
        assert isinstance(result, str)
        assert len(result) > 0
        print(f"\n✓ {filename} ({mime_type}): {len(result)} chars extracted")
```

```bash
# Run performance tests
pytest tests/test_performance.py -v -s

# Expected:
#   ✓ Extraction took X.XXs for XXXXX characters
#   ✓ Table extraction took X.XXs, extracted XX rows
#   ✓ Peak memory: XXX.XX MB (< 2000 MB)
#   ✓ sample.pdf (application/pdf): XXXX chars extracted
#   ✓ document.docx (...): XXXX chars extracted
#   ✓ presentation.pptx (...): XXXX chars extracted
#   ✓ image.png (image/png): XXX chars extracted

# If slow or high memory:
#   - Check DOCLING_DEVICE=auto for hardware acceleration
#   - Reduce DOCLING_NUM_THREADS if CPU-bound
#   - Consider table_mode=fast for faster processing
```

### Level 6: Docker Validation

```bash
# Test 1: Build Docker image with Tesseract dependencies
cd backend_rag_pipeline
docker build -t rag-pipeline-docling .

# Expected: Build succeeds without errors
# Look for: "Successfully tagged rag-pipeline-docling:latest"

# If build fails:
#   - Check Dockerfile has tesseract-ocr and libtesseract-dev
#   - Verify apt-get update runs before install
#   - Check TESSDATA_PREFIX environment variable set

# Test 2: Verify Tesseract installed in container
docker run --rm rag-pipeline-docling tesseract --version

# Expected output:
#   tesseract 4.x.x
#   leptonica-x.x.x

# If command not found:
#   - Tesseract not installed correctly
#   - Check Dockerfile apt-get install section

# Test 3: Verify Python packages in container
docker run --rm rag-pipeline-docling python -c "from docling.document_converter import DocumentConverter; print('✓ Docling OK')"

# Expected: ✓ Docling OK

# Test 4: Test OCR functionality in container
docker run --rm -v $(pwd)/tests/fixtures:/fixtures rag-pipeline-docling \
  python -c "
from pathlib import Path
from common.docling_extractor import extract_text_with_docling

with open('/fixtures/sample.pdf', 'rb') as f:
    content = f.read()

result = extract_text_with_docling(content, 'sample.pdf', 'application/pdf')
print(f'✓ Extracted {len(result)} characters')
assert len(result) > 0
"

# Expected: ✓ Extracted XXXX characters

# Test 5: Full docker-compose stack test
docker-compose up -d backend_rag_pipeline
docker-compose logs -f backend_rag_pipeline

# Expected in logs:
#   - "✓ Docling imports OK" or similar startup message
#   - No import errors for docling, easyocr, tesseract
#   - Pipeline starts successfully

# Test 6: Docker environment variables
docker-compose exec backend_rag_pipeline env | grep DOCLING

# Expected:
#   DOCLING_OCR_LANGUAGES=en
#   DOCLING_TABLE_MODE=accurate
#   DOCLING_DEVICE=auto
#   DOCLING_NUM_THREADS=4
#   TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/

# Clean up
docker-compose down
```

## Final Validation Checklist

```bash
# Complete validation sequence

# 1. Dependencies
pip install -r requirements.txt && echo "✓ Dependencies installed"

# 2. Imports
python -c "from common.docling_extractor import extract_text_with_docling; print('✓ Imports OK')"

# 3. Unit tests
pytest tests/test_docling_extractor.py -v && echo "✓ Unit tests pass"

# 4. Integration tests
pytest tests/test_text_processor.py -v && echo "✓ Integration tests pass"

# 5. Type checking (if using mypy)
mypy common/docling_extractor.py && echo "✓ Type checking pass"

# 6. Linting
ruff check common/docling_extractor.py && echo "✓ Linting pass"

# 7. End-to-end test
python docker_entrypoint.py --pipeline local --mode single --directory ./test_data && echo "✓ E2E test pass"

# 8. Performance validation
pytest tests/test_performance.py -v -s && echo "✓ Performance acceptable"

# 9. Docker build and validation
docker build -t rag-pipeline-docling . && echo "✓ Docker build success"
docker run --rm rag-pipeline-docling tesseract --version && echo "✓ Tesseract available"
docker run --rm rag-pipeline-docling python -c "from common.docling_extractor import extract_text_with_docling; print('✓ Docling in container')"

# 10. Table extraction test
python -c "
from pathlib import Path
from common.docling_extractor import extract_tables_from_pdf
with open('tests/fixtures/document_with_tables.pdf', 'rb') as f:
    rows = extract_tables_from_pdf(f.read(), 'test.pdf')
print(f'✓ Extracted {len(rows)} table rows')
" && echo "✓ Table extraction works"
```

### Final Checklist Items

**Core Functionality:**

- [ ] All dependencies installed successfully (docling, torch, easyocr)
- [ ] Docling imports work without errors
- [ ] Unit tests pass (test_docling_extractor.py)
- [ ] Integration tests pass (test_text_processor.py)
- [ ] End-to-end pipeline runs successfully
- [ ] No Mistral API calls in logs (grep for "Mistral")

**Unified Extraction:**

- [ ] PDF extraction works with Docling
- [ ] DOCX extraction works without python-docx
- [ ] PPTX extraction works (new capability)
- [ ] Image OCR works correctly (PNG, JPG, SVG)
- [ ] CSV/XLSX tabular handling preserved

**Table Extraction (Bonus):**

- [ ] Tables extracted from PDFs as DataFrames
- [ ] Table rows stored in document_rows table
- [ ] SQL queries work on PDF table data
- [ ] Table extraction doesn't break on PDFs without tables

**Docker & Infrastructure:**

- [ ] Docker builds successfully with Tesseract
- [ ] Tesseract available in container (tesseract --version)
- [ ] TESSDATA_PREFIX environment variable set
- [ ] Docling works inside Docker container
- [ ] docker-compose environment variables updated

**Configuration & Documentation:**

- [ ] Environment variables updated (.env.example)
- [ ] Docker compose updated (docker-compose.yml)
- [ ] Dockerfile updated with Tesseract dependencies
- [ ] README documentation updated
- [ ] requirements.txt updated (added docling, removed pypdf/python-docx)

**Performance & Quality:**

- [ ] Performance is acceptable (<10s per 5-page PDF)
- [ ] Memory usage is reasonable (<2GB per document)
- [ ] Table extraction accuracy >90% on test documents
- [ ] Error handling preserves filename fallback
- [ ] No breaking changes to function signatures

**Cleanup:**

- [ ] ocr_extractor.py deleted (or renamed .deprecated)
- [ ] pypdf dependency removed from requirements.txt
- [ ] python-docx dependency removed from requirements.txt
- [ ] Mistral API keys removed from documentation

## Anti-Patterns to Avoid

```python
# ❌ DON'T: Pass raw bytes to DocumentConverter
converter.convert(pdf_bytes)  # Will fail!

# ✅ DO: Wrap in DocumentStream
source = DocumentStream(name="file.pdf", stream=BytesIO(pdf_bytes))
converter.convert(source)

# ---

# ❌ DON'T: Modify pipeline options after converter creation
converter = DocumentConverter()
converter.options.do_ocr = True  # Too late!

# ✅ DO: Configure options BEFORE creating converter
pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True
converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
)

# ---

# ❌ DON'T: Raise exceptions on extraction errors
def extract_text_with_docling(file_content, file_name, mime_type):
    result = converter.convert(source)
    return result.document.export_to_markdown()  # May raise!

# ✅ DO: Catch all exceptions and return filename fallback
def extract_text_with_docling(file_content, file_name, mime_type):
    try:
        result = converter.convert(source)
        return result.document.export_to_markdown()
    except Exception as e:
        print(f"Error: {e}")
        return file_name  # Fallback pattern

# ---

# ❌ DON'T: Hardcode OCR languages
pipeline_options.ocr_options = EasyOcrOptions(lang=["en"])

# ✅ DO: Load from environment with sensible defaults
lang_env = os.getenv("DOCLING_OCR_LANGUAGES", "en")
languages = [lang.strip() for lang in lang_env.split(",")]
pipeline_options.ocr_options = EasyOcrOptions(lang=languages)

# ---

# ❌ DON'T: Ignore empty extraction results
return result.document.export_to_markdown()  # May be empty!

# ✅ DO: Validate and fallback on poor extraction
text = result.document.export_to_markdown()
if not text or len(text.strip()) < 10:
    print(f"Warning: Little text extracted from {file_name}")
    return file_name
return text

# ---

# ❌ DON'T: Skip environment variable validation
threads = int(os.getenv("DOCLING_NUM_THREADS"))  # May crash!

# ✅ DO: Use defaults and validate
try:
    threads = int(os.getenv("DOCLING_NUM_THREADS", "4"))
except ValueError:
    threads = 4

# ---

# ❌ DON'T: Create converter in every function call (slow!)
def extract_text_with_docling(...):
    converter = DocumentConverter(...)  # Expensive!
    result = converter.convert(source)

# ✅ DO: Reuse converter or make creation explicit
_converter = None

def _get_converter():
    global _converter
    if _converter is None:
        _converter = _create_document_converter()
    return _converter

# Or create once per call but document cost:
def extract_text_with_docling(...):
    # Note: Creates new converter each call (loads models)
    converter = _create_document_converter()
    ...
```

## Success Metrics

**Confidence Score**: 9/10

This PRP provides comprehensive context for one-pass implementation success:

**Strengths:**
- Complete Docling documentation with specific examples
- Exact function signatures for drop-in replacement
- Detailed error handling patterns from existing code
- Step-by-step validation loops with expected outputs
- Performance benchmarks and memory constraints
- Environment configuration with sensible defaults

**Potential Challenges:**
- Docling dependency installation on some systems (documented)
- GPU/MPS availability varies (handled with AUTO device)
- Large PDF memory usage (validated in tests)

**Validation**: An AI agent with access to this PRP and the codebase should successfully replace Mistral OCR with Docling, passing all tests and maintaining backward compatibility.
