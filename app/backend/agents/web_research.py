
from __future__ import annotations

import logging
import time

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from app.backend.agents.state import AgentFinding, AgentState
from app.backend.core.azure_clients import get_llm
from app.backend.tools.web_search import web_search_tool
from app.backend.tools.wikipedia import wikipedia_tool

logger = logging.getLogger(__name__)

_WEB_RESEARCH_SYSTEM = """You are a web research specialist. Your job is to search the web
and Wikipedia for accurate, current information to answer research questions.

Instructions:
- Use web_search for current events, recent developments, and general information
- Use wikipedia_search for factual background, definitions, and historical context
- Synthesise findings into a clear, factual summary (3-5 paragraphs)
- List all sources you used
- Focus on accuracy — if you are not certain, say so
- Do NOT speculate or add information not found in your searches"""


async def web_research_node(state: AgentState) -> dict:
    logger.info("Web Research Agent starting for session=%s", state["session_id"])
    start = time.monotonic()

    plan = state.get("research_plan")
    query = plan["original_query"] if plan else state["user_query"]
    sub_queries = plan["sub_queries"] if plan else [query]

    agent_executor = create_react_agent(
        model=get_llm(),
        tools=[web_search_tool, wikipedia_tool],
        prompt=_WEB_RESEARCH_SYSTEM,
    )

    research_prompt = f"""Research the following:

Main query: {query}

Sub-questions to address:
{chr(10).join(f"- {q}" for q in sub_queries[:3])}

Search the web and Wikipedia. Provide a thorough summary with all sources."""

    result = await agent_executor.ainvoke({
        "messages": [HumanMessage(content=research_prompt)]
    })

    final_message = result["messages"][-1]
    summary = final_message.content if hasattr(final_message, "content") else str(final_message)
    sources = _extract_sources_from_messages(result["messages"])

    duration = round(time.monotonic() - start, 2)
    logger.info("Web Research Agent completed in %.1fs for session=%s", duration, state["session_id"])

    finding = AgentFinding(
        agent_name="web_research",
        summary=summary,
        raw_data=summary,
        sources=sources,
        tokens_used=_estimate_tokens(result["messages"]),
        duration_seconds=duration,
        error=None,
    )

    return {"agent_findings": [finding]}


def web_research_error_handler(state: AgentState, error: Exception) -> dict:
    """Inserts a partial finding on retry exhaustion so synthesis can still run."""
    logger.error("Web Research Agent failed after retries: %s", error.error)
    finding = AgentFinding(
        agent_name="web_research",
        summary="Web research unavailable — service temporarily unreachable.",
        raw_data="",
        sources=[],
        tokens_used=0,
        duration_seconds=0.0,
        error=str(error.error),
    )
    return {"agent_findings": [finding]}


def _extract_sources_from_messages(messages: list) -> list:
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
        current_title = "Web source"
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
                        source_type="web",
                    ))
    return sources


def _estimate_tokens(messages: list) -> int:
    from app.backend.agents.utils import estimate_tokens
    return estimate_tokens(messages)
