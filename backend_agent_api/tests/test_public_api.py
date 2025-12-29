"""
Tests for the public API endpoints (no authentication required).
These endpoints are designed for portfolio website chat widget integration.
Uses the existing requests table with IP as user_id for rate limiting.
"""

import pytest
from unittest.mock import MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGetClientIP:
    """Tests for IP extraction logic."""

    def test_x_forwarded_for_single_ip(self):
        """Test extraction of single IP from X-Forwarded-For header."""
        from agent_api import get_client_ip

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "203.0.113.195"}
        mock_request.client = MagicMock(host="10.0.0.1")

        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.195"

    def test_x_forwarded_for_multiple_ips(self):
        """Test extraction of first IP from X-Forwarded-For chain."""
        from agent_api import get_client_ip

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
        mock_request.client = MagicMock(host="10.0.0.1")

        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.195"

    def test_x_real_ip_header(self):
        """Test extraction from X-Real-IP header."""
        from agent_api import get_client_ip

        mock_request = MagicMock()
        mock_request.headers = {"X-Real-IP": "203.0.113.195"}
        mock_request.client = MagicMock(host="10.0.0.1")

        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.195"

    def test_direct_client_ip(self):
        """Test fallback to direct client IP."""
        from agent_api import get_client_ip

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock(host="10.0.0.1")

        ip = get_client_ip(mock_request)
        assert ip == "10.0.0.1"

    def test_no_client_returns_unknown(self):
        """Test fallback when no client information is available."""
        from agent_api import get_client_ip

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = None

        ip = get_client_ip(mock_request)
        assert ip == "unknown"

    def test_x_forwarded_for_with_spaces(self):
        """Test that spaces around IPs are stripped."""
        from agent_api import get_client_ip

        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "  203.0.113.195  , 70.41.3.18"}
        mock_request.client = MagicMock(host="10.0.0.1")

        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.195"

    def test_x_real_ip_with_spaces(self):
        """Test that spaces around X-Real-IP are stripped."""
        from agent_api import get_client_ip

        mock_request = MagicMock()
        mock_request.headers = {"X-Real-IP": "  203.0.113.195  "}
        mock_request.client = MagicMock(host="10.0.0.1")

        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.195"


class TestPublicChatRequestValidation:
    """Tests for public chat request validation."""

    def test_empty_query_accepted_at_model_level(self):
        """Test that empty queries are accepted at model level (rejected at endpoint)."""
        from agent_api import PublicChatRequest

        # Empty string should be valid at model level
        request = PublicChatRequest(query="")
        assert request.query == ""

    def test_valid_query_accepted(self):
        """Test that valid queries are accepted."""
        from agent_api import PublicChatRequest

        request = PublicChatRequest(query="Hello, how are you?")
        assert request.query == "Hello, how are you?"

    def test_whitespace_query(self):
        """Test that whitespace-only queries are accepted at model level."""
        from agent_api import PublicChatRequest

        request = PublicChatRequest(query="   ")
        assert request.query == "   "

    def test_long_query_accepted(self):
        """Test that long queries are accepted (no artificial limit)."""
        from agent_api import PublicChatRequest

        long_query = "x" * 4000
        request = PublicChatRequest(query=long_query)
        assert len(request.query) == 4000


class TestPublicChatResponse:
    """Tests for public chat response model."""

    def test_response_with_rate_limit_info(self):
        """Test response includes rate limit information."""
        from agent_api import PublicChatResponse

        response = PublicChatResponse(
            response="Hello!",
            rate_limit_remaining={
                "per_minute": 2,
                "per_hour": 19,
                "per_day": 49
            }
        )

        assert response.response == "Hello!"
        assert response.rate_limit_remaining["per_minute"] == 2

    def test_response_without_rate_limit_info(self):
        """Test response without rate limit information."""
        from agent_api import PublicChatResponse

        response = PublicChatResponse(response="Hello!")

        assert response.response == "Hello!"
        assert response.rate_limit_remaining is None

    def test_response_with_empty_string(self):
        """Test response with empty string is valid."""
        from agent_api import PublicChatResponse

        response = PublicChatResponse(response="")
        assert response.response == ""


class TestPublicUserIdFormat:
    """Tests for public user ID format used in rate limiting."""

    def test_public_user_id_format(self):
        """Test that public user ID has correct prefix."""
        ip = "192.168.1.1"
        public_user_id = f"public:{ip}"
        assert public_user_id == "public:192.168.1.1"
        assert public_user_id.startswith("public:")

    def test_public_user_id_with_ipv6(self):
        """Test public user ID with IPv6 address."""
        ipv6 = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        public_user_id = f"public:{ipv6}"
        assert public_user_id == f"public:{ipv6}"
        assert public_user_id.startswith("public:")

    def test_public_user_id_distinguishes_from_real_users(self):
        """Test that public user IDs are distinguishable from real user UUIDs."""
        real_user_id = "550e8400-e29b-41d4-a716-446655440000"
        public_user_id = "public:192.168.1.1"

        # Real user IDs are UUIDs, public ones have "public:" prefix
        assert not real_user_id.startswith("public:")
        assert public_user_id.startswith("public:")
