from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict


class ResearchPlan(TypedDict):
    original_query: str
    sub_queries: list[str]
    assigned_agents: list[str]
    estimated_duration_seconds: int
    estimated_tokens: int


class Source(TypedDict):
    title: str
    url: str
    snippet: str
    source_type: Literal["web", "news", "financial", "wikipedia"]


class AgentFinding(TypedDict):
    agent_name: str
    summary: str
    raw_data: str
    sources: list[Source]
    tokens_used: int
    duration_seconds: float
    error: str | None


class AgentState(TypedDict):
    user_query: str
    user_id: str
    session_id: str
    research_plan: ResearchPlan | None
    plan_approved: bool
    # operator.add: parallel agents append findings without overwriting (LangGraph fan-in)
    agent_findings: Annotated[list[AgentFinding], operator.add]
    synthesis_notes: str
    final_report: str
    citations: list[Source]
    total_tokens_used: int
    total_cost_usd: float
    error_message: str | None
    status: Literal[
        "planning",
        "awaiting_approval",
        "researching",
        "synthesizing",
        "complete",
        "failed",
    ]
