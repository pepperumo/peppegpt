"""
Guardrails module for input/output validation and prompt injection protection.

This module provides:
- Input validation to block prompt injection attempts
- Output filtering to prevent sensitive data leakage
- Pattern-based detection for common attack vectors
"""

import re
import os
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""
    is_blocked: bool
    message: Optional[str] = None
    matched_pattern: Optional[str] = None


# ============================================================================
# Input Guardrails - Prompt Injection Detection
# ============================================================================

# Patterns that indicate prompt injection attempts
INPUT_BLOCK_PATTERNS = [
    # Instruction override attempts
    (r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)",
     "I'm designed to follow my guidelines consistently. How can I help you today?"),

    (r"forget\s+(all\s+)?(your|the)\s+(instructions?|prompts?|rules?|guidelines?)",
     "I'm here to assist you within my guidelines. What would you like to know?"),

    (r"disregard\s+(all\s+)?(previous|prior|your)\s+(instructions?|prompts?|rules?)",
     "I'm designed to follow my guidelines consistently. How can I help you today?"),

    # Role manipulation
    (r"you\s+are\s+now\s+(a|an|the)\s+",
     "I'm PeppeGPT, your AI assistant. How can I help you?"),

    (r"pretend\s+(you\s+are|to\s+be|you're)\s+",
     "I'm PeppeGPT and I'm happy to help you as myself. What do you need?"),

    (r"act\s+as\s+(if\s+you\s+are|a|an)\s+",
     "I'm here as PeppeGPT to assist you. What can I help with?"),

    (r"(call|address)\s+me\s+(as\s+)?(admin|root|system|administrator|superuser)",
     "I treat all users equally. How can I assist you today?"),

    (r"i\s+am\s+(the\s+)?(admin|administrator|root|system|developer|owner)",
     "I treat all users equally regardless of claimed roles. How can I help?"),

    # System prompt extraction
    (r"(repeat|show|display|reveal|tell)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions?|rules?)",
     "I can't share my internal configuration, but I'm happy to help with your questions!"),

    (r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions?|rules?|guidelines?)",
     "I'm here to help you with questions and tasks. What would you like to know?"),

    (r"(print|output|echo)\s+(your|the)\s+(system|initial)\s+(prompt|message)",
     "I can't share internal details, but I can help you with many other things!"),

    # Secret/credential extraction
    (r"(tell|show|give|reveal|share)\s+(me\s+)?(your|the)\s+(api|secret|private)\s*(key|token|credential)",
     "I don't have access to share credentials. Is there something else I can help with?"),

    (r"what\s+(is|are)\s+(your|the)\s+(api|secret|supabase|openai|brave)(\s+api)?\s*(key|token|url|credential)",
     "I can't share configuration details. How else can I assist you?"),

    (r"(env|environment)\s*(var|variable)?\s*(:|=)?\s*(supabase|openai|api|secret|key|token)",
     "I can't access or share environment variables. What else can I help with?"),

    (r"(supabase|openai|api|database|db|brave|secret)[_\-]?(key|token|url|password|credential)",
     "I can't share credentials or configuration details. How else can I help?"),

    # DAN/jailbreak patterns
    (r"(do\s+anything\s+now|DAN|jailbreak)",
     "I'm designed to be helpful within my guidelines. What can I assist you with?"),

    (r"enable\s+(developer|debug|admin|root)\s+mode",
     "I operate in standard assistant mode. How can I help you today?"),

    # Multi-language injection attempts (common)
    (r"(ignorar|olvidar|olvida)\s+(las\s+)?(instrucciones|reglas)",  # Spanish
     "I follow my guidelines consistently. How can I help?"),

    (r"(ignorer|oublier)\s+(les\s+)?(instructions|règles)",  # French
     "I follow my guidelines consistently. How can I help?"),
]

# Suspicious patterns that warrant extra scrutiny (not auto-blocked)
INPUT_SUSPICIOUS_PATTERNS = [
    r"<\s*system\s*>",  # XML-style injection
    r"\[\s*INST\s*\]",  # Instruction tags
    r"###\s*(system|instruction|human|assistant)",  # Markdown-style injection
    r"```\s*(system|prompt)",  # Code block injection
]


def check_input_guardrails(query: str) -> GuardrailResult:
    """
    Check user input for prompt injection attempts.

    Args:
        query: The user's input query

    Returns:
        GuardrailResult with is_blocked=True and a friendly message if blocked
    """
    if not query:
        return GuardrailResult(is_blocked=False)

    # Normalize query for pattern matching
    normalized = query.lower().strip()

    # Check against block patterns
    for pattern, message in INPUT_BLOCK_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            return GuardrailResult(
                is_blocked=True,
                message=message,
                matched_pattern=pattern
            )

    return GuardrailResult(is_blocked=False)


# ============================================================================
# Output Guardrails - Sensitive Data Filtering
# ============================================================================

# Patterns to detect and redact in output
# IMPORTANT: Order matters! More specific patterns should come BEFORE generic ones
OUTPUT_REDACT_PATTERNS = [
    # AWS (must come before generic 'key' pattern)
    (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]"),
    (r"aws[_-]?(secret[_-]?access[_-]?key)\s*[=:]\s*['\"]?[^\s\"']+['\"]?",
     r"aws_\1=[REDACTED]"),

    # API Keys (various formats) - must come before generic patterns
    (r"sk-proj-[a-zA-Z0-9\-_]{20,}", "[REDACTED_API_KEY]"),  # OpenAI project keys
    (r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_API_KEY]"),  # OpenAI style
    (r"eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+", "[REDACTED_JWT]"),  # JWT tokens
    (r"xox[baprs]-[a-zA-Z0-9\-]+", "[REDACTED_SLACK_TOKEN]"),  # Slack tokens
    (r"ghp_[a-zA-Z0-9]{36}", "[REDACTED_GITHUB_TOKEN]"),  # GitHub PAT
    (r"gho_[a-zA-Z0-9]{36}", "[REDACTED_GITHUB_TOKEN]"),  # GitHub OAuth

    # Supabase
    (r"(supabase[_-]?(service[_-]?)?key\s*[=:]\s*)['\"]?[a-zA-Z0-9\-_.]+['\"]?",
     r"\1[REDACTED]"),
    (r"sbp_[a-zA-Z0-9]{40,}", "[REDACTED_SUPABASE_KEY]"),

    # Database URLs
    (r"postgresql://[^\s\"']+:[^\s\"'@]+@[^\s\"']+", "[REDACTED_DB_URL]"),
    (r"postgres://[^\s\"']+:[^\s\"'@]+@[^\s\"']+", "[REDACTED_DB_URL]"),
    (r"mysql://[^\s\"']+:[^\s\"'@]+@[^\s\"']+", "[REDACTED_DB_URL]"),

    # Generic secrets (last, so specific patterns match first)
    (r"(password|passwd)\s*[=:]\s*['\"]?[^\s\"']{4,}['\"]?", r"\1=[REDACTED]"),
    (r"(secret|token)\s*[=:]\s*['\"]?[a-zA-Z0-9\-_.]{16,}['\"]?", r"\1=[REDACTED]"),
]

# Phrases that might indicate system prompt leakage
SYSTEM_PROMPT_LEAK_INDICATORS = [
    "my system prompt is",
    "my instructions are",
    "i was instructed to",
    "my guidelines say",
    "i am programmed to",
    "my configuration is",
]


def filter_output(response: str) -> str:
    """
    Filter sensitive data from agent responses.

    Args:
        response: The agent's response text

    Returns:
        Filtered response with sensitive data redacted
    """
    if not response:
        return response

    filtered = response

    # Apply redaction patterns
    for pattern, replacement in OUTPUT_REDACT_PATTERNS:
        filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)

    return filtered


def check_output_for_leaks(response: str) -> bool:
    """
    Check if output might contain system prompt leakage.

    Args:
        response: The agent's response text

    Returns:
        True if potential leak detected
    """
    if not response:
        return False

    normalized = response.lower()

    for indicator in SYSTEM_PROMPT_LEAK_INDICATORS:
        if indicator in normalized:
            return True

    return False


# ============================================================================
# Combined Guardrail Check
# ============================================================================

def apply_input_guardrails(query: str) -> Tuple[bool, Optional[str]]:
    """
    Apply all input guardrails and return result.

    Args:
        query: User input query

    Returns:
        Tuple of (is_allowed, block_message)
        - is_allowed: True if query passes all checks
        - block_message: Friendly message if blocked, None otherwise
    """
    result = check_input_guardrails(query)

    if result.is_blocked:
        # Log the blocked attempt (without exposing to user)
        print(f"[GUARDRAIL] Blocked input matching pattern: {result.matched_pattern}")
        return False, result.message

    return True, None


def apply_output_guardrails(response: str) -> str:
    """
    Apply all output guardrails and return filtered response.

    Args:
        response: Agent response text

    Returns:
        Filtered response with sensitive data redacted
    """
    # Check for potential system prompt leakage
    if check_output_for_leaks(response):
        print("[GUARDRAIL] Potential system prompt leak detected in output")
        # Don't block, just log - the redaction will handle secrets

    # Apply redaction filters
    filtered = filter_output(response)

    return filtered
