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
    html = f'''<!DOCTYPE html>
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
            min-height: 650px;
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
            height: 600px;
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
        content=html
    )


def create_contact_card() -> UIResource:
    """
    Create Giuseppe's contact card as MCP-UI resource.

    Returns:
        UIResource containing the contact card widget
    """
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: transparent;
        }
        .card {
            background: linear-gradient(135deg, #1e3a5f 0%, #0f0f23 100%);
            border-radius: 16px;
            padding: 24px;
            color: #fff;
            max-width: 400px;
        }
        .card-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 20px;
        }
        .avatar {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            font-weight: bold;
        }
        .name {
            font-size: 20px;
            font-weight: 600;
        }
        .title {
            font-size: 14px;
            color: #94a3b8;
            margin-top: 4px;
        }
        .info-row {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .info-row:last-child {
            border-bottom: none;
        }
        .info-row .icon {
            font-size: 18px;
            width: 24px;
            text-align: center;
        }
        .info-row a {
            color: #60a5fa;
            text-decoration: none;
            transition: color 0.2s;
        }
        .info-row a:hover {
            color: #93c5fd;
            text-decoration: underline;
        }
        .info-row span {
            color: #e2e8f0;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="card-header">
            <div class="avatar">GR</div>
            <div>
                <div class="name">Giuseppe Rumore</div>
                <div class="title">AI Agent & MLOps Engineer</div>
            </div>
        </div>
        <div class="info-row">
            <span class="icon">📍</span>
            <span>Berlin, Germany</span>
        </div>
        <div class="info-row">
            <span class="icon">📧</span>
            <a href="mailto:pepperumo@gmail.com">pepperumo@gmail.com</a>
        </div>
        <div class="info-row">
            <span class="icon">💼</span>
            <a href="https://linkedin.com/in/giuseppe-rumore-b2599961" target="_blank">LinkedIn Profile</a>
        </div>
        <div class="info-row">
            <span class="icon">💻</span>
            <a href="https://github.com/pepperumo" target="_blank">GitHub Profile</a>
        </div>
        <div class="info-row">
            <span class="icon">🌐</span>
            <a href="https://peppegpt.com" target="_blank">peppegpt.com</a>
        </div>
    </div>
</body>
</html>'''

    return UIResource(
        uri="ui://contact/card",
        mime_type="text/html",
        content=html
    )


def create_github_repos_widget() -> UIResource:
    """
    Create a GitHub repositories showcase widget.

    Returns:
        UIResource containing the GitHub repos widget
    """
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: transparent;
        }
        .widget {
            background: #0f0f23;
            border-radius: 12px;
            padding: 20px;
            color: #fff;
        }
        .widget-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .repo-grid {
            display: grid;
            gap: 12px;
        }
        .repo-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 16px;
            transition: all 0.2s;
        }
        .repo-card:hover {
            background: rgba(255,255,255,0.08);
            border-color: #3b82f6;
        }
        .repo-name {
            font-weight: 600;
            color: #60a5fa;
            text-decoration: none;
            font-size: 15px;
        }
        .repo-name:hover {
            text-decoration: underline;
        }
        .repo-desc {
            font-size: 13px;
            color: #94a3b8;
            margin-top: 8px;
            line-height: 1.4;
        }
        .repo-tags {
            display: flex;
            gap: 8px;
            margin-top: 12px;
            flex-wrap: wrap;
        }
        .tag {
            font-size: 11px;
            padding: 4px 8px;
            background: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="widget">
        <div class="widget-title">💻 Featured Projects</div>
        <div class="repo-grid">
            <div class="repo-card">
                <a class="repo-name" href="https://github.com/pepperumo/peppegpt" target="_blank">peppegpt</a>
                <div class="repo-desc">Full-stack AI chatbot with LangGraph agents, RAG pipeline, and real-time streaming</div>
                <div class="repo-tags">
                    <span class="tag">Python</span>
                    <span class="tag">React</span>
                    <span class="tag">LangGraph</span>
                    <span class="tag">RAG</span>
                </div>
            </div>
            <div class="repo-card">
                <a class="repo-name" href="https://github.com/pepperumo" target="_blank">More projects →</a>
                <div class="repo-desc">Explore more AI/ML projects including vehicle damage detection, recommender systems, and automation tools</div>
                <div class="repo-tags">
                    <span class="tag">YOLOv8</span>
                    <span class="tag">FastAPI</span>
                    <span class="tag">n8n</span>
                </div>
            </div>
        </div>
    </div>
</body>
</html>'''

    return UIResource(
        uri="ui://github/repos",
        mime_type="text/html",
        content=html
    )


# Widget registry for easy lookup
AVAILABLE_WIDGETS = {
    "calendly": create_calendly_widget,
    "contact": create_contact_card,
    "github": create_github_repos_widget,
}


def get_widget(widget_type: str, **kwargs) -> Optional[UIResource]:
    """
    Get a widget by type.

    Args:
        widget_type: One of 'calendly', 'contact', 'github'
        **kwargs: Additional arguments for the widget

    Returns:
        UIResource or None if widget type not found
    """
    creator = AVAILABLE_WIDGETS.get(widget_type)
    if creator:
        return creator(**kwargs) if kwargs else creator()
    return None
