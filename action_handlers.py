"""
Action handlers for Supreme Macro.
Provides handlers for different action types in macro execution.
"""

import time
import threading
import os
import random
import unicodedata
import json
import shutil
from datetime import datetime
import traceback
from PIL import ImageGrab, Image
import pytesseract
import pyautogui
from pyautogui import ImageNotFoundException
import keyboard
import win32clipboard

from core.utils.logger import get_or_create_logger
from core.utils.thread_utils import is_main_thread, schedule_on_main_thread

# Get logger
logger = get_or_create_logger("action_handlers")

# Global locks for resource access
_grab_lock = threading.Lock()  # for ImageGrab / screenshot
_tess_lock = threading.Lock()  # for pytesseract
_clipboard_lock = threading.Lock()  # for clipboard operations
_io_lock = threading.Lock()  # for file operations

def handle_action(action_type, params, context):
    """
    Dispatch to the appropriate action handler based on action type.
    
    Args:
        action_type: Type of action to handle
        params: Action parameters
        context: Execution context
        
    Returns:
        Next block ID or None
    """
    # Convert action type to lowercase for case-insensitive matching
    action_type = action_type.lower()
    
    # Map action types to handler functions
    handlers = {
        "click": handle_click,
        "delay": handle_delay,
        "goto": handle_goto,
        "imagem": handle_image,
        "label": handle_label,
        "loopstart": handle_loop_start,
        "loopend": handle_loop_end,
        "ocr": handle_ocr,
        "ocr_duplo": handle_ocr_duplo,
        "text": handle_text,
        "startthread": handle_start_thread,
        "endthread": handle_end_thread,
        "screenshot": handle_screenshot,
        "telegram_command": handle_telegram_command,
        "run_macro": handle_run_macro,
        "hotkey": handle_hotkey,
        "text_to_sheet": handle_text_to_sheet
    }
    
    # Get the handler function
    handler = handlers.get(action_type)
    
    if handler is None:
        logger.warning(f"Unknown action type: {action_type}")
        return get_next_block(context, current_id=context.get("current_id"))
    
    # Call the handler function
    return handler(params, context)

def get_next_block(context, current_id=None, branch=None):
    """
    Get the next block ID based on the current block and branch.
    
    Args:
        context: Execution context
        current_id: Current block ID (defaults to context["current_id"])
        branch: Branch to follow (None for default, "true", or "false")
        
    Returns:
        Next block ID or None
    """
    if current_id is None:
        current_id = context.get("current_id")
    
    next_map = context.get("next_map", {})
    if current_id not in next_map:
        return None
    
    # Get the appropriate branch
    if branch is None:
        nexts = next_map[current_id].get("default", [])
    else:
        nexts = next_map[current_id].get(branch, [])
    
    # Return the first next block or None
    return nexts[0] if nexts else None

# Individual action handlers

def handle_click(params, context):
    """Handle click action."""
    logger.debug(f"Handling click action: {params}")
    
    # Remove accents and convert to lowercase
    raw_mode = params.get("mode", "fixo")
    mode = unicodedata.normalize("NFD", raw_mode).encode("ascii", "ignore").decode().lower()
    btn = params.get("btn", "left")
    
    try:
        if mode == "aleatorio":
            x = random.randint(params["x"], params["x"] + params["w"] - 1)
            y = random.randint(params["y"], params["y"] + params["h"] - 1)
        elif mode == "imagem":
            # Locate template within defined region
            template = params.get("template_path")
            region = (params["x"], params["y"], params["w"], params["h"])
            try:
                loc = pyautogui.locateOnScreen(template, region=region, confidence=0.8)
            except ImageNotFoundException:
                # Image not found, silently abort
                logger.warning(f"Image not found for click: {template}")
                return get_next_block(context)
            
            # If locateOnScreen returns None, also abort
            if not loc:
                logger.warning(f"Image not found for click: {template}")
                return get_next_block(context)
            
            # Calculate center of found area
            x = loc.left + loc.width // 2
            y = loc.top + loc.height // 2
        else:
            x, y = params["x"], params["y"]
        
        # Move mouse to desired coordinates
        pyautogui.moveTo(x, y)
        # Wait 50ms to ensure movement is complete
        time.sleep(0.05)
        # Then trigger the click
        pyautogui.click(x, y, button=btn)
        logger.info(f"Clicked at coordinates: ({x}, {y}) with button: {btn}")
    except Exception as e:
        logger.error(f"Error in click action: {e}")
        logger.error(traceback.format_exc())
    
    return get_next_block(context)

def handle_delay(params, context):
    """Handle delay action."""
    delay_ms = params.get("time", 0)
    delay_sec = delay_ms / 1000.0
    
    logger.debug(f"Handling delay action: {delay_sec} seconds")
    
    # Get the stop event from context
    stop_event = context.get("stop_event")
    
    # If delay is very short, just sleep
    if delay_sec <= 0.1 or stop_event is None:
        time.sleep(delay_sec)
        return get_next_block(context)
    
    # For longer delays, use interruptible sleep
    step = 0.1
    remaining = delay_sec
    
    while remaining > 0 and not stop_event.is_set():
        time.sleep(min(step, remaining))
        remaining -= step
    
    return get_next_block(context)

def handle_goto(params, context):
    """Handle goto action."""
    target_label = params.get("label")
    logger.debug(f"Handling goto action to label: {target_label}")
    
    # Find the block with the matching label
    blocks = context.get("blocks", {})
    
    for block_id, block in blocks.items():
        block_params = block.get("params", {})
        if block_params.get("type") == "label" and block_params.get("name") == target_label:
            logger.info(f"Found label '{target_label}', jumping to block {block_id}")
            return block_id
    
    logger.warning(f"Label not found: {target_label}")
    return get_next_block(context)

def handle_image(params, context):
    """Handle image action."""
    logger.debug(f"Handling image action: {params}")
    
    # Get image path
    image_path = params.get("imagem")
    if not image_path:
        logger.warning("No image path provided")
        return get_next_block(context)
    
    # Resolve relative path if needed
    if not os.path.isabs(image_path):
        json_path = context.get("json_path")
        if json_path:
            base_dir = os.path.dirname(json_path)
            image_path = os.path.join(base_dir, image_path)
    
    try:
        # Check if image exists
        if not os.path.exists(image_path):
            logger.warning(f"Image not found: {image_path}")
            return get_next_block(context)
        
        # Load and display image (in a real implementation, this would show the image)
        logger.info(f"Displaying image: {image_path}")
        # In a real implementation, you would use a GUI library to display the image
    except Exception as e:
        logger.error(f"Error in image action: {e}")
        logger.error(traceback.format_exc())
    
    return get_next_block(context)

def handle_label(params, context):
    """Handle label action."""
    logger.debug(f"Handling label action: {params}")
    # Labels don't do anything, just continue to next block
    return get_next_block(context)

def handle_loop_start(params, context):
    """Handle loop start action."""
    logger.debug(f"Handling loop start action: {params}")
    
    # Don't re-push if we just jumped back here
    current = context.get("current_id")
    if context.has_active_loops() and context.get_current_loop_info()["start"] == current:
        return get_next_block(context)
    
    # Push the loop onto the stack
    context.push_loop(params)
    logger.info(f"Started loop with mode: {params.get('mode')}, count: {params.get('count')}")
    
    return get_next_block(context)

def handle_loop_end(params, context):
    """Handle loop end action."""
    logger.debug(f"Handling loop end action: {params}")
    
    # Only process if there's an open loop on the stack
    if not context.has_active_loops():
        logger.warning("Loop end without matching loop start")
        return get_next_block(context)
    
    # Get start ID and remaining count
    start_id, remaining = context.peek_loop()
    
    # Infinite mode - always repeat
    if remaining is None:
        logger.info("Infinite loop - returning to start")
        return start_id
    
    # Quantity mode - decrement until 1
    if remaining > 1:
        context.update_loop_count(remaining - 1)
        logger.info(f"Loop iteration complete, {remaining-1} iterations remaining")
        return start_id
    else:
        # Last iteration - exit the loop
        context.pop_loop()
        logger.info("Loop complete, exiting loop")
        return get_next_block(context)

def handle_ocr(params, context):
    """Handle OCR action."""
    logger.debug(f"Handling OCR action: {params}")
    
    try:
        # Get region parameters
        x = params.get("x", 0)
        y = params.get("y", 0)
        w = params.get("w", 100)
        h = params.get("h", 100)
        
        # Capture screenshot of the region
        with _grab_lock:
            screenshot = ImageGrab.grab(bbox=(x, y, x+w, y+h))
        
        # Perform OCR
        with _tess_lock:
            text = pytesseract.image_to_string(screenshot)
        
        # Store result in context
        context["ocr_result"] = text.strip()
        logger.info(f"OCR result: {context['ocr_result']}")
    except Exception as e:
        logger.error(f"Error in OCR action: {e}")
        logger.error(traceback.format_exc())
        context["ocr_result"] = ""
    
    return get_next_block(context)

def handle_ocr_duplo(params, context):
    """Handle double OCR action."""
    logger.debug(f"Handling double OCR action: {params}")
    
    try:
        # Get region parameters for first OCR
        x1 = params.get("x1", 0)
        y1 = params.get("y1", 0)
        w1 = params.get("w1", 100)
        h1 = params.get("h1", 100)
        
        # Get region parameters for second OCR
        x2 = params.get("x2", 0)
        y2 = params.get("y2", 0)
        w2 = params.get("w2", 100)
        h2 = params.get("h2", 100)
        
        # Capture screenshots of both regions
        with _grab_lock:
            screenshot1 = ImageGrab.grab(bbox=(x1, y1, x1+w1, y1+h1))
            screenshot2 = ImageGrab.grab(bbox=(x2, y2, x2+w2, y2+h2))
        
        # Perform OCR on both screenshots
        with _tess_lock:
            text1 = pytesseract.image_to_string(screenshot1)
            text2 = pytesseract.image_to_string(screenshot2)
        
        # Store results in context
        context["ocr_result1"] = text1.strip()
        context["ocr_result2"] = text2.strip()
        logger.info(f"OCR result 1: {context['ocr_result1']}")
        logger.info(f"OCR result 2: {context['ocr_result2']}")
    except Exception as e:
        logger.error(f"Error in double OCR action: {e}")
        logger.error(traceback.format_exc())
        context["ocr_result1"] = ""
        context["ocr_result2"] = ""
    
    return get_next_block(context)

def handle_text(params, context):
    """Handle text action."""
    logger.debug(f"Handling text action: {params}")
    
    try:
        # Get text content
        text = params.get("text", "")
        
        # Type the text
        pyautogui.typewrite(text)
        logger.info(f"Typed text: {text}")
    except Exception as e:
        logger.error(f"Error in text action: {e}")
        logger.error(traceback.format_exc())
    
    return get_next_block(context)

def handle_hotkey(params, context):
    """Handle hotkey action."""
    logger.debug(f"Handling hotkey action: {params}")
    
    try:
        # Get keys
        keys = params.get("keys", [])
        if not keys:
            logger.warning("No keys specified for hotkey action")
            return get_next_block(context)
        
        # Press the hotkey combination
        pyautogui.hotkey(*keys)
        logger.info(f"Pressed hotkey: {'+'.join(keys)}")
    except Exception as e:
        logger.error(f"Error in hotkey action: {e}")
        logger.error(traceback.format_exc())
    
    return get_next_block(context)

def handle_start_thread(params, context):
    """Handle start thread action."""
    logger.debug(f"Handling start thread action: {params}")
    
    current_id = context.get("current_id")
    next_map = context.get("next_map", {})
    
    if current_id not in next_map:
        return None
    
    # Get all possible branches
    branches = ["default", "true", "false"]
    destinations = []
    
    for branch in branches:
        destinations.extend(next_map[current_id].get(branch, []))
    
    if not destinations:
        return None
    
    # For now, just continue with the first destination
    # In a real implementation, this would spawn new threads
    return destinations[0]

def handle_end_thread(params, context):
    """Handle end thread action."""
    logger.debug(f"Handling end thread action: {params}")
    # End the current thread
    return None

def handle_screenshot(params, context):
    """Handle screenshot action."""
    logger.debug(f"Handling screenshot action: {params}")
    
    try:
        # Get region parameters
        x = params.get("x", 0)
        y = params.get("y", 0)
        w = params.get("w", 0)
        h = params.get("h", 0)
        
        # If no dimensions provided, capture full screen
        if w <= 0 or h <= 0:
            with _grab_lock:
                screenshot = ImageGrab.grab()
        else:
            with _grab_lock:
                screenshot = ImageGrab.grab(bbox=(x, y, x+w, y+h))
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        
        # Determine save path
        json_path = context.get("json_path")
        if json_path:
            base_dir = os.path.dirname(json_path)
            screenshots_dir = os.path.join(base_dir, "Screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            save_path = os.path.join(screenshots_dir, filename)
        else:
            save_path = os.path.join("Screenshots", filename)
            os.makedirs("Screenshots", exist_ok=True)
        
        # Save the screenshot
        with _io_lock:
            screenshot.save(save_path)
        
        logger.info(f"Screenshot saved to: {save_path}")
        
        # Store the path in context
        context["last_screenshot"] = save_path
    except Exception as e:
        logger.error(f"Error in screenshot action: {e}")
        logger.error(traceback.format_exc())
    
    return get_next_block(context)

def handle_telegram_command(params, context):
    """Handle telegram command action."""
    logger.debug(f"Handling telegram command action: {params}")
    
    # Get the command
    cmd = params.get("command", "").lower()
    
    # Get the stop event from context
    stop_event = context.get("stop_event")
    
    # Get the remote waiters from storage
    import core.storage as storage
    remote_waiters = getattr(storage, "remote_waiters", {})
    
    # Create and register a waiter for this command
    evt = threading.Event()
    remote_waiters.setdefault(cmd, set()).add(evt)
    
    logger.info(f"Waiting for Telegram command: {cmd}")
    
    # Wait until the command is received or stop is requested
    while not evt.is_set() and not stop_event.is_set():
        time.sleep(0.5)
    
    # Remove the waiter
    remote_waiters[cmd].discard(evt)
    
    if evt.is_set():
        logger.info(f"Received Telegram command: {cmd}")
    else:
        logger.info(f"Waiting for Telegram command {cmd} was interrupted")
    
    return get_next_block(context)

def handle_run_macro(params, context):
    """Handle run macro action."""
    logger.debug(f"Handling run macro action: {params}")
    
    try:
        # Get macro path
        macro_path = params.get("path")
        if not macro_path:
            logger.warning("No macro path provided")
            return get_next_block(context)
        
        # Resolve relative path if needed
        if not os.path.isabs(macro_path):
            json_path = context.get("json_path")
            if json_path:
                base_dir = os.path.dirname(json_path)
                macro_path = os.path.join(base_dir, macro_path)
        
        # Check if macro exists
        if not os.path.exists(macro_path):
            logger.warning(f"Macro not found: {macro_path}")
            return get_next_block(context)
        
        # Import here to avoid circular imports
        from core.executor.macro_executor import execute_macro
        
        # Execute the macro
        logger.info(f"Running macro: {macro_path}")
        execute_macro(
            macro_path,
            stop_event=context.get("stop_event"),
            status_win=context.get("status_win")
        )
    except Exception as e:
        logger.error(f"Error in run_macro action: {e}")
        logger.error(traceback.format_exc())
    
    return get_next_block(context)

def handle_text_to_sheet(params, context):
    """Handle text to sheet action."""
    logger.debug(f"Handling text to sheet action: {params}")
    
    try:
        # Get parameters
        sheet_id = params.get("sheet_id")
        sheet_name = params.get("sheet_name", "Sheet1")
        cell = params.get("cell", "A1")
        text = params.get("text", "")
        
        # Use OCR result if specified
        use_ocr = params.get("use_ocr", False)
        if use_ocr and "ocr_result" in context:
            text = context["ocr_result"]
        
        logger.info(f"Adding text to Google Sheet: {sheet_id}, {sheet_name}, {cell}, {text}")
        
        # In a real implementation, you would use the Google Sheets API to update the sheet
        # For now, just log the action
        logger.info(f"Would add text '{text}' to sheet {sheet_id}, worksheet {sheet_name}, cell {cell}")
    except Exception as e:
        logger.error(f"Error in text_to_sheet action: {e}")
        logger.error(traceback.format_exc())
    
    return get_next_block(context)
