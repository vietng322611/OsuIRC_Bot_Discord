import os
import logging
import logging.handlers

from sys import stdout
from os import path
from datetime import datetime

RED   = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
BLUE  = "\033[0;34m"
MAGENTA = "\033[0;95m"
CYAN  = "\033[0;96m"
BOLD_RED = "\x1b[31;1m"
RESET = "\033[0;0m"
custom_format = "[{asctime}] [{levelname:<8}] {name}: {message}"
datefmt = '%Y-%m-%d %H:%M:%S'

FORMATS = {
    logging.DEBUG   : MAGENTA + custom_format + RESET,
    logging.INFO    : GREEN + custom_format + RESET,
    logging.WARNING : YELLOW + custom_format + RESET,
    logging.ERROR   : RED + custom_format + RESET,
    logging.CRITICAL: BOLD_RED + custom_format + RESET
}

LOGGERS = {
    'root'       : logging.DEBUG,
    'discord'    : logging.INFO,
    'asyncio'    : logging.INFO,
    'OsuSocket'  : logging.DEBUG,
    'IrcManager' : logging.DEBUG,
}

class CustomFormatterFile(logging.Formatter):
    def format(self, record):
        log_fmt = custom_format
        formatter = logging.Formatter(
            log_fmt,
            datefmt,
            style="{"
        )
        return formatter.format(record)

class CustomFormatterConsole(logging.Formatter):
    def format(self, record):
        log_fmt = FORMATS.get(record.levelno)
        formatter = logging.Formatter(
            log_fmt,
            datefmt,
            style="{"
        )
        return formatter.format(record)
    
def optimize_folder(max_files: int):
    if not os.path.exists("./logs"): return
    files = [f for f in os.listdir("./logs") if os.path.isfile(os.path.join("./logs", f))]
    files.sort(reverse=True)
    cnt = len(files)
    while cnt > max_files:
        cnt -= 1
        os.remove(os.path.join("./logs", files[cnt]))

optimize_folder(10)

filename = path.join("./logs", datetime.today().strftime("%Y-%m-%d@%H.%M.%S") + ".log")

file_handler = logging.handlers.RotatingFileHandler(
    filename = filename,
    mode = "w",
    encoding = "utf-8",
    maxBytes = 32 * 1024 * 1024,  # 32 MiB
    backupCount = 5,  # Rotate through 5 files
)
stdout_handler = logging.StreamHandler(stdout)

file_handler.setFormatter(CustomFormatterFile())
stdout_handler.setFormatter(CustomFormatterConsole())

for name, level in LOGGERS.items():
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)
    logger.propagate = False