"""
Intelligent Graph Selector - Automatically decides if a document should use Knowledge Graph.

Uses heuristics and content analysis to determine if a document benefits from graph processing:
- Relationship density (mentions of people, organizations, connections)
- Document complexity (multiple entities, cross-references)
- Document type (contracts, org charts, research vs. simple guides)
- Size (very small docs don't benefit from graph overhead)
"""

import re
import os
from typing import List, Tuple, Optional
from collections import Counter


class GraphSelector:
    """Decides if a document should be processed through the knowledge graph."""
    
    def __init__(self):
        # Environment variable to force enable/disable graph for all documents
        # Options: auto, always, never, folder-only
        self.force_mode = os.getenv("GRAPH_MODE", "folder-only").lower()

        # Folder name that triggers graph processing (case-insensitive)
        self.graph_folder_name = os.getenv("GRAPH_FOLDER_NAME", "graph-rag").lower()

        # Minimum criteria for graph processing (used in auto mode)
        self.min_chunk_count = int(os.getenv("GRAPH_MIN_CHUNKS", "3"))  # Don't graph tiny docs
        self.entity_threshold = int(os.getenv("GRAPH_ENTITY_THRESHOLD", "5"))  # Min entities to detect
        self.relationship_threshold = float(os.getenv("GRAPH_RELATIONSHIP_THRESHOLD", "0.15"))  # % of text with relationships
        
    def should_use_graph(
        self,
        text: str,
        chunks: List[str],
        file_title: str,
        mime_type: str,
        file_metadata: Optional[dict] = None
    ) -> Tuple[bool, str]:
        """
        Determine if document should use knowledge graph.
        
        Args:
            text: Full document text
            chunks: Text chunks (already created)
            file_title: Document title/filename
            mime_type: MIME type of document
            file_metadata: Optional metadata
            
        Returns:
            Tuple of (use_graph: bool, reason: str)
        """
        # Check force mode
        if self.force_mode == "always":
            return True, "GRAPH_MODE=always (environment override)"
        elif self.force_mode == "never":
            return False, "GRAPH_MODE=never (environment override)"
        elif self.force_mode == "folder-only":
            # Only use graph if file is in the graph-rag folder
            is_in_graph_folder = self._is_in_graph_folder(file_title, file_metadata)
            if is_in_graph_folder:
                return True, f"File is in '{self.graph_folder_name}' folder"
            else:
                return False, f"GRAPH_MODE=folder-only: File not in '{self.graph_folder_name}' folder"
        
        # Rule 1: Document size check
        if len(chunks) < self.min_chunk_count:
            return False, f"Too small ({len(chunks)} chunks < {self.min_chunk_count} minimum)"
        
        # Rule 2: MIME type heuristics
        graph_worthy_types = {
            'application/pdf',  # PDFs often have complex structure
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # DOCX
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # PPTX
        }
        
        # Skip graph for simple formats
        simple_types = {
            'text/plain',
            'text/markdown',
            'image/',
        }
        
        if any(mime_type.startswith(st) for st in simple_types):
            return False, f"Simple format ({mime_type}) - vector search sufficient"
        
        # Rule 3: Filename/title heuristics
        graph_worthy_keywords = [
            'org', 'organization', 'chart', 'structure',
            'contract', 'agreement', 'legal',
            'research', 'paper', 'study', 'analysis',
            'relationship', 'network', 'connection',
            'timeline', 'history', 'genealogy',
            'directory', 'roster', 'team'
        ]
        
        simple_keywords = [
            'readme', 'guide', 'manual', 'faq',
            'receipt', 'invoice', 'certificate',
            'template', 'form', 'letter'
        ]
        
        title_lower = file_title.lower()
        
        if any(kw in title_lower for kw in graph_worthy_keywords):
            return True, f"Filename suggests complex relationships: '{file_title}'"
        
        if any(kw in title_lower for kw in simple_keywords):
            return False, f"Filename suggests simple content: '{file_title}'"
        
        # Rule 4: Content analysis - detect entity density
        entity_score = self._analyze_entity_density(text)
        relationship_score = self._analyze_relationship_density(text)
        
        # Rule 5: Decision logic
        if entity_score >= self.entity_threshold and relationship_score >= self.relationship_threshold:
            return True, f"High entity density ({entity_score} entities) and relationships ({relationship_score:.1%})"
        
        if entity_score >= self.entity_threshold * 2:
            return True, f"Very high entity density ({entity_score} entities detected)"
        
        # Default: use vector-only for efficiency
        return False, f"Low complexity (entities: {entity_score}, relationships: {relationship_score:.1%}) - vector search sufficient"
    
    def _analyze_entity_density(self, text: str) -> int:
        """
        Estimate number of named entities in text.
        Simple heuristic: proper nouns, capitalized phrases, dates, organizations.
        """
        entity_count = 0
        
        # Proper nouns (capitalized words not at sentence start)
        proper_nouns = re.findall(r'(?<!\. )\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entity_count += len(set(proper_nouns))  # Unique entities
        
        # Organization indicators (Inc., LLC, Corp., Ltd., etc.)
        org_patterns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|LLC|Corp|Ltd|GmbH|SA|AG)\b', text)
        entity_count += len(set(org_patterns))
        
        # Date patterns
        dates = re.findall(r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b', text, re.IGNORECASE)
        entity_count += min(len(set(dates)), 10)  # Cap date contribution
        
        # Email addresses (often indicate people/organizations)
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        entity_count += len(set(emails))
        
        return entity_count
    
    def _analyze_relationship_density(self, text: str) -> float:
        """
        Estimate relationship density (% of text expressing connections).
        Looks for relationship keywords and patterns.
        """
        relationship_words = [
            # Employment/organizational
            r'\bworked?\s+(?:at|for|with)\b',
            r'\bemployed\s+(?:at|by)\b',
            r'\b(?:manager|director|CEO|founder|partner)\s+(?:of|at)\b',
            r'\breport(?:s|ed)?\s+to\b',
            
            # Collaboration
            r'\bcollaborat(?:ed|ion|ing)\s+with\b',
            r'\bpartner(?:ed|ship)?\s+with\b',
            r'\bteam(?:ed)?\s+up\s+with\b',
            
            # Temporal/causal
            r'\b(?:led|caused|resulted\s+in|followed\s+by)\b',
            r'\b(?:before|after|during|while)\s+\w+ing\b',
            
            # Family/personal
            r'\b(?:married|spouse|child|parent|sibling|relative)\s+(?:of|to)\b',
            r'\bson\s+of\b', r'\bdaughter\s+of\b',
            
            # Ownership/possession
            r'\b(?:owns|owned|founder|creator)\s+of\b',
            r'\bbelongs\s+to\b',
            
            # Association
            r'\bassociat(?:ed|ion)?\s+with\b',
            r'\baffilia(?:ted|tion)?\s+with\b',
            r'\bmember\s+of\b',
        ]
        
        matches = 0
        for pattern in relationship_words:
            matches += len(re.findall(pattern, text, re.IGNORECASE))
        
        # Calculate density (matches per 1000 characters)
        text_length = max(len(text), 1)
        density = (matches * 1000) / text_length
        
        # Normalize to 0-1 range (assume 10 matches per 1000 chars = high density)
        normalized_density = min(density / 10, 1.0)

        return normalized_density

    def _is_in_graph_folder(self, file_title: str, file_metadata: Optional[dict]) -> bool:
        """
        Check if the file is in a folder named 'graph-rag' (or configured folder name).

        Works with:
        - Google Drive: checks 'folder_path' or 'parent_folder' in metadata
        - Local files: checks if file path contains the folder name
        - Web sources: checks if URL contains the folder name
        """
        folder_name = self.graph_folder_name

        # Check file_metadata for folder information
        if file_metadata:
            # Google Drive folder path
            folder_path = file_metadata.get('folder_path', '').lower()
            if folder_name in folder_path:
                return True

            # Parent folder name
            parent_folder = file_metadata.get('parent_folder', '').lower()
            if folder_name in parent_folder:
                return True

            # File URL (for web sources or drive links)
            url = file_metadata.get('url', '').lower()
            if folder_name in url:
                return True

            # File path (for local files)
            file_path = file_metadata.get('file_path', '').lower()
            if folder_name in file_path:
                return True

        # Check file title as fallback (some systems include path in title)
        if folder_name in file_title.lower():
            return True

        return False


# Global instance
_selector = None

def get_graph_selector() -> GraphSelector:
    """Get or create the global graph selector instance."""
    global _selector
    if _selector is None:
        _selector = GraphSelector()
    return _selector


def should_use_graph_for_document(
    text: str,
    chunks: List[str],
    file_title: str,
    mime_type: str,
    file_metadata: Optional[dict] = None
) -> Tuple[bool, str]:
    """
    Convenience function to check if a document should use the knowledge graph.
    
    Returns:
        Tuple of (use_graph: bool, reason: str)
    """
    selector = get_graph_selector()
    return selector.should_use_graph(text, chunks, file_title, mime_type, file_metadata)
