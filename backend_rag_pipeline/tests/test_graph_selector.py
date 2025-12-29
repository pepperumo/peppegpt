"""
Test the intelligent graph selector with various document types.
Shows how the system decides which documents should use knowledge graphs.
"""

import pytest
import sys
import os

# Add parent directory to path to import common modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.graph_selector import should_use_graph_for_document, GraphSelector



@pytest.fixture
def selector():
    """Create a GraphSelector instance with test-friendly settings."""
    # Set test-friendly environment variables
    os.environ['GRAPH_MIN_CHUNKS'] = '1'
    os.environ['GRAPH_MODE'] = 'auto'
    return GraphSelector()


@pytest.fixture
def test_documents():
    """Test documents with different characteristics."""
    return [
        {
            "title": "Company_Organizational_Chart_2024.pdf",
            "mime_type": "application/pdf",
            "text": """
            John Smith - CEO
            Reports to: Board of Directors
            
            Sarah Johnson - CTO
            Reports to: John Smith
            Manages: Engineering Team (15 people)
            
            Michael Chen - VP Engineering
            Reports to: Sarah Johnson
            Works with: Product Team, collaborated with Sarah on Cloud Migration
            
            Emily Davis - Engineering Manager
            Reports to: Michael Chen
            Team: Backend Engineering (8 developers)
            """,
            "expected": "USE_GRAPH"
        },
        {
            "title": "Receipt_Starbucks_2024.pdf",
            "mime_type": "application/pdf",
            "text": """
            Starbucks Receipt
            Date: 2024-10-26
            Store: Downtown Seattle
            
            Items:
            - Grande Latte: $5.50
            - Blueberry Muffin: $3.75
            
            Subtotal: $9.25
            Tax: $0.85
            Total: $10.10
            
            Thank you for your visit!
            """,
            "expected": "SKIP_GRAPH"
        },
        {
            "title": "Software_User_Manual.pdf",
            "mime_type": "application/pdf",
            "text": """
            Software Installation Guide
            
            Step 1: Download the installer
            Click the download button on our website.
            
            Step 2: Run the installer
            Double-click the downloaded file.
            
            Step 3: Follow the wizard
            Accept the license agreement and choose installation folder.
            
            Step 4: Complete setup
            Wait for installation to complete and restart your computer.
            """,
            "expected": "SKIP_GRAPH"
        },
        {
            "title": "Research_Paper_ML_Networks.pdf",
            "mime_type": "application/pdf",
            "text": """
            Deep Learning Networks: A Comprehensive Study
            Authors: Dr. Alice Wang, Prof. Robert Kumar, Dr. Maria Garcia
            
            Abstract:
            This research paper investigates the relationship between neural network architecture and performance.
            Our study builds upon the work of LeCun et al. (2015) and extends the findings of Zhang et al. (2020).
            
            Dr. Wang collaborated with Prof. Kumar at MIT, while Dr. Garcia contributed from Stanford.
            The research was funded by NSF Grant #12345 and supported by Google Research.
            
            Related work by Chen et al. shows similar patterns in convolutional networks.
            """,
            "expected": "USE_GRAPH"
        },
        {
            "title": "Certificate_AWS_Solutions_Architect.pdf",
            "mime_type": "application/pdf",
            "text": """
            AWS Certified Solutions Architect - Professional
            
            This certificate is awarded to:
            John Doe
            
            Certification ID: ABC-123-XYZ
            Issue Date: October 26, 2024
            Valid Until: October 26, 2027
            
            Signed by:
            AWS Certification Authority
            """,
            "expected": "SKIP_GRAPH"
        },
        {
            "title": "Legal_Partnership_Agreement.pdf",
            "mime_type": "application/pdf",
            "text": """
            Partnership Agreement
            
            This agreement is entered into between:
            Party A: TechCorp Inc., represented by CEO Jane Smith
            Party B: InnoSoft LLC, represented by Founder Michael Johnson
            
            Jane Smith previously worked with Michael Johnson at DataSystems Corp.
            Both parties agree to collaborate on the development of AI products.
            
            TechCorp will provide engineering resources, led by VP Sarah Chen.
            InnoSoft will provide market access through partnership with RetailCo.
            
            The agreement is governed by California law and overseen by legal counsel from both parties.
            """,
            "expected": "USE_GRAPH"
        },
        {
            "title": "README.md",
            "mime_type": "text/markdown",
            "text": """
            # Project README
            
            ## Installation
            Run `npm install` to install dependencies.
            
            ## Usage
            Run `npm start` to start the application.
            
            ## License
            MIT License
            """,
            "expected": "SKIP_GRAPH"
        },
        {
            "title": "Team_Directory_2024.pdf",
            "mime_type": "application/pdf",
            "text": """
            Engineering Team Directory
            
            Alice Chen - Senior Engineer
            Email: alice@company.com
            Reports to: Bob Smith
            Works with: Carol Johnson, David Lee
            
            Bob Smith - Engineering Manager  
            Email: bob@company.com
            Reports to: Eve Wilson
            Manages: Alice Chen, Frank Miller, Grace Taylor
            
            Carol Johnson - Product Manager
            Email: carol@company.com
            Collaborates with: Alice Chen, Bob Smith
            Partners with: Marketing Team
            
            David Lee - Designer
            Email: david@company.com  
            Works with: Alice Chen
            Reports to: Design Director
            
            Eve Wilson - Director of Engineering
            Email: eve@company.com
            Oversees: Bob Smith, Henry Adams
            Founded the Engineering org in 2020
            """,
            "expected": "USE_GRAPH"
        }
    ]


class TestGraphSelector:
    """Test suite for the intelligent graph selector."""
    
    def test_selector_initialization(self, selector):
        """Test that selector initializes with correct defaults."""
        assert selector is not None
        assert selector.min_chunk_count == 1  # Set via fixture
        assert selector.force_mode == "auto"
    
    def test_force_mode_always(self, test_documents):
        """Test GRAPH_MODE=always forces all documents to use graph."""
        os.environ['GRAPH_MODE'] = 'always'
        os.environ['GRAPH_MIN_CHUNKS'] = '1'
        selector = GraphSelector()
        
        for doc in test_documents:
            use_graph, reason = selector.should_use_graph(
                text=doc["text"],
                chunks=[doc["text"]],
                file_title=doc["title"],
                mime_type=doc["mime_type"]
            )
            assert use_graph is True
            assert "always" in reason.lower()
    
    def test_force_mode_never(self, test_documents):
        """Test GRAPH_MODE=never prevents all documents from using graph."""
        os.environ['GRAPH_MODE'] = 'never'
        os.environ['GRAPH_MIN_CHUNKS'] = '1'
        selector = GraphSelector()
        
        for doc in test_documents:
            use_graph, reason = selector.should_use_graph(
                text=doc["text"],
                chunks=[doc["text"]],
                file_title=doc["title"],
                mime_type=doc["mime_type"]
            )
            assert use_graph is False
            assert "never" in reason.lower()
    
    def test_organizational_chart_uses_graph(self, selector):
        """Test that organizational charts are selected for graph processing."""
        text = """
        John Smith - CEO
        Reports to: Board of Directors
        Sarah Johnson - CTO
        Reports to: John Smith
        """
        
        use_graph, reason = selector.should_use_graph(
            text=text,
            chunks=[text],
            file_title="Company_Organizational_Chart_2024.pdf",
            mime_type="application/pdf"
        )
        
        assert use_graph is True
        assert "organization" in reason.lower() or "chart" in reason.lower()
    
    def test_receipt_skips_graph(self, selector):
        """Test that simple receipts skip graph processing."""
        text = """
        Starbucks Receipt
        Total: $10.10
        Thank you!
        """
        
        use_graph, reason = selector.should_use_graph(
            text=text,
            chunks=[text],
            file_title="Receipt_Starbucks_2024.pdf",
            mime_type="application/pdf"
        )
        
        assert use_graph is False
        assert "receipt" in reason.lower() or "simple" in reason.lower()
    
    def test_research_paper_uses_graph(self, selector):
        """Test that research papers with citations use graph."""
        text = """
        Research Paper by Dr. Alice Wang and Prof. Robert Kumar.
        This work builds upon findings of Zhang et al. (2020).
        Collaborated with Dr. Garcia at Stanford.
        """
        
        use_graph, reason = selector.should_use_graph(
            text=text,
            chunks=[text, text],  # Multiple chunks
            file_title="Research_Paper_ML_Networks.pdf",
            mime_type="application/pdf"
        )
        
        assert use_graph is True
    
    def test_simple_markdown_skips_graph(self, selector):
        """Test that simple markdown files skip graph."""
        text = "# README\n\nInstallation: npm install\nUsage: npm start"
        
        use_graph, reason = selector.should_use_graph(
            text=text,
            chunks=[text],
            file_title="README.md",
            mime_type="text/markdown"
        )
        
        assert use_graph is False
        assert "simple format" in reason.lower()
    
    def test_small_document_skips_graph(self, selector):
        """Test that documents with too few chunks skip graph."""
        os.environ['GRAPH_MIN_CHUNKS'] = '3'
        selector_strict = GraphSelector()
        
        text = "Short document"
        
        use_graph, reason = selector_strict.should_use_graph(
            text=text,
            chunks=[text],  # Only 1 chunk
            file_title="short.pdf",
            mime_type="application/pdf"
        )
        
        assert use_graph is False
        assert "too small" in reason.lower() or "chunks" in reason.lower()
    
    @pytest.mark.parametrize("doc_index", range(8))
    def test_all_documents_correct_decision(self, selector, test_documents, doc_index):
        """Test that all documents get the correct graph/no-graph decision."""
        doc = test_documents[doc_index]
        
        use_graph, reason = selector.should_use_graph(
            text=doc["text"],
            chunks=[doc["text"]] * (2 if "research" in doc["title"].lower() or "team" in doc["title"].lower() else 1),
            file_title=doc["title"],
            mime_type=doc["mime_type"]
        )
        
        expected_use_graph = doc["expected"] == "USE_GRAPH"
        assert use_graph == expected_use_graph, (
            f"Document '{doc['title']}' failed:\n"
            f"  Expected: {doc['expected']}\n"
            f"  Got: {'USE_GRAPH' if use_graph else 'SKIP_GRAPH'}\n"
            f"  Reason: {reason}"
        )