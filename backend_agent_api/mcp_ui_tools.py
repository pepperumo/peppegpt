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
        content=html
    )


def create_github_widget(username: str = "pepperumo", repos: list = None) -> UIResource:
    """
    Create a GitHub profile/repos widget as MCP-UI resource.

    Args:
        username: GitHub username
        repos: List of repo dicts with name, description, language, stars, url

    Returns:
        UIResource containing the GitHub widget
    """
    # Build repo cards HTML
    repo_cards = ""
    if repos:
        for repo in repos[:6]:  # Show top 6 repos
            lang_color = {
                "Python": "#3572A5",
                "JavaScript": "#f1e05a",
                "TypeScript": "#2b7489",
                "HTML": "#e34c26",
                "CSS": "#563d7c",
                "Jupyter Notebook": "#DA5B0B",
            }.get(repo.get("language", ""), "#8b949e")

            lang_badge = f'''<span class="lang-badge" style="background: {lang_color}20; color: {lang_color};">{repo.get("language", "")}</span>''' if repo.get("language") else ""

            repo_cards += f'''
            <a class="repo-card" href="{repo.get("url", "#")}" target="_blank">
                <div class="repo-name">{repo.get("name", "")}</div>
                <div class="repo-desc">{repo.get("description", "No description")[:100]}</div>
                <div class="repo-meta">
                    {lang_badge}
                    <span class="stars">⭐ {repo.get("stars", 0)}</span>
                </div>
            </a>'''

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
        .widget {{
            background: #0f0f23;
            border-radius: 12px;
            padding: 20px;
            color: #fff;
        }}
        .header {{
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .avatar {{
            width: 64px;
            height: 64px;
            border-radius: 50%;
            border: 2px solid #3b82f6;
        }}
        .profile-info h2 {{
            font-size: 18px;
            margin-bottom: 4px;
        }}
        .profile-info a {{
            color: #60a5fa;
            text-decoration: none;
            font-size: 14px;
        }}
        .profile-info a:hover {{
            text-decoration: underline;
        }}
        .section-title {{
            font-size: 14px;
            color: #8b949e;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .repo-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 12px;
        }}
        .repo-card {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 14px;
            text-decoration: none;
            color: inherit;
            transition: all 0.2s;
            display: block;
        }}
        .repo-card:hover {{
            background: rgba(255,255,255,0.08);
            border-color: #3b82f6;
            transform: translateY(-2px);
        }}
        .repo-name {{
            font-weight: 600;
            color: #60a5fa;
            font-size: 14px;
            margin-bottom: 6px;
        }}
        .repo-desc {{
            font-size: 12px;
            color: #8b949e;
            line-height: 1.4;
            margin-bottom: 10px;
        }}
        .repo-meta {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 12px;
        }}
        .lang-badge {{
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
        }}
        .stars {{
            color: #8b949e;
        }}
        .view-all {{
            display: block;
            text-align: center;
            margin-top: 16px;
            padding: 10px;
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 8px;
            color: #60a5fa;
            text-decoration: none;
            font-size: 14px;
            transition: all 0.2s;
        }}
        .view-all:hover {{
            background: rgba(59, 130, 246, 0.2);
        }}
    </style>
</head>
<body>
    <div class="widget">
        <div class="header">
            <img class="avatar" src="https://github.com/{username}.png" alt="{username}">
            <div class="profile-info">
                <h2>Giuseppe Rumore</h2>
                <a href="https://github.com/{username}" target="_blank">@{username}</a>
            </div>
        </div>
        <div class="section-title">📦 Popular Repositories</div>
        <div class="repo-grid">
            {repo_cards}
        </div>
        <a class="view-all" href="https://github.com/{username}?tab=repositories" target="_blank">
            View all repositories →
        </a>
    </div>
</body>
</html>'''

    return UIResource(
        uri="ui://github/profile",
        mime_type="text/html",
        content=html
    )


# Widget registry for easy lookup
AVAILABLE_WIDGETS = {
    "calendly": create_calendly_widget,
    "github": create_github_widget,
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
