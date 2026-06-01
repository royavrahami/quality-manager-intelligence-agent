"""Shared notification helpers used across the email/slack/console channels."""

from __future__ import annotations

# Category display metadata for Quality Management Intelligence
_CATEGORY_META: dict[str, dict[str, str]] = {
    "genai":              {"label": "GenAI & LLMs",           "icon": "🤖", "color": "#155e75", "bg": "#cffafe"},
    "agents":             {"label": "AI Agents & Automation", "icon": "🕵️", "color": "#4a1d96", "bg": "#f3e8ff"},
    "qa_testing":         {"label": "Quality Engineering",    "icon": "🧪", "color": "#065f46", "bg": "#d1fae5"},
    "devops":             {"label": "DevOps & CI/CD",         "icon": "⚙️", "color": "#92400e", "bg": "#fef3c7"},
    "tools":              {"label": "Developer Tools",        "icon": "🛠️", "color": "#1d4ed8", "bg": "#dbeafe"},
    "project_management": {"label": "Project Management",     "icon": "📋", "color": "#9f1239", "bg": "#ffe4e6"},
    "general":            {"label": "Industry News",          "icon": "📰", "color": "#374151", "bg": "#f3f4f6"},
}


def _score_color(score: float) -> str:
    if score >= 75:
        return "#059669"
    if score >= 55:
        return "#d97706"
    return "#6b7280"
