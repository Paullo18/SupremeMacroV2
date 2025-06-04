"""
Main executar.py replacement for Supreme Macro.
This file serves as a drop-in replacement for the original executar.py,
providing backward compatibility while using the new modular architecture.
"""

# Import from the new modular architecture
from core import (
    execute_macro,
    load_macro_flow,
    start_keyboard_monitor,
    get_active_thread_count,
    is_macro_running,
    stop_all_macros,
    toggle_pause,
    process_main_thread_queue,
    schedule_on_main_thread,
    initialize
)

# Initialize the core module
initialize()

# For backward compatibility
def _ui_async(callback, *args, **kwargs):
    """Legacy function for backward compatibility"""
    return schedule_on_main_thread(callback, *args, **kwargs)

# Export the main functions for backward compatibility
__all__ = [
    'execute_macro',
    'load_macro_flow',
    'process_ui_queue',
    '_ui_async',
    'start_keyboard_monitor',
    'get_active_thread_count',
    'is_macro_running',
    'stop_all_macros',
    'toggle_pause'
]

# Alias for backward compatibility
process_ui_queue = process_main_thread_queue

# Start keyboard monitor
keyboard_monitor_thread = start_keyboard_monitor()
