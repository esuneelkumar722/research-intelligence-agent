
from __future__ import annotations

import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy

from app.backend.agents.market_data import market_data_node
from app.backend.agents.news_sentiment import news_sentiment_node
from app.backend.agents.state import AgentState
from app.backend.agents.supervisor import planning_node, supervisor_node
from app.backend.agents.synthesis import synthesis_node
from app.backend.agents.web_research import web_research_node

logger = logging.getLogger(__name__)

_RESEARCH_RETRY = RetryPolicy(
    initial_interval=1.0,
    backoff_factor=2.0,
    max_interval=30.0,
    max_attempts=3,
    jitter=True,
)

_SUPERVISOR_RETRY = RetryPolicy(
    initial_interval=0.5,
    backoff_factor=2.0,
    max_attempts=2,
)


def build_research_graph(checkpointer: AsyncPostgresSaver) -> CompiledStateGraph:
    graph = StateGraph(AgentState)

    graph.add_node(
        "planning",
        planning_node,
        retry=_SUPERVISOR_RETRY,
    )
    graph.add_node(
        "supervisor",
        supervisor_node,
        retry=_SUPERVISOR_RETRY,
    )
    graph.add_node(
        "web_research",
        web_research_node,
        retry=_RESEARCH_RETRY,
    )
    graph.add_node(
        "market_data",
        market_data_node,
        retry=_RESEARCH_RETRY,
    )
    graph.add_node(
        "news_sentiment",
        news_sentiment_node,
        retry=_RESEARCH_RETRY,
    )
    graph.add_node(
        "synthesis",
        synthesis_node,
        retry=_SUPERVISOR_RETRY,
    )

    graph.add_edge(START, "planning")
    graph.add_edge("web_research", "synthesis")
    graph.add_edge("market_data", "synthesis")
    graph.add_edge("news_sentiment", "synthesis")

    graph.add_edge("synthesis", END)

    # interrupt_before is not set — interrupt() is called inside supervisor_node directly
    compiled = graph.compile(checkpointer=checkpointer)
    logger.info("Research graph compiled successfully")
    return compiled
