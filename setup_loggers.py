import os
import sys
import logging


logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")


def setup_root_logger(level: int = logging.INFO):
    root_logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logFormatter)
    root_logger.setLevel(level)
    root_logger.addHandler(handler)


def setup_file_logger(filename: str, level: int = logging.INFO) -> logging.Logger:
    log_dirpath = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "logs",
        os.path.basename(filename) + ".log"
    )
    logger = logging.getLogger(filename)
    file_handler = logging.FileHandler(filename=log_dirpath)
    file_handler.setFormatter(logFormatter)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    return logger
