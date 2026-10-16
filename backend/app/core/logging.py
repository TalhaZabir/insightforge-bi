"""Structured logging setup."""

import logging
import sys

import structlog


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(stream=sys.stdout, level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
    )


def get_logger(name: str = "insightforge"):
    return structlog.get_logger(name)
