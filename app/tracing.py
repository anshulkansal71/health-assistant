"""Arize tracing bootstrap.

Call `setup_tracing(app)` once at startup — **before** any LangChain or
OpenAI objects are created — so that every downstream call is captured.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


def setup_tracing(app=None):
    """Register the Arize OTel tracer and auto-instrument LangChain + FastAPI.

    Silently no-ops when ``ARIZE_API_KEY`` or ``ARIZE_SPACE_ID`` are not
    configured, so the app still starts in local dev without credentials.
    """
    if not settings.ARIZE_API_KEY or not settings.ARIZE_SPACE_ID:
        logger.info("Arize tracing disabled (ARIZE_API_KEY or ARIZE_SPACE_ID not set)")
        return

    try:
        from arize.otel import register
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        tracer_provider = register(
            space_id=settings.ARIZE_SPACE_ID,
            api_key=settings.ARIZE_API_KEY,
            project_name=settings.ARIZE_PROJECT_NAME,
            endpoint=settings.ARIZE_COLLECTOR_ENDPOINT,
        )

        # Instrument LangChain so all chain / LLM invocations emit spans.
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

        # Instrument FastAPI so every HTTP request is captured as a parent span.
        if app is not None:
            FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

        logger.info(
            "Arize tracing enabled (project=%s, endpoint=%s)",
            settings.ARIZE_PROJECT_NAME,
            settings.ARIZE_COLLECTOR_ENDPOINT,
        )
    except Exception:
        logger.exception("Failed to initialise Arize tracing — continuing without it")
