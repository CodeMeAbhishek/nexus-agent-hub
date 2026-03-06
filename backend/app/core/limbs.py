"""
Central limb registry — single source of truth for routes, keywords, and tool counts.
Adding a new limb requires editing only this file and the corresponding MCP/tool loader in agent/graph.
"""
from __future__ import annotations

from typing import TypedDict


class LimbDefinition(TypedDict):
    id: str
    name: str
    route: str  # Used in agent routing (may differ from id, e.g. googledrive -> drive)
    keywords: list[str]
    tools_count: int


# Conversational has no limb; it's a route only.
CONVERSATIONAL_KEYWORDS = [
    "hi", "hello", "hey", "thanks", "who are you", "what are you",
    "write a poem", "tell me a joke", "help me understand",
]

LIMB_DEFINITIONS: list[LimbDefinition] = [
    {
        "id": "notion",
        "name": "Notion",
        "route": "notion",
        "keywords": ["notion", "page", "workspace", "database", "block"],
        "tools_count": 10,
    },
    {
        "id": "slack",
        "name": "Slack",
        "route": "slack",
        "keywords": ["slack", "channel", "#general", "#", "dm ", "post to"],
        "tools_count": 10,
    },
    {
        "id": "github",
        "name": "GitHub",
        "route": "github",
        "keywords": [
            "github", "repo", "repository", "issue", "pull request", "pr",
            "commit", "branch", "code",
        ],
        "tools_count": 5,
    },
    {
        "id": "gmail",
        "name": "Gmail",
        "route": "gmail",
        "keywords": ["email", "gmail", "inbox", "mail", "send mail", "unread"],
        "tools_count": 3,
    },
    {
        "id": "calendar",
        "name": "Google Calendar",
        "route": "calendar",
        "keywords": ["calendar", "schedule", "event", "meeting", "appointment", "standup"],
        "tools_count": 3,
    },
    {
        "id": "googledrive",
        "name": "Google Drive",
        "route": "drive",
        "keywords": [
            "drive", "gdrive", "google drive", "document", "spreadsheet", "sheet",
            "slides", "doc", "file", "pdf", "summarise", "summarize", "read the file",
        ],
        "tools_count": 3,
    },
    {
        "id": "mongodb",
        "name": "MongoDB",
        "route": "mongodb",
        "keywords": ["mongo", "mongodb", "collection", "aggregate", "pipeline"],
        "tools_count": 3,
    },
    {
        "id": "filesystem",
        "name": "Local Files",
        "route": "filesystem",
        "keywords": [],  # No keyword routing; optional future limb
        "tools_count": 0,
    },
]


def get_all_limb_keywords() -> set[str]:
    """All keywords from limbs; used to detect if a query might need any tool."""
    out: set[str] = set()
    for limb in LIMB_DEFINITIONS:
        out.update(kw for kw in limb["keywords"] if kw)
    return out


def get_keyword_routes() -> dict[str, list[str]]:
    """Route name -> list of keywords. Used only for conversational detection."""
    routes: dict[str, list[str]] = {}
    for limb in LIMB_DEFINITIONS:
        if limb["keywords"]:
            routes[limb["route"]] = limb["keywords"]
    routes["conversational"] = CONVERSATIONAL_KEYWORDS
    return routes


def get_all_limbs_for_api() -> list[dict]:
    """Default limb list for /api/tools (id, name, status, tools_count). Status filled by caller."""
    return [
        {
            "id": limb["id"],
            "name": limb["name"],
            "status": "disconnected",
            "tools_count": limb["tools_count"],
        }
        for limb in LIMB_DEFINITIONS
    ]


def get_tools_count(limb_id: str) -> int:
    """Return tools_count for a limb by id (e.g. 'slack', 'googledrive')."""
    for limb in LIMB_DEFINITIONS:
        if limb["id"] == limb_id:
            return limb["tools_count"]
    return 0


def get_valid_limb_ids() -> set[str]:
    """Set of limb ids accepted by settings/connect and DB."""
    return {limb["id"] for limb in LIMB_DEFINITIONS}


def get_route_names() -> set[str]:
    """Set of route names used in agent graph (e.g. 'notion', 'slack', 'general')."""
    return {"general"} | {limb["route"] for limb in LIMB_DEFINITIONS if limb["keywords"]}
