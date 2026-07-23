
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from azure.identity.aio import DefaultAzureCredential
from fastapi import FastAPI
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from tavily import AsyncTavilyClient

from app.backend.core.config import get_settings

logger = logging.getLogger(__name__)

# Module-level references — set during lifespan startup
_llm: AzureChatOpenAI | None = None
_tavily: AsyncTavilyClient | None = None
_graph_checkpointer: AsyncPostgresSaver | None = None
_checkpointer_ctx = None  # async context manager for AsyncPostgresSaver
_credential: DefaultAzureCredential | None = None
_compiled_graph: CompiledStateGraph | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _llm, _tavily, _graph_checkpointer, _checkpointer_ctx, _credential, _compiled_graph

    settings = get_settings()
    logger.info("Initialising Azure clients (env=%s)", settings.app_env)

    _credential = DefaultAzureCredential()

    from azure.identity import get_bearer_token_provider
    from azure.identity import DefaultAzureCredential as SyncCredential
    from app.backend.core.telemetry import get_langfuse_handler

    lf_handler = get_langfuse_handler()
    callbacks = [lf_handler] if lf_handler else []

    if settings.azure_openai_api_key:
        # Local dev — API key path. Production uses Managed Identity below.
        _llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
            api_key=settings.azure_openai_api_key,
            max_tokens=16384,
            callbacks=callbacks,
        )
        logger.info("AzureChatOpenAI initialised with API key (local dev)")
    else:
        token_provider = get_bearer_token_provider(
            SyncCredential(),
            "https://cognitiveservices.azure.com/.default",
        )
        _llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
            azure_ad_token_provider=token_provider,
            max_tokens=16384,
            callbacks=callbacks,
        )
        logger.info("AzureChatOpenAI initialised with Managed Identity")

    # Tavily key is fetched from Key Vault in production; falls back to .env locally
    tavily_key = await _get_secret_or_env("TAVILY_API_KEY", settings.tavily_api_key)
    _tavily = AsyncTavilyClient(api_key=tavily_key)
    logger.info("Tavily client initialised")

    # Neon.tech requires SSL; append sslmode if not already in the DSN
    dsn = settings.postgres_dsn
    if "sslmode" not in dsn:
        dsn += "?sslmode=require"
    _checkpointer_ctx = AsyncPostgresSaver.from_conn_string(dsn)
    _graph_checkpointer = await _checkpointer_ctx.__aenter__()
    await _graph_checkpointer.setup()  # creates LangGraph checkpoint tables on first run
    logger.info("PostgreSQL checkpointer ready at %s:%d", settings.postgres_host, settings.postgres_port)

    from app.backend.agents.graph import build_research_graph
    _compiled_graph = build_research_graph(_graph_checkpointer)
    logger.info("Research graph compiled and ready")

    app.state.llm = _llm
    app.state.tavily = _tavily
    app.state.checkpointer = _graph_checkpointer
    app.state.credential = _credential
    app.state.graph = _compiled_graph

    logger.info("All Azure clients ready — application startup complete")
    yield

    logger.info("Closing Azure clients")
    if _credential:
        await _credential.close()
    if _checkpointer_ctx is not None:
        await _checkpointer_ctx.__aexit__(None, None, None)


async def _get_secret_or_env(secret_name: str, env_fallback: str) -> str:
    settings = get_settings()
    if settings.azure_key_vault_url and _credential:
        try:
            from azure.keyvault.secrets.aio import SecretClient
            kv_client = SecretClient(
                vault_url=settings.azure_key_vault_url,
                credential=_credential,
            )
            secret = await kv_client.get_secret(secret_name.lower().replace("_", "-"))
            await kv_client.close()
            return secret.value or env_fallback
        except Exception as e:
            logger.warning("Could not fetch %s from Key Vault, using env fallback: %s", secret_name, e)
    return env_fallback


def get_llm() -> AzureChatOpenAI:
    if _llm is None:
        raise RuntimeError("LLM not initialised — lifespan not started")
    return _llm


def get_tavily_client() -> AsyncTavilyClient:
    if _tavily is None:
        raise RuntimeError("Tavily client not initialised — lifespan not started")
    return _tavily


def get_checkpointer() -> AsyncPostgresSaver:
    if _graph_checkpointer is None:
        raise RuntimeError("Checkpointer not initialised — lifespan not started")
    return _graph_checkpointer


def get_graph() -> CompiledStateGraph:
    if _compiled_graph is None:
        raise RuntimeError("Research graph not compiled — lifespan not started")
    return _compiled_graph
