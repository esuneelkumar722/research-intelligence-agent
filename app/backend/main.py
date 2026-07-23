from __future__ import annotations

import asyncio
import logging
import os
import sys

import uvicorn

# psycopg requires SelectorEventLoop; Windows defaults to ProactorEventLoop since Python 3.8
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.backend.core.config import get_settings


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    uvicorn.run(
        "app.backend.app:create_app",
        factory=True,
        host="0.0.0.0",  # noqa: S104 — intentional for container binding
        port=int(os.getenv("PORT", "8000")),
        reload=not settings.is_production,
        log_level=settings.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
