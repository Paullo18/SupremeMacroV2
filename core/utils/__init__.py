"""
Package initialization for core.utils module.
Exports utility functions and classes.
"""

# Import utilities
from core.utils.thread_utils import (
    schedule_on_main_thread,
    process_main_thread_queue,
    is_main_thread,
    create_thread_safe_lock,
    ensure_main_thread,
    initialize as initialize_thread_utils
)

from core.utils.gui_utils import (
    show_info,
    show_warning,
    show_error,
    ask_question,
    ask_ok_cancel,
    ask_yes_no,
    ask_retry_cancel,
    patch_photo_image_del,
    patch_tkinter_widgets,
    initialize as initialize_gui_utils
)

from core.utils.io_utils import (
    load_json_file,
    save_json_file,
    load_settings,
    get_timestamp_filename,
    ensure_directory,
    clean_directory,
    copy_file,
    move_file
)

from core.utils.logger import (
    setup_logger,
    get_logger,
    get_or_create_logger,
    create_default_loggers,
    initialize as initialize_logger
)

# Export all utilities
__all__ = [
    # Thread utilities
    'schedule_on_main_thread',
    'process_main_thread_queue',
    'is_main_thread',
    'create_thread_safe_lock',
    'ensure_main_thread',
    
    # GUI utilities
    'show_info',
    'show_warning',
    'show_error',
    'ask_question',
    'ask_ok_cancel',
    'ask_yes_no',
    'ask_retry_cancel',
    'patch_photo_image_del',
    'patch_tkinter_widgets',
    
    # IO utilities
    'load_json_file',
    'save_json_file',
    'load_settings',
    'get_timestamp_filename',
    'ensure_directory',
    'clean_directory',
    'copy_file',
    'move_file',
    
    # Logger utilities
    'setup_logger',
    'get_logger',
    'get_or_create_logger',
    'create_default_loggers'
]

# Initialize function
def initialize():
    """
    Initialize all utility modules.
    This should be called once from the main thread during application startup.
    """
    initialize_thread_utils()
    initialize_gui_utils()
    initialize_logger()
