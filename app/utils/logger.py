import logging
import structlog
from app.config import settings


def _get_level() -> int:
    return getattr(logging, settings.log_level.upper(), logging.INFO)


def setup_logging() -> None:
    shared_processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.log_format == "pretty":
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (APScheduler, uvicorn) through structlog
    handler = logging.StreamHandler()
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    ))

    logging.basicConfig(
        handlers=[handler],
        level=_get_level(),
    )
    logging.getLogger("apscheduler").setLevel(_get_level())
    logging.getLogger("uvicorn.access").setLevel(_get_level())
    logging.getLogger("uvicorn.error").setLevel(_get_level())


setup_logging()
logger = structlog.get_logger()
