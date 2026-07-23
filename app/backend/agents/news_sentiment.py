
from __future__ import annotations

import logging
import time

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from app.backend.agents.state import AgentFinding, AgentState
from app.backend.core.azure_clients import get_llm
from app.backend.tools.news_search import news_search_tool

logger = logging.getLogger(__name__)

_NEWS_SENTIMENT_SYSTEM = """You are a news analyst specialising in sentiment analysis.

Instructions:
- Use news_search to find recent news articles (last 7 days)
- Analyse the overall sentiment: Positive / Neutral / Negative / Mixed
- Identify the top 3-5 themes from the news
- Note any significant events, controversies, or announcements
- Quantify sentiment where possible (e.g., "8 of 10 articles positive")
- Be objective — report what the news says, not your opinion"""


async def news_sentiment_node(state: AgentState) -> dict:
    logger.info("News Sentiment Agent starting for session=%s", state["session_id"])
    start = time.monotonic()

    plan = state.get("research_plan")
    query = plan["original_query"] if plan else state["user_query"]

    agent_executor = create_react_agent(
        model=get_llm(),
        tools=[news_search_tool],
        prompt=_NEWS_SENTIMENT_SYSTEM,
    )

    research_prompt = f"""Find and analyse recent news related to: {query}

Search for news from the last 7 days. Provide:
1. Overall sentiment (Positive/Negative/Neutral/Mixed)
2. Top 3-5 news themes or headlines
3. Any significant recent events
4. Sentiment trend (improving/declining/stable)"""

    result = await agent_executor.ainvoke({
        "messages": [HumanMessage(content=research_prompt)]
    })

    final_message = result["messages"][-1]
    summary = final_message.content if hasattr(final_message, "content") else str(final_message)

    sources = _extract_news_sources(result["messages"])
    duration = round(time.monotonic() - start, 2)
    logger.info("News Sentiment Agent completed in %.1fs for session=%s", duration, state["session_id"])

    finding = AgentFinding(
        agent_name="news_sentiment",
        summary=summary,
        raw_data=summary,
        sources=sources,
        tokens_used=_estimate_tokens(result["messages"]),
        duration_seconds=duration,
        error=None,
    )

    return {"agent_findings": [finding]}


def news_sentiment_error_handler(state: AgentState, error: Exception) -> dict:
    """Inserts a partial finding on retry exhaustion so synthesis can still run."""
    logger.error("News Sentiment Agent failed after retries: %s", error.error)
    finding = AgentFinding(
        agent_name="news_sentiment",
        summary="News data unavailable — news search service temporarily unreachable.",
        raw_data="",
        sources=[],
        tokens_used=0,
        duration_seconds=0.0,
        error=str(error.error),
    )
    return {"agent_findings": [finding]}


def _extract_news_sources(messages: list) -> list:
    import re
    from app.backend.agents.state import Source

    sources: list[Source] = []
    seen_urls: set[str] = set()
    url_line_re = re.compile(r"URL:\s*(https?://\S+)")
    title_line_re = re.compile(r"\[(\d+)\]\s*(.+)")

    for msg in messages:
        if getattr(msg, "type", None) != "tool":
            continue
        content = str(getattr(msg, "content", ""))
        lines = content.splitlines()
        current_title = "News source"
        for line in lines:
            title_match = title_line_re.match(line.strip())
            if title_match:
                current_title = title_match.group(2).strip()
            url_match = url_line_re.search(line)
            if url_match:
                url = url_match.group(1).rstrip(".,)")
                if url not in seen_urls and len(sources) < 5:
                    seen_urls.add(url)
                    sources.append(Source(
                        title=current_title,
                        url=url,
                        snippet=content[:200],
                        source_type="news",
                    ))
    return sources


def _estimate_tokens(messages: list) -> int:
    from app.backend.agents.utils import estimate_tokens
    return estimate_tokens(messages)
