# Split supervisor: planning_node (LLM call) → supervisor_node (interrupt only).
# LangGraph re-runs the entire node on interrupt resume, so the LLM call and interrupt
# must live in separate nodes to avoid calling the LLM twice.

from __future__ import annotations

import logging
import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Command, Send, interrupt

from app.backend.agents.state import AgentState, ResearchPlan
from app.backend.core.azure_clients import get_llm

logger = logging.getLogger(__name__)

_SUPERVISOR_SYSTEM_PROMPT = """You are a senior research analyst. Given a research query,
produce a structured JSON research plan that breaks the query into focused sub-questions
and assigns ONLY the agents that are genuinely useful for that query.

Available agents — include an agent ONLY if it will meaningfully contribute:
- web_research: General knowledge, technology topics, comparisons, definitions, trends, current events. Include for almost all queries.
- market_data: Stock prices, revenue, earnings, P/E ratios, company financials, market cap. Include ONLY when the query explicitly asks about financial performance, stock data, or company financials. Do NOT include for conceptual, educational, or strategic questions.
- news_sentiment: Recent news headlines, public sentiment, media coverage. Include when the query involves current perception, recent developments, or public reaction to a topic.

Rules:
- Assign ONLY agents that will produce meaningful output for this specific query
- Each agent name MUST appear at most ONCE — never repeat the same agent
- Break complex queries into 2-4 focused sub-questions
- Estimate total tokens needed (rough estimate: 500-2000 per agent)

Examples:
- "What is Agentic AI?" -> assigned_agents: ["web_research", "news_sentiment"]
- "NVIDIA stock performance 2025" -> assigned_agents: ["web_research", "market_data", "news_sentiment"]
- "Compare cloud strategies of AWS vs Azure" -> assigned_agents: ["web_research", "news_sentiment"]
- "Microsoft Q4 earnings and revenue growth" -> assigned_agents: ["web_research", "market_data", "news_sentiment"]

Return ONLY valid JSON matching this schema:
{
  "original_query": "string",
  "sub_queries": ["string"],
  "assigned_agents": ["web_research", "news_sentiment"],
  "estimated_duration_seconds": 30,
  "estimated_tokens": 3000
}"""


async def planning_node(state: AgentState) -> Command:
    logger.info("Planning starting for session=%s query=%r", state["session_id"], state["user_query"][:80])
    start = time.monotonic()

    llm = get_llm()
    parser = JsonOutputParser()

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=_SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=f"Research query: {state['user_query']}"),
    ])

    chain = prompt | llm | parser
    plan_dict: dict = await chain.ainvoke({})

    _valid_agents = {"web_research", "market_data", "news_sentiment"}
    _seen: set[str] = set()
    unique_agents: list[str] = []
    for a in plan_dict.get("assigned_agents", ["web_research", "market_data", "news_sentiment"]):
        if a in _valid_agents and a not in _seen:
            _seen.add(a)
            unique_agents.append(a)
    if not unique_agents:
        unique_agents = ["web_research", "market_data", "news_sentiment"]

    research_plan = ResearchPlan(
        original_query=state["user_query"],
        sub_queries=plan_dict.get("sub_queries", [state["user_query"]]),
        assigned_agents=unique_agents,
        estimated_duration_seconds=plan_dict.get("estimated_duration_seconds", 30),
        estimated_tokens=plan_dict.get("estimated_tokens", 3000),
    )

    logger.info(
        "Plan created in %.1fs: agents=%s estimated_tokens=%d",
        round(time.monotonic() - start, 2),
        research_plan["assigned_agents"],
        research_plan["estimated_tokens"],
    )

    return Command(
        update={"research_plan": research_plan},
        goto="supervisor",
    )


async def supervisor_node(state: AgentState) -> Command:
    research_plan = state["research_plan"]

    logger.info(
        "Awaiting approval for session=%s agents=%s",
        state["session_id"],
        research_plan["assigned_agents"],
    )

    approval_response = interrupt({
        "type": "plan_approval",
        "plan": research_plan,
        "message": "Review and approve the research plan before agents begin working.",
    })

    if not approval_response.get("approved", True):
        logger.info("Research plan rejected by user for session=%s", state["session_id"])
        return Command(
            update={
                "status": "failed",
                "error_message": "Research plan was rejected by user.",
            },
        )

    agents_to_run = research_plan["assigned_agents"]
    logger.info("Fanning out to %d agents in parallel: %s", len(agents_to_run), agents_to_run)

    return Command(
        update={
            "plan_approved": True,
            "status": "researching",
        },
        goto=[
            Send(agent_name, {**state, "research_plan": research_plan, "plan_approved": True})
            for agent_name in agents_to_run
        ],
    )
