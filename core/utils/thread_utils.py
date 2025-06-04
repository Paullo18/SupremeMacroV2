"""
Thread utilities for Supreme Macro.
Provides thread-safe operations and utilities for managing threads.
"""

import threading
import tkinter as tk
from queue import Queue, Empty
import traceback
import sys

# Global queue for UI operations
_ui_queue = Queue()

def schedule_on_main_thread(callback, *args, **kwargs):
    """
    Agenda uma função para rodar no main-thread.
    Se o objeto recebido não for chamável, apenas avisa
    (evita TypeError no process_main_thread_queue) e exibe
    o stack-trace para localizar o erro original.
    """
    if callback is None:
        return

    if not callable(callback):
        print(f"[thread_utils] Warning: objeto não-callable passado para "
              f"schedule_on_main_thread: {type(callback).__name__}")
        import traceback
        traceback.print_stack()
        return

    _ui_queue.put((callback, args, kwargs))

def process_main_thread_queue():
    """
    Process all pending UI operations from the queue.
    This function should be called periodically from the main thread.
    """
    try:
        while not _ui_queue.empty():
            callback, args, kwargs = _ui_queue.get_nowait()
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"Error in UI callback: {e}")
                traceback.print_exc()
    except Empty:
        pass
    except Exception as e:
        print(f"Error processing UI queue: {e}")
        traceback.print_exc()
    
    # Schedule the next check
    if tk._default_root is not None:
        tk._default_root.after(30, process_main_thread_queue)

def is_main_thread():
    """Check if the current thread is the main thread."""
    return threading.current_thread() is threading.main_thread()

def create_thread_safe_lock():
    """Create and return a new thread lock."""
    return threading.Lock()

def install_exception_hook():
    """
    Install a custom exception hook to catch and log threading errors.
    """
    original_hook = sys.excepthook
    
    def exception_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, RuntimeError) and "main thread is not in main loop" in str(exc_value):
            print("=" * 80)
            print("Caught RuntimeError: main thread is not in main loop")
            print("This error occurs when a GUI operation is attempted from a non-main thread.")
            print("Stack trace:")
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            print("=" * 80)
        
        # Call the original exception hook
        original_hook(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = exception_hook

def ensure_main_thread(func):
    """
    Decorator to ensure a function is called on the main thread.
    
    If the function is called from a non-main thread, it will be
    scheduled to run on the main thread instead.
    
    Args:
        func: The function to be wrapped
        
    Returns:
        A wrapped function that ensures execution on the main thread
    """
    def wrapper(*args, **kwargs):
        if is_main_thread():
            return func(*args, **kwargs)
        else:
            # Schedule the function to be called on the main thread
            schedule_on_main_thread(func, *args, **kwargs)
    return wrapper

# Initialize the thread utilities
def initialize():
    """
    Initialize the thread utilities.
    This should be called once from the main thread during application startup.
    """
    install_exception_hook()
    if tk._default_root is not None:
        tk._default_root.after(30, process_main_thread_queue)
