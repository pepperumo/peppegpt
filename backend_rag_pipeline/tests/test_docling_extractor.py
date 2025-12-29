import pytest
from unittest.mock import patch, MagicMock, mock_open
import io
import os
import sys
from typing import List, Dict, Any

# Add the parent directory to sys.path to import the modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import after path setup
from common.docling_extractor import (
    DoclingConfig,
    extract_text_with_docling,
    extract_tables_from_pdf,
    _create_document_converter
)


class TestDoclingConfig:
    """Test DoclingConfig dataclass and environment loading"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = DoclingConfig()
        assert config.ocr_languages == ["en"]
        assert config.table_mode == "accurate"
        assert config.accelerator_device == "auto"
        assert config.num_threads == 4
        assert config.do_ocr is True
        assert config.do_table_structure is True
    
    @patch.dict(os.environ, {
        'DOCLING_OCR_LANGUAGES': 'en,de,fr',
        'DOCLING_TABLE_MODE': 'fast',
        'DOCLING_DEVICE': 'cpu',
        'DOCLING_NUM_THREADS': '8'
    })
    def test_from_env(self):
        """Test loading configuration from environment variables"""
        config = DoclingConfig.from_env()
        assert config.ocr_languages == ["en", "de", "fr"]
        assert config.table_mode == "fast"
        assert config.accelerator_device == "cpu"
        assert config.num_threads == 8
    
    @patch.dict(os.environ, {
        'DOCLING_NUM_THREADS': 'invalid'
    })
    def test_from_env_invalid_thread_count(self):
        """Test fallback to default when thread count is invalid"""
        config = DoclingConfig.from_env()
        assert config.num_threads == 4  # Default value


class TestCreateDocumentConverter:
    """Test DocumentConverter creation with different configurations"""
    
    def test_create_converter_default_config(self):
        """Test creating DocumentConverter with default configuration"""
        config = DoclingConfig()
        
        # Should not raise an exception
        converter = _create_document_converter(config)
        
        # Verify converter was created
        assert converter is not None
        from docling.document_converter import DocumentConverter
        assert isinstance(converter, DocumentConverter)
    
    def test_create_converter_multiple_languages(self):
        """Test creating DocumentConverter with multiple OCR languages"""
        config = DoclingConfig(ocr_languages=["en", "de", "fr"])
        
        # Should not raise an exception
        converter = _create_document_converter(config)
        
        # Verify converter was created
        assert converter is not None
        from docling.document_converter import DocumentConverter
        assert isinstance(converter, DocumentConverter)
    
    def test_create_converter_fast_table_mode(self):
        """Test creating DocumentConverter with fast table mode"""
        config = DoclingConfig(table_mode="fast")
        
        # Should not raise an exception
        converter = _create_document_converter(config)
        
        # Verify converter was created
        assert converter is not None
        from docling.document_converter import DocumentConverter
        assert isinstance(converter, DocumentConverter)


class TestExtractTextWithDocling:
    """Test text extraction from various file types"""
    
    @patch('common.docling_extractor._create_document_converter')
    def test_extract_pdf_with_text(self, mock_create_converter):
        """Test extracting text from a PDF with text content"""
        # Setup mocks
        mock_converter = MagicMock()
        mock_create_converter.return_value = mock_converter
        
        # Mock the convert method
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "# Sample PDF\n\nThis is sample text."
        mock_converter.convert.return_value = mock_result
        
        # Call the function
        pdf_content = b'%PDF-1.4 fake pdf content'
        result = extract_text_with_docling(pdf_content, "sample.pdf", "application/pdf")
        
        # Assertions
        assert result == "# Sample PDF\n\nThis is sample text."
        mock_converter.convert.assert_called_once()
    
    @patch('common.docling_extractor._create_document_converter')
    def test_extract_scanned_pdf_with_ocr(self, mock_create_converter):
        """Test extracting text from a scanned PDF using OCR"""
        # Setup mocks
        mock_converter = MagicMock()
        mock_create_converter.return_value = mock_converter
        
        # Mock OCR result
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "OCR extracted text from scanned PDF"
        mock_converter.convert.return_value = mock_result
        
        # Call the function
        pdf_content = b'%PDF-1.4 scanned pdf content'
        result = extract_text_with_docling(pdf_content, "scanned.pdf", "application/pdf")
        
        # Assertions
        assert result == "OCR extracted text from scanned PDF"
        mock_converter.convert.assert_called_once()
    
    @patch('common.docling_extractor._create_document_converter')
    def test_extract_docx(self, mock_create_converter):
        """Test extracting text from DOCX file"""
        # Setup mocks
        mock_converter = MagicMock()
        mock_create_converter.return_value = mock_converter
        
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "# DOCX Document\n\nContent from DOCX."
        mock_converter.convert.return_value = mock_result
        
        # Call the function
        docx_content = b'PK\x03\x04 fake docx content'
        result = extract_text_with_docling(
            docx_content, 
            "document.docx", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        # Assertions
        assert result == "# DOCX Document\n\nContent from DOCX."
        mock_converter.convert.assert_called_once()
    
    @patch('common.docling_extractor._create_document_converter')
    def test_extract_pptx(self, mock_create_converter):
        """Test extracting text from PPTX file"""
        # Setup mocks
        mock_converter = MagicMock()
        mock_create_converter.return_value = mock_converter
        
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "# Slide 1\n\nPresentation content."
        mock_converter.convert.return_value = mock_result
        
        # Call the function
        pptx_content = b'PK\x03\x04 fake pptx content'
        result = extract_text_with_docling(
            pptx_content,
            "presentation.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        
        # Assertions
        assert result == "# Slide 1\n\nPresentation content."
        mock_converter.convert.assert_called_once()
    
    @patch('common.docling_extractor._create_document_converter')
    def test_extract_image_png(self, mock_create_converter):
        """Test extracting text from PNG image using OCR"""
        # Setup mocks
        mock_converter = MagicMock()
        mock_create_converter.return_value = mock_converter
        
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "Text extracted from PNG image"
        mock_converter.convert.return_value = mock_result
        
        # Call the function
        png_content = b'\x89PNG\r\n\x1a\n fake png content'
        result = extract_text_with_docling(png_content, "image.png", "image/png")
        
        # Assertions
        assert result == "Text extracted from PNG image"
        mock_converter.convert.assert_called_once()
    
    @patch('common.docling_extractor._create_document_converter')
    def test_extract_image_jpg(self, mock_create_converter):
        """Test extracting text from JPEG image using OCR"""
        # Setup mocks
        mock_converter = MagicMock()
        mock_create_converter.return_value = mock_converter
        
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "Text from JPEG"
        mock_converter.convert.return_value = mock_result
        
        # Call the function
        jpg_content = b'\xff\xd8\xff fake jpg content'
        result = extract_text_with_docling(jpg_content, "photo.jpg", "image/jpeg")
        
        # Assertions
        assert result == "Text from JPEG"
        mock_converter.convert.assert_called_once()
    
    @patch('common.docling_extractor._create_document_converter')
    def test_fallback_on_error(self, mock_create_converter, capfd):
        """Test graceful fallback when extraction fails"""
        # Setup mocks
        mock_converter = MagicMock()
        mock_create_converter.return_value = mock_converter
        
        # Make convert raise an exception
        mock_converter.convert.side_effect = Exception("Docling conversion failed")
        
        # Call the function
        result = extract_text_with_docling(b'corrupt content', "file.pdf", "application/pdf")
        
        # Assertions - should return filename on error (matching ocr_extractor behavior)
        assert result == "file.pdf"
        
        # Check that error was printed
        captured = capfd.readouterr()
        assert "Error during Docling extraction" in captured.out
        assert "Docling conversion failed" in captured.out
    
    @patch('common.docling_extractor._create_document_converter')
    def test_empty_content(self, mock_create_converter):
        """Test handling empty file content"""
        # Setup mocks
        mock_converter = MagicMock()
        mock_create_converter.return_value = mock_converter
        
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = ""
        mock_converter.convert.return_value = mock_result
        
        # Call the function
        result = extract_text_with_docling(b'', "empty.pdf", "application/pdf")
        
        # Assertions - returns filename when text is too short (< 10 chars)
        assert result == "empty.pdf"


class TestExtractTablesFromPdf:
    """Test PDF table extraction functionality"""
    
    @patch('common.docling_extractor._create_document_converter')
    def test_extract_pdf_with_tables(self, mock_create_converter):
        """Test extracting tables from PDF"""
        # Setup mocks
        mock_converter = MagicMock()
        mock_create_converter.return_value = mock_converter
        
        # Mock table data using proper pandas DataFrame mock
        import pandas as pd
        
        mock_table1 = MagicMock()
        df1 = pd.DataFrame({
            'Name': ['Alice', 'Bob'],
            'Age': [30, 25]
        })
        mock_table1.export_to_dataframe.return_value = df1
        
        mock_table2 = MagicMock()
        df2 = pd.DataFrame({
            'Product': ['Widget', 'Gadget'],
            'Price': [10.99, 25.50]
        })
        mock_table2.export_to_dataframe.return_value = df2
        
        # Mock document with tables
        mock_result = MagicMock()
        mock_result.document.tables = [mock_table1, mock_table2]
        mock_converter.convert.return_value = mock_result
        
        # Call the function
        pdf_content = b'%PDF-1.4 pdf with tables'
        tables = extract_tables_from_pdf(pdf_content, "tables.pdf")
        
        # Assertions - returns list of row dictionaries
        assert len(tables) == 4  # 2 rows from each table
        assert tables[0]['Name'] == 'Alice'
        assert tables[0]['Age'] == 30
        assert tables[1]['Name'] == 'Bob'
        assert tables[2]['Product'] == 'Widget'
    
    @patch('common.docling_extractor._create_document_converter')
    def test_extract_pdf_no_tables(self, mock_create_converter):
        """Test extracting tables from PDF with no tables"""
        # Setup mocks
        mock_converter = MagicMock()
        mock_create_converter.return_value = mock_converter
        
        mock_result = MagicMock()
        mock_result.document.tables = []
        mock_converter.convert.return_value = mock_result
        
        # Call the function
        pdf_content = b'%PDF-1.4 pdf without tables'
        tables = extract_tables_from_pdf(pdf_content, "no_tables.pdf")
        
        # Assertions
        assert tables == []
    
    @patch('common.docling_extractor._create_document_converter')
    def test_extract_tables_error_handling(self, mock_create_converter, capfd):
        """Test error handling in table extraction"""
        # Setup mocks
        mock_converter = MagicMock()
        mock_create_converter.return_value = mock_converter
        
        # Make convert raise an exception
        mock_converter.convert.side_effect = Exception("Table extraction failed")
        
        # Call the function
        tables = extract_tables_from_pdf(b'corrupt pdf', "error.pdf")
        
        # Assertions
        assert tables == []
        
        # Check that error was printed
        captured = capfd.readouterr()
        assert "Error extracting tables from application/pdf" in captured.out
        assert "Table extraction failed" in captured.out
    
    @patch('common.docling_extractor._create_document_converter')
    def test_extract_single_table(self, mock_create_converter):
        """Test extracting single table from PDF"""
        # Setup mocks
        import pandas as pd
        
        mock_converter = MagicMock()
        mock_create_converter.return_value = mock_converter
        
        mock_table = MagicMock()
        df = pd.DataFrame({
            'Column1': ['Value1'],
            'Column2': ['Value2']
        })
        mock_table.export_to_dataframe.return_value = df
        
        mock_result = MagicMock()
        mock_result.document.tables = [mock_table]
        mock_converter.convert.return_value = mock_result
        
        # Call the function
        tables = extract_tables_from_pdf(b'%PDF-1.4 single table', "single.pdf")
        
        # Assertions - returns list of row dictionaries (1 row)
        assert len(tables) == 1
        assert 'Column1' in tables[0]
        assert 'Column2' in tables[0]
