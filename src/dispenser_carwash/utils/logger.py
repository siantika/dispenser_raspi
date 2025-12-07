import logging
from typing import Optional


def _configure_root_logger() -> None:
    """
    Configure root logger one time.
    If already configured, skip.
    """
    root = logging.getLogger()

    if root.handlers:
        # Already configured → do nothing
        return

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s [%(processName)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Set minimum log level
    root.setLevel(logging.INFO)


def setup_logger(name: str = "app", queue: Optional[object] = None) -> logging.Logger:
    """
    Create/get logger with standard formatting.
    `queue` argument ignored for backward compatibility.
    """
    # Make sure root logger is configured once
    _configure_root_logger()

    logger = logging.getLogger(name)
    logger.propagate = True  # send to root handler
    return logger
