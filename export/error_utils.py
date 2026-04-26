"""Error reporting"""
import logging

logger = logging.getLogger(__name__)


def _print_export_failure(message, exception):
    logger.exception("%s: %s", message, exception)
