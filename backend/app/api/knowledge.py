"""
Knowledge Base for local LLM training via web research.

Lets users search for topics and store the results locally so the LLM
can reference them in future conversations — like giving Ollama a
personal library of curated knowledge.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.web_search import web_search, web_search_news

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

# Storage path — persists in the backend data directory
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
KNOWLEDGE_FILE = KNOWLEDGE_DIR / "knowledge_base.json"


# ── Models ────────────────────────────────────────────────────────────────────

class KnowledgeEntry(BaseModel):
    """A single piece of learned knowledge."""
    id: str
    topic: str
    query: str
    sources: list[dict[str, Any]]
    summary: str
    learned_at: float
    tags: list[str] = []


class KnowledgeBase(BaseModel):
    """The full knowledge base."""
    entries: list[KnowledgeEntry] = []
    total_sources: int = 0


class LearnRequest(BaseModel):
    """Request to learn about a topic."""
    topic: str = Field(..., min_length=1, description="Topic to research")
    max_results: int = Field(default=8, ge=1, le=20, description="Number of sources to fetch")
    include_news: bool = Field(default=True, description="Also search news articles")
    tags: list[str] = Field(default=[], description="Optional tags for organization")


class LearnResponse(BaseModel):
    """Response after learning a topic."""
    id: str
    topic: str
    sources_found: int
    summary: str
    tags: list[str]


# ── Storage helpers ───────────────────────────────────────────────────────────

def _load_kb() -> KnowledgeBase:
    """Load knowledge base from disk."""
    if not KNOWLEDGE_FILE.exists():
        return KnowledgeBase()
    try:
        data = json.loads(KNOWLEDGE_FILE.read_text())
        return KnowledgeBase(**data)
    except Exception as exc:
        logger.error("Failed to load knowledge base: %s", exc)
        return KnowledgeBase()


def _save_kb(kb: KnowledgeBase) -> None:
    """Save knowledge base to disk."""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_FILE.write_text(json.dumps(kb.model_dump(), indent=2))


# ── Context injection for chat ────────────────────────────────────────────────

def search_knowledge(query: str, max_entries: int = 3) -> str | None:
    """
    Search the knowledge base for entries relevant to a chat query.
    Returns formatted context string or None.
    """
    kb = _load_kb()
    if not kb.entries:
        return None

    query_lower = query.lower()
    query_words = set(query_lower.split())

    # Score each entry by keyword overlap
    scored: list[tuple[float, KnowledgeEntry]] = []
    for entry in kb.entries:
        topic_words = set(entry.topic.lower().split())
        tag_words = {t.lower() for t in entry.tags}
        all_entry_words = topic_words | tag_words

        # Check topic match
        topic_in_query = entry.topic.lower() in query_lower
        word_overlap = len(query_words & all_entry_words)

        # Also check source content for keyword matches
        source_text = " ".join(
            (s.get("title", "") + " " + s.get("body", "")).lower()
            for s in entry.sources
        )
        content_matches = sum(1 for w in query_words if w in source_text and len(w) > 3)

        score = (10.0 if topic_in_query else 0.0) + word_overlap * 2.0 + content_matches * 0.5

        if score > 0:
            scored.append((score, entry))

    if not scored:
        return None

    # Sort by score descending, take top entries
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:max_entries]

    sections: list[str] = []
    for _score, entry in top:
        source_texts: list[str] = []
        for i, s in enumerate(entry.sources[:5], 1):
            title = s.get("title", "")
            body = s.get("body", s.get("snippet", ""))
            url = s.get("href", s.get("link", ""))
            source_texts.append(f"  [{i}] {title}\n      {body}\n      Source: {url}")

        sections.append(
            f"Topic: {entry.topic}\n"
            f"Tags: {', '.join(entry.tags) if entry.tags else 'none'}\n"
            f"Sources:\n" + "\n".join(source_texts)
        )

    return (
        "=== KNOWLEDGE BASE (previously researched topics) ===\n\n"
        + "\n\n---\n\n".join(sections)
        + "\n\n=== END KNOWLEDGE BASE ===\n"
        "Use the knowledge base above to provide informed answers. "
        "Cite sources when relevant."
    )


# ── API Endpoints ─────────────────────────────────────────────────────────────

@router.post("/learn", response_model=LearnResponse)
async def learn_topic(request: LearnRequest):
    """
    Research a topic by searching the web and storing results in the knowledge base.
    This gives your local LLM access to curated information on the topic.
    """
    logger.info("Learning about: %s", request.topic)

    # Search the web for this topic
    results = await web_search(request.topic, max_results=request.max_results)

    # Optionally include news
    if request.include_news:
        news = await web_search_news(request.topic, max_results=min(3, request.max_results))
        results.extend(news)

    if not results:
        raise HTTPException(status_code=404, detail=f"No results found for '{request.topic}'")

    # Build summary from top results
    snippets = [r.get("body", r.get("snippet", ""))[:200] for r in results[:5]]
    summary = f"Researched '{request.topic}' — found {len(results)} sources. " + " | ".join(snippets[:3])

    # Create knowledge entry
    entry_id = f"kb-{int(time.time())}-{hash(request.topic) % 10000:04d}"
    entry = KnowledgeEntry(
        id=entry_id,
        topic=request.topic,
        query=request.topic,
        sources=results,
        summary=summary[:500],
        learned_at=time.time(),
        tags=request.tags or [request.topic.split()[0].lower()],
    )

    # Save to knowledge base
    kb = _load_kb()
    kb.entries.append(entry)
    kb.total_sources = sum(len(e.sources) for e in kb.entries)
    _save_kb(kb)

    logger.info("Learned about '%s': %d sources stored", request.topic, len(results))

    return LearnResponse(
        id=entry_id,
        topic=request.topic,
        sources_found=len(results),
        summary=summary[:300],
        tags=entry.tags,
    )


@router.get("/topics")
async def list_topics():
    """List all learned topics in the knowledge base."""
    kb = _load_kb()
    topics = [
        {
            "id": e.id,
            "topic": e.topic,
            "sources": len(e.sources),
            "tags": e.tags,
            "learned_at": e.learned_at,
            "summary": e.summary[:200],
        }
        for e in kb.entries
    ]
    return {
        "total_topics": len(topics),
        "total_sources": kb.total_sources,
        "topics": topics,
    }


@router.get("/topics/{topic_id}")
async def get_topic(topic_id: str):
    """Get full details of a learned topic."""
    kb = _load_kb()
    for entry in kb.entries:
        if entry.id == topic_id:
            return entry.model_dump()
    raise HTTPException(status_code=404, detail="Topic not found")


@router.delete("/topics/{topic_id}")
async def delete_topic(topic_id: str):
    """Remove a topic from the knowledge base."""
    kb = _load_kb()
    original_len = len(kb.entries)
    kb.entries = [e for e in kb.entries if e.id != topic_id]
    if len(kb.entries) == original_len:
        raise HTTPException(status_code=404, detail="Topic not found")
    kb.total_sources = sum(len(e.sources) for e in kb.entries)
    _save_kb(kb)
    return {"deleted": True, "topic_id": topic_id}


@router.delete("/")
async def clear_knowledge():
    """Clear all knowledge base entries."""
    kb = KnowledgeBase()
    _save_kb(kb)
    return {"cleared": True}


@router.post("/search")
async def search_kb(query: str):
    """Search the knowledge base for relevant entries."""
    context = search_knowledge(query)
    if not context:
        return {"found": False, "context": None}
    return {"found": True, "context": context}
