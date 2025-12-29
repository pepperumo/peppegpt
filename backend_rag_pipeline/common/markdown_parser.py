"""
Markdown parsing utilities.
Handles detection and parsing of Markdown tables and headings.
"""
import re
from typing import List, Dict, Any


def is_table_line(line: str) -> bool:
    """Check if a line is part of a Markdown pipe table."""
    # Pipe table line: | cell | cell |
    if re.match(r'^\s*\|.*\|\s*$', line):
        return True
    # Delimiter row: |:---|:---:|---:|
    if re.match(r'^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$', line):
        return True
    return False


def split_by_headings(text: str) -> List[str]:
    """Split Markdown text by headings, keeping heading with its section."""
    # Split on lines starting with # (headings), keeping the heading
    parts = re.split(r'\n(?=(?:#{1,6}\s))', text)
    return [p.strip() for p in parts if p.strip()]


def split_markdown_into_blocks(text: str) -> List[Dict[str, Any]]:
    """
    Group consecutive table lines together; everything else is regular text.
    
    Args:
        text: Markdown text
        
    Returns:
        List of blocks with 'text' and 'is_table' properties
    """
    lines = text.split('\n')
    blocks = []
    buffer = []
    in_table = False
    
    def flush():
        if buffer:
            blocks.append({
                'text': '\n'.join(buffer).strip(),
                'is_table': in_table
            })
            buffer.clear()
    
    for line in lines:
        if is_table_line(line):
            if not in_table:
                flush()
                in_table = True
            buffer.append(line)
        else:
            if in_table:
                flush()
                in_table = False
            buffer.append(line)
    
    flush()
    return [b for b in blocks if b['text']]
