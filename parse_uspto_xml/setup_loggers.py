from __future__ import annotations

import os
import sys
import logging
from pathlib import Path


_logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")


def create_file_handler(log_name):
    """creates a file logger"""
    log_dirpath = os.getcwd()
    log_filepath = os.path.join(
        log_dirpath,  "logs", os.path.basename(log_name) + ".log"
    )
    Path(os.path.dirname(log_filepath)).mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(filename=log_filepath)
    file_handler.setFormatter(_logFormatter)
    return file_handler


def setup_root_logger(level: int = logging.INFO, include_file_logger: bool = False):
    """Sets up root logger to use console."""
    root_logger = logging.getLogger()

    # don't setup root again if already setup.
    for handler in root_logger.handlers:
        if handler.stream == sys.stdout:
            return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_logFormatter)
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    if include_file_logger:
        file_handler = create_file_handler("main")
        root_logger.addHandler(file_handler)


def set_root_logger_level(level: int = logging.INFO):
    """Sets the level for the root logger."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)


def setup_file_logger(filename: str, level: int | None = None) -> logging.Logger:
    """Sets up file logger for an individual file."""
    level = logging.getLogger().level

    file_handler = create_file_handler(filename)
    logger = logging.getLogger(filename)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    return logger
