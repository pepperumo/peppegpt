"""
Tests for MCP-UI widget tools.
"""

import pytest
import json
from mcp_ui_tools import (
    UIResource,
    create_calendly_widget,
    create_contact_card,
    create_github_repos_widget,
    get_widget,
    AVAILABLE_WIDGETS
)


class TestUIResource:
    """Tests for the UIResource dataclass."""

    def test_ui_resource_creation(self):
        """Test creating a UIResource."""
        resource = UIResource(
            uri="ui://test/widget",
            mime_type="text/html",
            content="<h1>Test</h1>"
        )
        assert resource.uri == "ui://test/widget"
        assert resource.mime_type == "text/html"
        assert resource.content == "<h1>Test</h1>"

    def test_ui_resource_to_dict(self):
        """Test UIResource to_dict conversion."""
        resource = UIResource(
            uri="ui://test/widget",
            mime_type="text/html",
            content="<h1>Test</h1>"
        )
        result = resource.to_dict()

        assert result["uri"] == "ui://test/widget"
        assert result["mimeType"] == "text/html"
        assert result["text"] == "<h1>Test</h1>"


class TestCalendlyWidget:
    """Tests for Calendly widget creation."""

    def test_create_calendly_widget_default(self):
        """Test creating Calendly widget with defaults."""
        widget = create_calendly_widget()

        assert widget.uri == "ui://calendly/booking"
        assert widget.mime_type == "text/html"
        assert "calendly.com/pepperumo/30min" in widget.content
        assert "Schedule a Call with Giuseppe" in widget.content

    def test_create_calendly_widget_custom_url(self):
        """Test creating Calendly widget with custom URL."""
        widget = create_calendly_widget(
            calendly_url="https://calendly.com/custom/meeting",
            title="Custom Meeting"
        )

        assert "calendly.com/custom/meeting" in widget.content
        assert "Custom Meeting" in widget.content

    def test_calendly_widget_has_iframe(self):
        """Test that Calendly widget contains an iframe."""
        widget = create_calendly_widget()
        assert "<iframe" in widget.content
        assert 'class="calendly-frame"' in widget.content


class TestContactCard:
    """Tests for contact card widget creation."""

    def test_create_contact_card(self):
        """Test creating contact card widget."""
        widget = create_contact_card()

        assert widget.uri == "ui://contact/card"
        assert widget.mime_type == "text/html"

    def test_contact_card_contains_info(self):
        """Test that contact card contains Giuseppe's information."""
        widget = create_contact_card()

        assert "Giuseppe Rumore" in widget.content
        assert "pepperumo@gmail.com" in widget.content
        assert "linkedin.com/in/giuseppe-rumore" in widget.content
        assert "github.com/pepperumo" in widget.content
        assert "Berlin, Germany" in widget.content

    def test_contact_card_has_styling(self):
        """Test that contact card has proper styling."""
        widget = create_contact_card()

        assert "<style>" in widget.content
        assert ".card" in widget.content


class TestGithubReposWidget:
    """Tests for GitHub repos widget creation."""

    def test_create_github_repos_widget(self):
        """Test creating GitHub repos widget."""
        widget = create_github_repos_widget()

        assert widget.uri == "ui://github/repos"
        assert widget.mime_type == "text/html"

    def test_github_widget_contains_peppegpt(self):
        """Test that GitHub widget showcases peppegpt project."""
        widget = create_github_repos_widget()

        assert "peppegpt" in widget.content
        assert "github.com/pepperumo" in widget.content

    def test_github_widget_has_tech_tags(self):
        """Test that GitHub widget shows technology tags."""
        widget = create_github_repos_widget()

        assert "Python" in widget.content or "React" in widget.content


class TestWidgetRegistry:
    """Tests for the widget registry."""

    def test_available_widgets_contains_all(self):
        """Test that AVAILABLE_WIDGETS contains all widget types."""
        assert "calendly" in AVAILABLE_WIDGETS
        assert "contact" in AVAILABLE_WIDGETS
        assert "github" in AVAILABLE_WIDGETS

    def test_get_widget_calendly(self):
        """Test getting Calendly widget by type."""
        widget = get_widget("calendly")
        assert widget is not None
        assert widget.uri == "ui://calendly/booking"

    def test_get_widget_contact(self):
        """Test getting contact widget by type."""
        widget = get_widget("contact")
        assert widget is not None
        assert widget.uri == "ui://contact/card"

    def test_get_widget_github(self):
        """Test getting GitHub widget by type."""
        widget = get_widget("github")
        assert widget is not None
        assert widget.uri == "ui://github/repos"

    def test_get_widget_invalid_type(self):
        """Test getting widget with invalid type returns None."""
        widget = get_widget("invalid_type")
        assert widget is None

    def test_get_widget_with_kwargs(self):
        """Test getting widget with keyword arguments."""
        widget = get_widget("calendly", calendly_url="https://custom.url/test")
        assert widget is not None
        assert "custom.url/test" in widget.content


class TestWidgetJsonSerialization:
    """Tests for widget JSON serialization (for frontend communication)."""

    def test_calendly_widget_json_serializable(self):
        """Test that Calendly widget dict is JSON serializable."""
        widget = create_calendly_widget()
        json_str = json.dumps(widget.to_dict())

        parsed = json.loads(json_str)
        assert parsed["uri"] == "ui://calendly/booking"
        assert parsed["mimeType"] == "text/html"
        assert "calendly" in parsed["text"]

    def test_contact_widget_json_serializable(self):
        """Test that contact widget dict is JSON serializable."""
        widget = create_contact_card()
        json_str = json.dumps(widget.to_dict())

        parsed = json.loads(json_str)
        assert parsed["uri"] == "ui://contact/card"

    def test_github_widget_json_serializable(self):
        """Test that GitHub widget dict is JSON serializable."""
        widget = create_github_repos_widget()
        json_str = json.dumps(widget.to_dict())

        parsed = json.loads(json_str)
        assert parsed["uri"] == "ui://github/repos"
