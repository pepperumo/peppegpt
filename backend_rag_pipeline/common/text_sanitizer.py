"""
Text sanitization and cleaning utilities.
Handles LaTeX escapes, formatting normalization, and whitespace cleanup.
"""
import re


def sanitize_text(text: str) -> str:
    """
    Sanitize text by cleaning LaTeX/escape noise and normalizing formatting.
    Preserves Markdown structure including pipe tables.
    
    Args:
        text: Raw text to sanitize
        
    Returns:
        Sanitized text with clean formatting
    """
    if not text:
        return ''
    
    # Convert literal "\n" strings to actual newlines if there are many
    if text.count('\\n') >= 3:
        text = text.replace('\\n', '\n')
    
    # Unescape common LaTeX escapes
    text = text.replace('\\%', '%')
    text = text.replace('\\_', '_')
    text = text.replace('\\#', '#')
    text = text.replace('\\&', '&')
    text = text.replace('\\$', '$')
    
    # Strip math wrappers, keep inner text
    text = re.sub(r'\$\s*([^$]*?)\s*\$', r'\1', text)           # $ ... $
    text = re.sub(r'\\\(\s*([\s\S]*?)\s*\\\)', r'\1', text)     # \( ... \)
    text = re.sub(r'\\\[\s*([\s\S]*?)\s*\\\]', r'\1', text)     # \[ ... \]
    
    # Collapse stray backslashes before punctuation (e.g., \" → ")
    text = re.sub(r'\\([\'\"(){}\[\]?:;,.!%\-])', r'\1', text)
    
    # Normalize spaces/newlines around percentages (7 % → 7%, 20\n\n% → 20%)
    text = re.sub(r'(\d)\s+%', r'\1%', text)
    text = re.sub(r'(\d)\s*\n+\s*%', r'\1%', text)
    
    # Normalize spaces around punctuation
    text = re.sub(r'\s+([,;:.!?)])', r'\1', text)
    text = re.sub(r'([(\[])\s+', r'\1', text)
    
    return text


def clean_text(text: str) -> str:
    """
    Clean text by collapsing whitespace and normalizing newlines.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    # Collapse runs of spaces/tabs
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Cap blank lines at two
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()
