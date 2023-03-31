"""This module implements a specific logging API tuned for Quantum Internet simulations on Netsquid."""

import netsquid as ns
import logging

__all__ = ["log_to_console", "log_to_file", "set_log_level",
           "remove_console_log", "debug", "info", "warning", "error", "critical"]


class ColorFormatter(logging.Formatter):
    """Class used to format log output color depending on its level.

    DEBUG: blue
    INFO: grey
    WARNING: yellow
    ERROR: red
    CRITICAL: bold red

    Parameters
    ----------
    fmt : str, optional
        The text format to apply to the log entry. Defaults to the message alone.
    """

    grey = '\x1b[37m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'

    def __init__(self, fmt="%(message)s"):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.blue + self.fmt + self.reset,
            logging.INFO: self.grey + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


logger = logging.getLogger("QI_Logger")
logger.setLevel(logging.DEBUG)


def log_to_console(level=logging.DEBUG):
    """Activate log output to the stdout console.

    Parameters
    ----------
    level : int, optional
        The logging level for the console. Defaults to logging.DEBUG

    Returns
    -------
    :class:`logging.StreamHandler`
        The handler of the log output.
    """
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(ColorFormatter())
    remove_console_log()  # to avoid double log on console if user calls this function twice
    logger.addHandler(ch)
    return ch


def log_to_file(filename, level=logging.DEBUG):
    """Activate log output to the specified file.

    Parameters
    ----------
    filename : str
        The name of the output log file. If not present it is created. It is opened in append mode.
    level : int, optional
        The logging level on the file. Defaults to `logging.DEBUG`

    Returns
    -------
    logging.FileHandler
        The handler of the log output.
    """
    fh = logging.FileHandler(filename=filename)
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter(''))
    logger.addHandler(fh)
    return fh


def set_log_level(level):
    """Set the log level on all outputs.

    Parameters
    ----------
    level : int
        The new log level.
    """
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


def remove_console_log():
    """Remove the console log handler."""
    h = None
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            h = handler
            break
    if h is not None:
        logger.removeHandler(h)


def debug(message, repeater_id=None, protocol=None, protocol_state=None):
    """Log a message with level DEBUG on the logger.

    Parameters
    ----------
    message : str
        The message to be logged. It should not contain the current simulation time because it is already
        present in the log format.
    repeater_id : int or None optional
        If not None, an additional string is added to the log entry, containing the components.rst identifier.
    protocol : str or None, optional
        If not None, an additional string is added to the log entry, containing the provided protocols name.
    protocol_state : str or None, optional
        If not None, an additional string is added to the log entry, containing the provided protocols state.
    """
    log_message = f"[{ns.sim_time()}]::DEBUG::"
    log_message += _get_additional_info(repeater_id, protocol, protocol_state)
    log_message += (" " + message)
    logger.debug(log_message)


def info(message, repeater_id=None, protocol=None, protocol_state=None):
    """Log a message with level INFO on the logger.

    Parameters
    ----------
    message : str
        The message to be logged. It should not contain the current simulation time because it is already
        present in the log format.
    repeater_id : int or None, optional
        If not None, an additional string is added to the log entry, containing the components.rst identifier.
    protocol : str or None, optional
        If not None, an additional string is added to the log entry, containing the provided protocols name.
    protocol_state : str or None, optional
        If not None, an additional string is added to the log entry, containing the provided protocols state.
    """
    log_message = f"[{ns.sim_time()}]::INFO::"
    log_message += _get_additional_info(repeater_id, protocol, protocol_state)
    log_message += (" " + message)
    logger.info(log_message)


def warning(message, repeater_id=None, protocol=None, protocol_state=None):
    """Log a message with level WARNING on the logger.

    Parameters
    ----------
    message : str
        The message to be logged. It should not contain the current simulation time because it is already
        present in the log format.
    repeater_id : int or None, optional
        If not None, an additional string is added to the log entry, containing the components.rst identifier.
    protocol : str or None, optional
        If not None, an additional string is added to the log entry, containing the provided protocols name.
    protocol_state : str or None, optional
        If not None, an additional string is added to the log entry, containing the provided protocols state.
    """
    log_message = f"[{ns.sim_time()}]::WARNING::"
    log_message += _get_additional_info(repeater_id, protocol, protocol_state)
    log_message += (" " + message)
    logger.warning(log_message)


def error(message, repeater_id=None, protocol=None, protocol_state=None):
    """Log a message with level ERROR on the logger.

    Parameters
    ----------
    message : str
        The message to be logged. It should not contain the current simulation time because it is already
        present in the log format.
    repeater_id : int or None, optional
        If not None, an additional string is added to the log entry, containing the components.rst identifier.
    protocol : str or None, optional
        If not None, an additional string is added to the log entry, containing the provided protocols name.
    protocol_state : str or None, optional
        If not None, an additional string is added to the log entry, containing the provided protocols state.
    """
    log_message = f"[{ns.sim_time()}]::ERROR::"
    log_message += _get_additional_info(repeater_id, protocol, protocol_state)
    log_message += (" " + message)
    logger.error(log_message)


def critical(message, repeater_id=None, protocol=None, protocol_state=None):
    """Log a message with level CRITICAL on the logger.

    Parameters
    ----------
    message : str
        The message to be logged. It should not contain the current simulation time because it is already
        present in the log format.
    repeater_id : int or None, optional
        If not None, an additional string is added to the log entry, containing the components.rst identifier.
    protocol : str or None, optional
        If not None, an additional string is added to the log entry, containing the provided protocols name.
    protocol_state : str or None, optional
        If not None, an additional string is added to the log entry, containing the provided protocols state.
    """
    log_message = f"[{ns.sim_time()}]::CRITICAL_ERROR::"
    log_message += _get_additional_info(repeater_id, protocol, protocol_state)
    log_message += (" " + message)
    logger.critical(log_message)


def _get_additional_info(repeater_id=None, protocol=None, protocol_state=None):
    log_message = ""
    if repeater_id is not None:
        log_message += f"REPEATER-{repeater_id}::"
    if protocol is not None:
        log_message += f"{protocol}::"
    if protocol_state is not None:
        log_message += f"STATE {protocol_state}::"
    return log_message
