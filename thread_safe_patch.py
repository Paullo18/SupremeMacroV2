"""
Enhanced thread-safe wrapper for GUI operations in Supreme Macro.
This module ensures all GUI operations are performed on the main thread.
"""

import threading
import tkinter as tk
from tkinter import messagebox
from queue import Queue, Empty
import traceback
import sys

# Global queue for UI operations
_ui_queue = Queue()

def _ui_async(callback, *args, **kwargs):
    """
    Schedule a callback to be executed on the main thread.
    
    Args:
        callback: The function to be called on the main thread
        *args: Positional arguments to pass to the callback
        **kwargs: Keyword arguments to pass to the callback
    """
    if callback is not None:
        _ui_queue.put((callback, args, kwargs))

def process_ui_queue():
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
        tk._default_root.after(30, process_ui_queue)

# Create thread-safe versions of messagebox functions
def safe_messagebox(original_func):
    def wrapper(*args, **kwargs):
        if threading.current_thread() is threading.main_thread():
            return original_func(*args, **kwargs)
        else:
            # We're not in the main thread, so schedule it
            print(f"Thread-safe wrapper: Routing messagebox call to main thread from {threading.current_thread().name}")
            _ui_async(original_func, *args, **kwargs)
    return wrapper

# Patch PIL.ImageTk.PhotoImage.__del__ to be thread-safe
def patch_photo_image_del():
    from PIL import ImageTk
    
    # Store the original __del__ method
    if not hasattr(ImageTk.PhotoImage, '_original_del'):
        ImageTk.PhotoImage._original_del = ImageTk.PhotoImage.__del__
    
    def safe_del(self):
        if threading.current_thread() is threading.main_thread():
            # We're in the main thread, call original directly
            ImageTk.PhotoImage._original_del(self)
        else:
            # Schedule deletion on main thread
            print(f"Thread-safe wrapper: Routing PhotoImage.__del__ to main thread from {threading.current_thread().name}")
            _ui_async(ImageTk.PhotoImage._original_del, self)
    
    # Replace the __del__ method
    ImageTk.PhotoImage.__del__ = safe_del
    
    # Also patch tkinter.PhotoImage
    if not hasattr(tk.PhotoImage, '_original_del'):
        tk.PhotoImage._original_del = tk.PhotoImage.__del__
    
    def safe_tk_del(self):
        if threading.current_thread() is threading.main_thread():
            tk.PhotoImage._original_del(self)
        else:
            print(f"Thread-safe wrapper: Routing tk.PhotoImage.__del__ to main thread from {threading.current_thread().name}")
            _ui_async(tk.PhotoImage._original_del, self)
    
    tk.PhotoImage.__del__ = safe_tk_del

# Patch all Tkinter widget methods to be thread-safe
def patch_tkinter_widgets():
    """
    Patch all Tkinter widget methods to ensure they're called on the main thread.
    This is a more comprehensive approach that catches all widget operations.
    """
    # Get all widget classes from tkinter
    widget_classes = [getattr(tk, name) for name in dir(tk) 
                     if isinstance(getattr(tk, name), type) 
                     and issubclass(getattr(tk, name), tk.Widget)]
    
    # Add Toplevel, which is not a subclass of Widget
    widget_classes.append(tk.Toplevel)
    
    # Add Canvas, which is a special case
    widget_classes.append(tk.Canvas)
    
    # Methods to exclude from patching (methods that are safe to call from any thread)
    exclude_methods = {
        "__init__", "__class__", "__repr__", "__eq__", "__ne__", "__lt__", "__gt__",
        # Não envolver essas rotinas de controle de thread‐utils:
        "is_main_thread", "schedule_on_main_thread", "process_main_thread_queue",
        # Métodos de messagebox – assim evitamos recursão infinita:
        "showinfo", "showwarning", "showerror", "askquestion", "askyesno", "askokcancel"
    }
    
    for widget_class in widget_classes:
        for method_name in dir(widget_class):
            if method_name.startswith('__') or method_name in exclude_methods:
                continue
                
            method = getattr(widget_class, method_name)
            if callable(method) and not isinstance(method, type):
                # Create a thread-safe wrapper for this method
                def create_safe_method(original_method, method_name, widget_class_name):
                    def safe_method(self, *args, **kwargs):
                        if threading.current_thread() is threading.main_thread():
                            return original_method(self, *args, **kwargs)
                        else:
                            # Schedule the method call on the main thread
                            print(f"Thread-safe wrapper: Routing {widget_class_name}.{method_name} to main thread from {threading.current_thread().name}")
                            result = []
                            def main_thread_call():
                                try:
                                    ret = original_method(self, *args, **kwargs)
                                    result.append(ret)
                                except Exception as e:
                                    print(f"Error in {widget_class_name}.{method_name}: {e}")
                                    traceback.print_exc()
                            
                            _ui_async(main_thread_call)
                            # Note: This returns None immediately, as we can't wait for the result
                            # For methods that need to return values, a different approach is needed
                            return None
                    return safe_method
                
                # Only patch instance methods, not class methods or static methods
                if not isinstance(method, (classmethod, staticmethod)):
                    try:
                        setattr(widget_class, method_name, 
                                create_safe_method(method, method_name, widget_class.__name__))
                    except (AttributeError, TypeError):
                        # Skip methods that can't be replaced
                        pass

# Install exception hook to catch and log unhandled exceptions
def install_exception_hook():
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

# Apply all patches
def apply_thread_safety_patches():
    """Apply all thread-safety patches to the application"""
    # Install exception hook to catch and log unhandled exceptions
    install_exception_hook()
    
    # Patch messagebox functions
    messagebox.showinfo = safe_messagebox(messagebox.showinfo)
    messagebox.showwarning = safe_messagebox(messagebox.showwarning)
    messagebox.showerror = safe_messagebox(messagebox.showerror)
    messagebox.askquestion = safe_messagebox(messagebox.askquestion)
    messagebox.askokcancel = safe_messagebox(messagebox.askokcancel)
    messagebox.askyesno = safe_messagebox(messagebox.askyesno)
    messagebox.askretrycancel = safe_messagebox(messagebox.askretrycancel)
    
    # Patch PhotoImage.__del__
    patch_photo_image_del()
    
    # Patch all Tkinter widget methods
    patch_tkinter_widgets()
    
    # Start UI queue processing
    if tk._default_root is not None:
        tk._default_root.after(30, process_ui_queue)
    
    print("Thread safety patches applied successfully")
    return True
