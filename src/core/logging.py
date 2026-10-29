import logging
import sys

from src.core.config import settings


def setup_logging() -> logging.Logger:
    """Configure application-wide structured stdout logging."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("express_delivery")


logger = setup_logging()
