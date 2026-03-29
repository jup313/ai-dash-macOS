"""
Web Search integration for ai-dash chat.

Uses DuckDuckGo to fetch real-time web results and inject them
as context into the LLM system prompt — giving your local Ollama
model access to current internet information.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def web_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """
    Search the web using DuckDuckGo (no API key needed).

    Returns a list of result dicts with keys: title, href, body.
    """
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return results
    except ImportError:
        logger.error("duckduckgo-search not installed. Run: pip install duckduckgo-search")
        return []
    except Exception as exc:
        logger.error("Web search error: %s", exc, exc_info=True)
        return []


async def web_search_news(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search DuckDuckGo news."""
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))
            return results
    except Exception as exc:
        logger.error("Web news search error: %s", exc, exc_info=True)
        return []


async def fetch_search_context(query: str, max_results: int = 5) -> str | None:
    """
    Perform a web search and format results as context for the LLM.

    Returns a formatted string the LLM can reference, or None on failure.
    """
    results = await web_search(query, max_results=max_results)

    if not results:
        return None

    formatted: list[str] = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")
        url = r.get("href", r.get("link", ""))
        snippet = r.get("body", r.get("snippet", ""))
        formatted.append(f"[{i}] {title}\n    URL: {url}\n    {snippet}")

    return (
        "=== WEB SEARCH RESULTS ===\n"
        f"Query: \"{query}\"\n\n"
        + "\n\n".join(formatted)
        + "\n\n=== END SEARCH RESULTS ===\n"
        "Use the search results above to provide an accurate, up-to-date answer. "
        "Cite sources by referencing the result number [1], [2], etc. when relevant. "
        "If the search results don't fully answer the question, say so and provide "
        "what you can from both the results and your training data."
    )


def should_search(text: str) -> bool:
    """
    Heuristic: detect if a query would benefit from web search.

    Returns True for questions about current events, facts, prices,
    weather, news, specific people/companies, etc.
    """
    text_lower = text.lower()

    # Explicit search triggers
    search_triggers = [
        "search for", "look up", "google", "find out", "search the web",
        "what is the latest", "current", "today", "right now",
        "news about", "price of", "weather in", "how much does",
        "who won", "when did", "where is", "score of",
        "stock price", "crypto", "bitcoin",
        "release date", "new version", "update on",
    ]
    if any(trigger in text_lower for trigger in search_triggers):
        return True

    # Question patterns that often need current data
    question_words = ["what is", "who is", "where is", "when is", "how to", "why is", "how much"]
    # Only auto-trigger for questions that seem to need current info
    current_markers = [
        "2024", "2025", "2026", "latest", "new", "recent", "current",
        "now", "today", "this week", "this month", "this year",
    ]
    if any(qw in text_lower for qw in question_words) and any(cm in text_lower for cm in current_markers):
        return True

    return False
