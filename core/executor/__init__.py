#core/executor/__init__.py

"""
Package initialization for core.executor module.
Exports main execution functions and classes.
"""

from core.executor.macro_executor import (
    execute_macro,
    load_macro_flow,
    start_keyboard_monitor,
    get_active_thread_count,
    is_macro_running,
    stop_all_macros,
    toggle_pause
)

from core.executor.context import ExecContext
#from core.executor.action_handlers import handle_action

__all__ = [
    'execute_macro',
    'load_macro_flow',
    'start_keyboard_monitor',
    'get_active_thread_count',
    'is_macro_running',
    'stop_all_macros',
    'toggle_pause',
    'ExecContext'
]
