"""Structured logging setup. Pretty console output in development,
JSON lines otherwise. Configures structlog, doesn't emit any logs
itself, the pipeline logs one line per stage per query, tagged with
the correlation ID, see application/pipeline.py.
"""

import logging

import structlog

from voicerag.config import settings


def configure_logging() -> None:
    renderer = (
        structlog.dev.ConsoleRenderer()
        if settings.environment == "development"
        else structlog.processors.JSONRenderer()
    )
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
