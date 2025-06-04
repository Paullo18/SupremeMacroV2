"""
GUI utilities for Supreme Macro.
Provides thread-safe GUI operations and utilities.
"""

import tkinter as tk
from tkinter import messagebox
from PIL import ImageTk
from core.utils.thread_utils import ensure_main_thread, is_main_thread, schedule_on_main_thread

# Preserve os métodos originais antes de sobrescrever
_ORIG_SHOWINFO = messagebox.showinfo
_ORIG_SHOWWARNING = messagebox.showwarning
_ORIG_SHOWERROR = messagebox.showerror
_ORIG_ASKQUESTION = messagebox.askquestion
_ORIG_ASKOKCANCEL = messagebox.askokcancel
_ORIG_ASKYESNO = messagebox.askyesno
_ORIG_ASKRETRYCANCEL = messagebox.askretrycancel

# Create thread-safe versions of messagebox functions
@ensure_main_thread
def show_info(title, message, **kwargs):
    """Show an info messagebox in a thread-safe manner."""
    return _ORIG_SHOWINFO(title, message, **kwargs)

@ensure_main_thread
def show_warning(title, message, **kwargs):
    """Show a warning messagebox in a thread-safe manner."""
    return _ORIG_SHOWWARNING(title, message, **kwargs)

@ensure_main_thread
def show_error(title, message, **kwargs):
    """Show an error messagebox in a thread-safe manner."""
    return _ORIG_SHOWERROR(title, message, **kwargs)

@ensure_main_thread
def ask_question(title, message, **kwargs):
    """Show a question messagebox in a thread-safe manner."""
    return _ORIG_ASKQUESTION(title, message, **kwargs)

@ensure_main_thread
def ask_ok_cancel(title, message, **kwargs):
    """Show an ok/cancel messagebox in a thread-safe manner."""
    return _ORIG_ASKOKCANCEL(title, message, **kwargs)

@ensure_main_thread
def ask_yes_no(title, message, **kwargs):
    """Show a yes/no messagebox in a thread-safe manner."""
    return _ORIG_ASKYESNO(title, message, **kwargs)

@ensure_main_thread
def ask_retry_cancel(title, message, **kwargs):
    """Show a retry/cancel messagebox in a thread-safe manner."""
    return _ORIG_ASKRETRYCANCEL(title, message, **kwargs)

def patch_photo_image_del():
    """
    Patch PIL.ImageTk.PhotoImage.__del__ and tk.PhotoImage.__del__ to be thread-safe.
    This ensures that image destruction always happens on the main thread.
    """
    # Store the original __del__ methods if not already stored
    if not hasattr(ImageTk.PhotoImage, '_original_del'):
        ImageTk.PhotoImage._original_del = ImageTk.PhotoImage.__del__
    
    if not hasattr(tk.PhotoImage, '_original_del'):
        tk.PhotoImage._original_del = tk.PhotoImage.__del__
    
    # Define thread-safe __del__ methods
    def safe_pil_del(self):
        if is_main_thread():
            ImageTk.PhotoImage._original_del(self)
        else:
            schedule_on_main_thread(ImageTk.PhotoImage._original_del, self)
    
    def safe_tk_del(self):
        if is_main_thread():
            tk.PhotoImage._original_del(self)
        else:
            schedule_on_main_thread(tk.PhotoImage._original_del, self)
    
    # Apply the patches
    ImageTk.PhotoImage.__del__ = safe_pil_del
    tk.PhotoImage.__del__ = safe_tk_del

def patch_tkinter_widgets():
    """
    Patch all Tkinter widget methods to ensure they're called on the main thread.
    This is a comprehensive approach that catches all widget operations.
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
    exclude_methods = ['__init__', '__del__', '__getattr__', '__setattr__', '__str__', '__repr__']
    
    for widget_class in widget_classes:
        for method_name in dir(widget_class):
            if method_name.startswith('__') or method_name in exclude_methods:
                continue
                
            method = getattr(widget_class, method_name)
            if callable(method) and not isinstance(method, type):
                # Create a thread-safe wrapper for this method
                def create_safe_method(original_method, method_name, widget_class_name):
                    @ensure_main_thread
                    def safe_method(self, *args, **kwargs):
                        return original_method(self, *args, **kwargs)
                    return safe_method
                
                # Only patch instance methods, not class methods or static methods
                if not isinstance(method, (classmethod, staticmethod)):
                    try:
                        setattr(widget_class, method_name, 
                                create_safe_method(method, method_name, widget_class.__name__))
                    except (AttributeError, TypeError):
                        # Skip methods that can't be replaced
                        pass

# Apply all GUI-related patches
def initialize():
    """
    Initialize all GUI utilities and apply patches.
    This should be called once from the main thread during application startup.
    """
    patch_photo_image_del()
    # Uncomment the line below for comprehensive widget patching (may impact performance)
    # patch_tkinter_widgets()
    
    # Replace standard messagebox functions with thread-safe versions
    messagebox.showinfo = show_info
    messagebox.showwarning = show_warning
    messagebox.showerror = show_error
    messagebox.askquestion = ask_question
    messagebox.askokcancel = ask_ok_cancel
    messagebox.askyesno = ask_yes_no
    messagebox.askretrycancel = ask_retry_cancel
