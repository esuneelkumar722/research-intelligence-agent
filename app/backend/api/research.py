# Two approval workflows per session (do NOT mix them for the same session):
#   A) Sync:      POST /approve (blocks until done) → GET /result
#   B) Streaming: GET /stream?approved=true (resumes graph + streams live events)

from __future__ import annotations

import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from app.backend.agents.state import AgentState
from app.backend.core.azure_clients import get_graph
from app.backend.core.content_safety import check_input_safety
from app.backend.models.research import (
    PlanApprovalRequest,
    ResearchRequest,
    ResearchResultResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/research", tags=["research"])


@router.post("/start", status_code=status.HTTP_202_ACCEPTED)
async def start_research(
    request: Request,
    body: ResearchRequest,
) -> dict:
    await check_input_safety(body.query)

    session_id = str(uuid.uuid4())
    user_id = getattr(request.state, "user_id", "anonymous")

    initial_state = AgentState(
        user_query=body.query,
        user_id=user_id,
        session_id=session_id,
        research_plan=None,
        plan_approved=False,
        agent_findings=[],
        synthesis_notes="",
        final_report="",
        citations=[],
        total_tokens_used=0,
        total_cost_usd=0.0,
        error_message=None,
        status="planning",
    )

    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}

    try:
        await graph.ainvoke(initial_state, config=config)

        current_state = await graph.aget_state(config)
        interrupt_value = None

        if current_state.tasks:
            for task in current_state.tasks:
                if hasattr(task, "interrupts") and task.interrupts:
                    interrupt_value = task.interrupts[0].value
                    break

        if interrupt_value and interrupt_value.get("type") == "plan_approval":
            plan = interrupt_value["plan"]
            return {
                "session_id": session_id,
                "status": "awaiting_approval",
                "plan": plan,
                "message": (
                    "Review the research plan and call "
                    "POST /research/{session_id}/approve to proceed, "
                    "or GET /research/{session_id}/stream?approved=true to stream live."
                ),
            }

        state_values = current_state.values or {}
        return {
            "session_id": session_id,
            "status": state_values.get("status", "unknown"),
            "message": state_values.get("error_message", "Research complete"),
        }

    except Exception as e:
        logger.exception("Failed to start research session=%s", session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start research. Please try again.",
        ) from e


@router.post("/{session_id}/approve")
async def approve_plan(
    request: Request,
    session_id: str,
    body: PlanApprovalRequest,
) -> dict:
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}

    state = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session '{session_id}' not found.",
        )

    try:
        await graph.ainvoke(
            Command(resume={"approved": body.approved, "feedback": body.feedback}),
            config=config,
        )

        if body.approved:
            return {
                "session_id": session_id,
                "status": "complete",
                "message": "Research complete. Fetch report at GET /research/{session_id}/result",
            }
        return {
            "session_id": session_id,
            "status": "failed",
            "message": "Research cancelled.",
        }

    except Exception as e:
        logger.exception("Failed to resume session=%s", session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume research session. Please try again.",
        ) from e


@router.get("/{session_id}/stream")
async def stream_research_events(
    request: Request,
    session_id: str,
    approved: bool = True,
    feedback: str = "",
) -> StreamingResponse:
    """SSE stream. If graph is at an interrupt, resumes it using the approved/feedback params."""
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}

    state = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session '{session_id}' not found.",
        )

    is_interrupted = any(
        hasattr(task, "interrupts") and task.interrupts
        for task in (state.tasks or [])
    )
    stream_input = (
        Command(resume={"approved": approved, "feedback": feedback})
        if is_interrupted
        else None
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for event in graph.astream_events(stream_input, config=config, version="v2"):
                event_type = event.get("event", "")
                name = event.get("name", "")
                data = event.get("data", {})

                if event_type == "on_chain_start" and name in (
                    "web_research", "market_data", "news_sentiment", "synthesis"
                ):
                    yield _sse({"event": "agent_start", "agent": name})

                elif event_type == "on_chain_end" and name in (
                    "web_research", "market_data", "news_sentiment", "synthesis"
                ):
                    yield _sse({"event": "agent_complete", "agent": name})

                elif (
                    event_type == "on_chain_end"
                    and name == "LangGraph"
                    and not event.get("parent_ids")  # outer graph only — not inner create_react_agent graphs
                ):
                    output = data.get("output", {})
                    yield _sse({
                        "event": "complete",
                        "session_id": session_id,
                        "status": output.get("status", "complete"),
                    })

                if await request.is_disconnected():
                    break

        except Exception as e:
            logger.exception("SSE stream error for session=%s", session_id)
            yield _sse({"event": "error", "message": f"Stream error: {type(e).__name__}: {e}"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{session_id}/status")
async def get_status(session_id: str) -> dict:
    """Poll-based status check for clients that cannot use SSE."""
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}

    state = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    values = state.values
    return {
        "session_id": session_id,
        "status": values.get("status", "unknown"),
        "agents_done": [f["agent_name"] for f in values.get("agent_findings", [])],
    }


@router.get("/{session_id}/result", response_model=ResearchResultResponse)
async def get_result(session_id: str) -> ResearchResultResponse:
    """Fetch the completed research report for a session."""
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}

    state = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    values = state.values
    if values.get("status") not in ("complete", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Research not complete yet. Current status: {values.get('status')}",
        )

    return ResearchResultResponse(
        session_id=session_id,
        query=values.get("user_query", ""),
        final_report=values.get("final_report", ""),
        citations=values.get("citations", []),
        total_tokens_used=values.get("total_tokens_used", 0),
        total_cost_usd=values.get("total_cost_usd", 0.0),
        agents_used=[f["agent_name"] for f in values.get("agent_findings", [])],
        status=values.get("status", "unknown"),
    )


def _sse(data: dict) -> str:
    """Format a Server-Sent Event string."""
    return f"data: {json.dumps(data)}\n\n"
