"""
IO utilities for Supreme Macro.
Provides file operations, JSON handling, and settings management.
"""

import os
import json
import shutil
from datetime import datetime
from core.utils.gui_utils import show_error, show_info

def load_json_file(file_path, default=None):
    """
    Load a JSON file safely.
    
    Args:
        file_path: Path to the JSON file
        default: Default value to return if file doesn't exist or is invalid
        
    Returns:
        The loaded JSON data or the default value
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading JSON file {file_path}: {e}")
        return default if default is not None else {}

def save_json_file(file_path, data, ensure_dir=True, indent=2):
    """
    Save data to a JSON file.
    
    Args:
        file_path: Path to save the JSON file
        data: Data to save
        ensure_dir: Whether to create the directory if it doesn't exist
        indent: Indentation level for the JSON file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if ensure_dir:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        return True
    except Exception as e:
        print(f"Error saving JSON file {file_path}: {e}")
        return False

def load_settings(settings_path, default=None):
    """
    Load application settings from a JSON file.
    
    Args:
        settings_path: Path to the settings file
        default: Default settings to use if file doesn't exist
        
    Returns:
        The loaded settings or default settings
    """
    return load_json_file(settings_path, default)

def get_timestamp_filename(prefix, extension):
    """
    Generate a filename with a timestamp.
    
    Args:
        prefix: Prefix for the filename
        extension: File extension (without the dot)
        
    Returns:
        A filename in the format prefix_YYYYMMDD_HHMMSS.extension
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.{extension}"

def ensure_directory(directory):
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Path to the directory
        
    Returns:
        True if the directory exists or was created, False otherwise
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {directory}: {e}")
        return False

def clean_directory(directory, file_extensions=None):
    """
    Clean a directory by removing all files or files with specific extensions.
    
    Args:
        directory: Path to the directory to clean
        file_extensions: List of file extensions to remove (without the dot),
                         or None to remove all files
        
    Returns:
        Number of files removed
    """
    if not os.path.isdir(directory):
        return 0
    
    count = 0
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        
        if os.path.isfile(file_path):
            if file_extensions is None or any(filename.lower().endswith(f".{ext.lower()}") for ext in file_extensions):
                try:
                    os.remove(file_path)
                    count += 1
                except Exception as e:
                    print(f"Error removing file {file_path}: {e}")
        elif os.path.isdir(file_path):
            try:
                shutil.rmtree(file_path, ignore_errors=True)
                count += 1
            except Exception as e:
                print(f"Error removing directory {file_path}: {e}")
    
    return count

def copy_file(source, destination, ensure_dest_dir=True):
    """
    Copy a file from source to destination.
    
    Args:
        source: Source file path
        destination: Destination file path
        ensure_dest_dir: Whether to create the destination directory if it doesn't exist
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if ensure_dest_dir:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        shutil.copy2(source, destination)
        return True
    except Exception as e:
        print(f"Error copying file from {source} to {destination}: {e}")
        return False

def move_file(source, destination, ensure_dest_dir=True):
    """
    Move a file from source to destination.
    
    Args:
        source: Source file path
        destination: Destination file path
        ensure_dest_dir: Whether to create the destination directory if it doesn't exist
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if ensure_dest_dir:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        shutil.move(source, destination)
        return True
    except Exception as e:
        print(f"Error moving file from {source} to {destination}: {e}")
        return False
