"""Public FastAPI entry point.

Runs:
- Telegram bot polling
- Delivery bot polling
- Public reseller API
- Documentation UI at /docs

Render start command:
uvicorn render_api:app --host 0.0.0.0 --port $PORT
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from api.reseller_v1 import router as reseller_router
from bot_app import bot, dp
from delivery_bot_app import delivery_bot, delivery_dp


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("render_api")


# ============================================================
# ENVIRONMENT
# ============================================================

PORT = int(os.getenv("PORT", "10000"))

BASE_DIR = Path(__file__).resolve().parent

# Put your full HTML UI here:
# static/docs/index.html
DOCS_FILE = BASE_DIR / "static" / "docs" / "index.html"


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    polling_task: asyncio.Task | None = None
    delivery_polling_task: asyncio.Task | None = None

    try:
        # Main Telegram bot

        await bot.delete_webhook(
            drop_pending_updates=True
        )

        me = await bot.get_me()

        logger.info(
            "Main Telegram bot connected: @%s",
            me.username,
        )

        # Main Telegram bot polling

        polling_task = asyncio.create_task(
            dp.start_polling(
                bot,
                handle_signals=False,
                close_bot_session=False,
            ),
            name="telegram-polling",
        )

        # Delivery bot polling

        if delivery_bot and delivery_dp:
            await delivery_bot.delete_webhook(
                drop_pending_updates=False
            )

            delivery_polling_task = asyncio.create_task(
                delivery_dp.start_polling(
                    delivery_bot,
                    handle_signals=False,
                    close_bot_session=False,
                ),
                name="delivery-polling",
            )

            logger.info(
                "Manual delivery bot started"
            )

        logger.info(
            "FastAPI API and Telegram bots started"
        )

        yield

    finally:
        logger.info("Shutting down services...")

        tasks = (
            delivery_polling_task,
            polling_task,
        )

        for task in tasks:
            if task and not task.done():
                task.cancel()

        for task in tasks:
            if task:
                with suppress(asyncio.CancelledError):
                    await task

        if bot and bot.session:
            await bot.session.close()

        if delivery_bot and delivery_bot.session:
            await delivery_bot.session.close()

        logger.info("Shutdown complete")


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Rain Reseller API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


# ============================================================
# REQUEST LOGGING
# ============================================================

@app.middleware("http")
async def request_logger(request: Request, call_next):
    logger.info(
        "%s %s",
        request.method,
        request.url.path,
    )

    try:
        response = await call_next(request)

        logger.info(
            "%s %s -> %s",
            request.method,
            request.url.path,
            response.status_code,
        )

        return response

    except Exception:
        logger.exception(
            "Unhandled request error: %s %s",
            request.method,
            request.url.path,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "Internal server error.",
            },
        )


# ============================================================
# HEALTH
# ============================================================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Rain Reseller API",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "Rain Reseller API",
    }


# ============================================================
# DOCUMENTATION UI
# ============================================================

@app.get("/docs", include_in_schema=False)
async def api_docs_page():
    if not DOCS_FILE.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                "Documentation UI file missing. "
                "Create static/docs/index.html."
            ),
        )

    return FileResponse(
        DOCS_FILE,
        media_type="text/html",
    )


# ============================================================
# RESELLER API
# ============================================================

app.include_router(
    reseller_router,
)


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    logger.info(
        "Starting server on 0.0.0.0:%s",
        PORT,
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
    )
