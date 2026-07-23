
from __future__ import annotations

import logging
import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from app.backend.agents.state import AgentState, Source
from app.backend.core.azure_clients import get_llm

logger = logging.getLogger(__name__)

# gpt-5-mini pricing (update if model or pricing changes)
_COST_PER_1K_INPUT_TOKENS = 0.0025
_COST_PER_1K_OUTPUT_TOKENS = 0.010

_SYNTHESIS_SYSTEM = """You are a senior research analyst writing an executive research report.

You have received findings from multiple research agents. Your job is to:
1. Cross-reference all findings for consistency
2. Note any contradictions between sources
3. Write a clear, structured research report

Report format (Markdown):
## Executive Summary
(2-3 sentence overview)

## Key Findings
(Bullet points with the most important discoveries)

## Detailed Analysis
(3-5 paragraphs synthesising all agent findings)

## Market & Financial Context
(Financial data and market position, if available)

## Recent Developments
(News and sentiment analysis)

## Conclusions
(What this research reveals and what it means)

## Sources
(Numbered list of all sources used — [1] Title — URL)

Rules:
- Cite sources inline as [1], [2], etc.
- State clearly when data is missing or unavailable
- Be factual — do not speculate beyond what the data shows
- Flag any contradictions between sources"""


async def synthesis_node(state: AgentState) -> dict:
    logger.info(
        "Synthesis Agent starting with %d agent findings for session=%s",
        len(state.get("agent_findings", [])),
        state["session_id"],
    )
    start = time.monotonic()

    findings = state.get("agent_findings", [])

    if not findings:
        logger.warning("No agent findings available for synthesis session=%s", state["session_id"])
        return {
            "final_report": "No research data was collected. All agents may have failed.",
            "status": "failed",
            "citations": [],
            "total_tokens_used": 0,
            "total_cost_usd": 0.0,
        }

    findings_text = _format_findings_for_llm(findings)

    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=_SYNTHESIS_SYSTEM),
        HumanMessage(content=f"""Original research query: {state['user_query']}

Agent Findings:
{findings_text}

Write the research report now."""),
    ])

    chain = prompt | llm
    response = await chain.ainvoke({})
    final_report = response.content

    agent_input_tokens = sum(f.get("tokens_used", 0) for f in findings)
    all_sources = []
    for finding in findings:
        all_sources.extend(finding.get("sources", []))

    # Exclude sources with empty URLs to avoid dedup collisions on unresolved entries
    seen_urls: set[str] = set()
    unique_sources: list[Source] = []
    for src in all_sources:
        url = src.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_sources.append(src)

    synthesis_output_tokens = len(final_report) // 4
    total_tokens = agent_input_tokens + synthesis_output_tokens
    cost_usd = (
        (agent_input_tokens / 1000) * _COST_PER_1K_INPUT_TOKENS
        + (synthesis_output_tokens / 1000) * _COST_PER_1K_OUTPUT_TOKENS
    )

    duration = round(time.monotonic() - start, 2)
    logger.info(
        "Synthesis complete in %.1fs total_tokens=%d cost_usd=%.4f session=%s",
        duration, total_tokens, cost_usd, state["session_id"],
    )

    return {
        "final_report": final_report,
        "citations": unique_sources,
        "total_tokens_used": total_tokens,
        "total_cost_usd": round(cost_usd, 4),
        "status": "complete",
    }


def _format_findings_for_llm(findings: list) -> str:
    sections = []
    for finding in findings:
        agent = finding.get("agent_name", "unknown")
        summary = finding.get("summary", "No data")
        error = finding.get("error")
        sources = finding.get("sources", [])

        section = f"### {agent.replace('_', ' ').title()} Agent\n"
        if error:
            section += f"⚠️ Partial data (agent had an error: {error})\n"
        section += f"{summary}\n"
        if sources:
            section += f"Sources: {', '.join(s.get('url', s.get('title', '')) for s in sources[:3])}\n"
        sections.append(section)

    return "\n".join(sections)
