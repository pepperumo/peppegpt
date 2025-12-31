"""
MCP-UI Tools for rendering interactive widgets in chat.

These tools return UIResource objects that the frontend renders
using @mcp-ui/client's UIResourceRenderer component.
"""

from typing import Optional
from dataclasses import dataclass
import json


@dataclass
class UIResource:
    """MCP-UI Resource for rendering interactive widgets."""
    uri: str
    mime_type: str
    content: str

    def to_dict(self) -> dict:
        return {
            "uri": self.uri,
            "mimeType": self.mime_type,
            "text": self.content
        }


def create_calendly_widget(
    calendly_url: str = "https://calendly.com/pepperumo/30min",
    title: str = "Schedule a Call with Giuseppe"
) -> UIResource:
    """
    Create a Calendly booking widget as MCP-UI resource.

    Args:
        calendly_url: The Calendly scheduling link
        title: Widget title

    Returns:
        UIResource containing the Calendly embed
    """
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: transparent;
        }}
        .widget-container {{
            width: 100%;
            min-height: 1050px;
            border-radius: 12px;
            overflow: hidden;
            background: #0f0f23;
        }}
        .widget-header {{
            padding: 16px 20px;
            background: linear-gradient(135deg, #1e3a5f 0%, #0f0f23 100%);
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .widget-header h3 {{
            color: #fff;
            font-size: 16px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .calendly-frame {{
            width: 100%;
            height: 1000px;
            border: none;
        }}
    </style>
</head>
<body>
    <div class="widget-container">
        <div class="widget-header">
            <h3>📅 {title}</h3>
        </div>
        <iframe
            class="calendly-frame"
            src="{calendly_url}?hide_gdpr_banner=1&background_color=0f0f23&text_color=ffffff&primary_color=3b82f6"
            frameborder="0"
            scrolling="yes">
        </iframe>
    </div>
</body>
</html>'''

    return UIResource(
        uri="ui://calendly/booking",
        mime_type="text/html",
        content=html_content
    )


# Widget registry for easy lookup
AVAILABLE_WIDGETS = {
    "calendly": create_calendly_widget,
}


def get_widget(widget_type: str, **kwargs) -> Optional[UIResource]:
    """
    Get a widget by type.

    Args:
        widget_type: Currently only 'calendly' is supported
        **kwargs: Additional arguments for the widget

    Returns:
        UIResource or None if widget type not found
    """
    creator = AVAILABLE_WIDGETS.get(widget_type)
    if creator:
        return creator(**kwargs) if kwargs else creator()
    return None
