"""
Logging system for Supreme Macro.
Provides a centralized logging system with configurable levels and outputs.
"""

import logging
import os
import sys
from datetime import datetime

# Default log directory
DEFAULT_LOG_DIR = "logs"

# Log levels
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# Global logger instances
_loggers = {}

def setup_logger(name, level="INFO", log_file=None, console=True, format_str=None):
    """
    Set up a logger with the specified configuration.
    
    Args:
        name: Name of the logger
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to the log file, or None for no file logging
        console: Whether to log to console
        format_str: Custom format string for log messages
        
    Returns:
        The configured logger
    """
    if name in _loggers:
        return _loggers[name]
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Set level
    level = LOG_LEVELS.get(level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Create formatter
    if format_str is None:
        format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(format_str)
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add file handler if requested
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Store logger
    _loggers[name] = logger
    
    return logger

def get_logger(name):
    """
    Get an existing logger by name.
    
    Args:
        name: Name of the logger
        
    Returns:
        The logger, or None if it doesn't exist
    """
    return _loggers.get(name)

def get_or_create_logger(name, **kwargs):
    """
    Get an existing logger or create a new one if it doesn't exist.
    
    Args:
        name: Name of the logger
        **kwargs: Additional arguments to pass to setup_logger if creating a new logger
        
    Returns:
        The logger
    """
    logger = get_logger(name)
    if logger is None:
        logger = setup_logger(name, **kwargs)
    return logger

def create_default_loggers(base_dir=None):
    """
    Create the default set of loggers for the application.
    
    Args:
        base_dir: Base directory for log files, or None to use the default
        
    Returns:
        Dictionary of created loggers
    """
    if base_dir is None:
        base_dir = DEFAULT_LOG_DIR
    
    # Ensure log directory exists
    os.makedirs(base_dir, exist_ok=True)
    
    # Create timestamp for log files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create loggers
    loggers = {
        "main": setup_logger(
            "main", 
            level="INFO",
            log_file=os.path.join(base_dir, f"main_{timestamp}.log"),
            console=True
        ),
        "executor": setup_logger(
            "executor", 
            level="INFO",
            log_file=os.path.join(base_dir, f"executor_{timestamp}.log"),
            console=True
        ),
        "gui": setup_logger(
            "gui", 
            level="INFO",
            log_file=os.path.join(base_dir, f"gui_{timestamp}.log"),
            console=True
        ),
        "error": setup_logger(
            "error", 
            level="ERROR",
            log_file=os.path.join(base_dir, f"error_{timestamp}.log"),
            console=True,
            format_str='%(asctime)s - %(levelname)s - %(message)s\n%(pathname)s:%(lineno)d\n'
        )
    }
    
    return loggers

# Initialize the logging system
def initialize(base_dir=None):
    """
    Initialize the logging system.
    
    Args:
        base_dir: Base directory for log files, or None to use the default
        
    Returns:
        Dictionary of created loggers
    """
    return create_default_loggers(base_dir)
