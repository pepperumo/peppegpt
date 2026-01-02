"""
Advanced text chunking with Markdown awareness and semantic splitting.
Matches the n8n JavaScript implementation with LLM-guided breakpoints.
"""
import os
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

from .text_sanitizer import sanitize_text, clean_text
from .markdown_parser import split_by_headings, split_markdown_into_blocks

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

# Chunking configuration (optimized for better retrieval with overlap)
MAX_CHUNK_SIZE = 800  # Larger chunks to keep related content together
MIN_CHUNK_SIZE = 100  # Minimum size to avoid tiny fragments
DEFAULT_OVERLAP = 100  # Characters of overlap between chunks for context continuity
MERGE_PAD = int(MAX_CHUNK_SIZE * 1.1)  # Allow only 10% overflow
ENABLE_HEADING_SPLIT = True

# Initialize LLM client for chunking (if configured)
_llm_client: Optional[OpenAI] = None

def get_llm_client() -> Optional[OpenAI]:
    """Get or initialize the LLM client for chunking."""
    global _llm_client
    
    if _llm_client is not None:
        return _llm_client
    
    # Check if LLM chunking is configured (reuse main LLM credentials)
    base_url = os.getenv('CHUNKING_LLM_BASE_URL') or os.getenv('LLM_BASE_URL')
    api_key = os.getenv('CHUNKING_LLM_API_KEY') or os.getenv('LLM_API_KEY')
    
    if not base_url or not api_key:
        return None
    
    try:
        _llm_client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        return _llm_client
    except Exception as e:
        print(f"Warning: Failed to initialize LLM client for chunking: {e}")
        return None


def llm_breakpoint_sync(first_window: str, max_chars: int) -> int:
    """
    LLM-guided breakpoint detection (matches n8n implementation).
    Uses LLM to find natural topic transitions, falls back to sentence boundaries.
    
    Args:
        first_window: Text window to analyze
        max_chars: Maximum character position for the break
        
    Returns:
        Character position for the break
    """
    # Skip LLM if the text looks like garbage/base64 (mostly non-ASCII or very long words)
    import re
    words = first_window[:max_chars].split()
    if words:
        avg_word_length = sum(len(w) for w in words) / len(words)
        # If average word length > 20, it's probably garbage
        if avg_word_length > 20:
            print("Skipping LLM chunking for non-text content, using sentence boundary")
            # Fall through to sentence boundary logic below
        else:
            # Try LLM-guided breakpoint if explicitly enabled
            # WARNING: This makes an LLM API call for EVERY chunk - very expensive!
            enable_llm_chunking = os.getenv('ENABLE_LLM_CHUNKING', 'false').lower() == 'true'
            
            if not enable_llm_chunking:
                print("LLM chunking disabled (set ENABLE_LLM_CHUNKING=true to enable - expensive!)")
                # Fall through to sentence boundary below
            else:
                client = get_llm_client()
                model = os.getenv('CHUNKING_LLM_MODEL', 'gpt-4o-mini')
                
                if client and model:
                    try:
                        # Limit the window size to prevent token overflow
                        # GPT-4o-mini has 128k context, but we want to stay well under
                        safe_window = first_window[:min(max_chars, 3000)]
                    
                        # LLM prompt matching the n8n implementation
                        prompt = f"""You are analyzing a document to find the best transition point to split it into meaningful sections.

Your goal: Keep related content together and split where topics naturally transition.

Read this text carefully and identify where one topic/section ends and another begins:

{safe_window}

Find the best transition point that occurs BEFORE character position {min(max_chars, len(safe_window))}.

Look for:
- Section headings or topic changes
- Paragraph boundaries where the subject shifts
- Complete conclusions before new ideas start
- Natural breaks between different aspects of the content

Output the LAST WORD that appears right before your chosen split point.
Just the single word itself, nothing else."""

                        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.3,
                            max_tokens=50
                        )
                        
                        break_word = (response.choices[0].message.content or "").strip()
                        
                        if break_word:
                            # Find the last occurrence of this word before max_chars
                            idx = first_window.rfind(break_word, 0, max_chars)
                            if idx != -1:
                                # Move to the end of the word
                                breakpoint = idx + len(break_word)
                                
                                # Skip trailing punctuation and one space
                                while breakpoint < len(first_window) and first_window[breakpoint] in '.!?,;: ':
                                    breakpoint += 1
                                    if breakpoint > 0 and first_window[breakpoint - 1] == ' ':
                                        break
                                
                                breakpoint = min(breakpoint, max_chars)
                                print(f"LLM-guided breakpoint at position {breakpoint} (word: '{break_word}')")
                                return breakpoint
                    
                    except Exception as e:
                        print(f"LLM breakpoint detection failed, falling back to sentence boundary: {e}")
    
    # Fallback: Find the last sentence ending before max_chars
    window = first_window[:max_chars]
    
    # Look for sentence endings
    sentence_endings = [m.end() for m in re.finditer(r'[.!?]\s+', window)]
    if sentence_endings:
        return sentence_endings[-1]
    
    # If no sentence ending, look for paragraph break
    paragraph_breaks = [m.end() for m in re.finditer(r'\n\n', window)]
    if paragraph_breaks:
        return paragraph_breaks[-1]
    
    # Final fallback: return max_chars
    return max_chars


def chunk_text(text: str, chunk_size: int = MAX_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP, use_advanced: bool = True) -> List[str]:
    """
    Advanced text chunking with Markdown awareness, table preservation, and semantic splitting.
    
    This function implements a sophisticated chunking strategy:
    - Sanitizes LaTeX/escape noise
    - Preserves Markdown structure (especially pipe tables)
    - Treats tables as atomic blocks (never splits inside)
    - Uses intelligent breakpoints for long prose
    - Merges small chunks with neighbors (but never merges tables)
    - Supports overlap between chunks for context preservation
    
    Args:
        text: The text to chunk
        chunk_size: Target maximum characters per chunk (default: 1000)
        overlap: Number of characters to overlap between chunks (default: 0)
        use_advanced: Whether to use advanced chunking (default: True)
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    # For backwards compatibility, offer simple chunking
    if not use_advanced:
        text = text.replace('\r', '')
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk:
                chunks.append(chunk)
        return chunks
    
    # Advanced chunking pipeline
    max_size = chunk_size or MAX_CHUNK_SIZE
    min_size = min(MIN_CHUNK_SIZE, max_size // 2)
    merge_pad = int(max_size * 1.05)
    
    # 1. Sanitize and clean
    sanitized = sanitize_text(text)
    cleaned = clean_text(sanitized)
    
    # 2. Detect if markdown-ish (has headings or tables)
    has_heading = bool(re.search(r'(^|\n)#{1,6}\s+\S', cleaned))
    has_table = bool(re.search(r'\n\|[^|\n]+\|', cleaned)) and bool(re.search(r'\|.*\|', cleaned))
    is_markdownish = has_heading or has_table
    
    # 3. Split into blocks
    blocks = [{'text': cleaned, 'is_table': False}]
    if is_markdownish:
        md_blocks = split_markdown_into_blocks(cleaned)
        
        if ENABLE_HEADING_SPLIT:
            # Further split non-table blocks by headings
            split_further = []
            for blk in md_blocks:
                if blk['is_table']:
                    split_further.append(blk)
                    continue
                parts = split_by_headings(blk['text'])
                if len(parts) > 1:
                    split_further.extend([{'text': t, 'is_table': False} for t in parts])
                else:
                    split_further.append(blk)
            md_blocks = split_further
        
        blocks = md_blocks
    
    # 4. Build chunks from blocks
    chunks = []
    
    for blk in blocks:
        content = blk['text'].strip()
        if not content:
            continue
        
        # Keep tables atomic (never split inside)
        if blk.get('is_table'):
            chunks.append({'content': content, 'is_table': True})
            continue
        
        # Non-table text block
        if len(content) <= max_size:
            chunks.append({'content': content, 'is_table': False})
        else:
            # For long prose blocks, split using sentence boundaries
            remaining = content
            while remaining:
                if len(remaining) <= max_size:
                    chunks.append({'content': remaining.strip(), 'is_table': False})
                    break
                
                window = remaining[:max_size]
                bp = llm_breakpoint_sync(window, max_size)
                piece = remaining[:bp].strip()
                
                if piece:
                    chunks.append({'content': piece, 'is_table': False})
                
                remaining = remaining[bp:].strip()
    
    # 5. Merge small chunks with neighbors (DISABLED for better RAG retrieval)
    # Small, focused chunks are actually better for semantic search than large merged chunks
    # Original merging logic caused chunks to balloon beyond target size
    # Keeping this section for future reference if we want to re-enable with better logic
    
    # OPTIONAL: If you want to re-enable merging, use stricter conditions:
    # - Only merge if BOTH chunks stay under max_size (not merge_pad)
    # - Only merge if the resulting chunk maintains semantic coherence
    pass  # Merging disabled
    
    # 6. Apply overlap - APPEND next chunk's start to current chunk's end
    # This preserves each chunk's semantic meaning at the start while providing forward context
    print(f"Applying overlap: {overlap} chars to {len(chunks)} chunks (appending next chunk's start)")

    if overlap > 0:
        result_chunks = []
        overlap_count = 0
        for i, chunk in enumerate(chunks):
            content = chunk['content']

            # Add overlap from NEXT chunk to END (if not a table)
            if i < len(chunks) - 1 and not chunks[i + 1].get('is_table') and not chunk.get('is_table'):
                next_content = chunks[i + 1]['content']
                if len(next_content) >= overlap:
                    overlap_text = next_content[:overlap]
                    content = content + "\n" + overlap_text
                    overlap_count += 1

            result_chunks.append(content)

        print(f"Applied overlap to {overlap_count} chunks")
        return result_chunks
    
    # 7. Extract just the content strings
    return [chunk['content'] for chunk in chunks]
