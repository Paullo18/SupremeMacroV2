#core/__init__.py

"""
Core module initialization for Supreme Macro.
Exports main functionality and initializes the system.
"""

# Import from executor module
from core.executor import (
    execute_macro,
    load_macro_flow,
    start_keyboard_monitor,
    get_active_thread_count,
    is_macro_running,
    stop_all_macros,
    toggle_pause,
    ExecContext
)

# Import from utils module
from core.utils import (
    schedule_on_main_thread,
    process_main_thread_queue,
    is_main_thread,
    ensure_main_thread,
    show_info,
    show_warning,
    show_error,
    ask_question,
    ask_ok_cancel,
    ask_yes_no,
    ask_retry_cancel,
    initialize as initialize_utils
)

# Export all functionality
__all__ = [
    # Executor functions
    'execute_macro',
    'load_macro_flow',
    'start_keyboard_monitor',
    'get_active_thread_count',
    'is_macro_running',
    'stop_all_macros',
    'toggle_pause',
    'ExecContext'
    
    # Utility functions
    'schedule_on_main_thread',
    'process_main_thread_queue',
    'is_main_thread',
    'ensure_main_thread',
    'show_info',
    'show_warning',
    'show_error',
    'ask_question',
    'ask_ok_cancel',
    'ask_yes_no',
    'ask_retry_cancel'
]

# Initialize function
def initialize():
    """
    Initialize the core module.
    This should be called once from the main thread during application startup.
    """
    # Initialize utilities first
    initialize_utils()
    
    # Start keyboard monitor
    start_keyboard_monitor()
    
    return True
