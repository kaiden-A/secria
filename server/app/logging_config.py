import logging

import structlog


def configure_logging(level: str = "INFO", environment: str = "development") -> None:
    """Configure structlog once at process start.

    Development gets a readable console renderer; production gets JSON so log
    aggregation can parse it. Never log secret values, tokens, or plaintext.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", level=numeric_level)

    renderer = (
        structlog.processors.JSONRenderer()
        if environment.lower() == "production"
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
