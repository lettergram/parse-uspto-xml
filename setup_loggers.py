import os
import sys
import logging
from pathlib import Path


logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")


def setup_root_logger(level: int = logging.INFO):
    root_logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logFormatter)
    root_logger.setLevel(level)
    root_logger.addHandler(handler)


def setup_file_logger(filename: str, level: int = logging.INFO) -> logging.Logger:
    log_dirpath = os.path.dirname(os.path.abspath(__file__))
    Path(log_dirpath).mkdir(parents=True, exist_ok=True)

    log_filepath = os.path.join(
        log_dirpath,  "logs", os.path.basename(filename) + ".log"
    )
    logger = logging.getLogger(filename)
    file_handler = logging.FileHandler(filename=log_filepath)
    file_handler.setFormatter(logFormatter)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    return logger
