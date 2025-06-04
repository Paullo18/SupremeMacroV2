"""
Execution context for Supreme Macro.
Provides context management for macro execution.
"""

class ExecContext(dict):
    """
    Enhanced dictionary for macro execution context.
    Provides loop stack management and flow control.
    """
    def __init__(self, data=None):
        """
        Initialize the execution context.
        
        Args:
            data: Initial data dictionary
        """
        super().__init__(data or {})
        self._loop_stack = []
    
    def push_loop(self, params):
        """
        Register the start of a loop on the stack.
        
        For infinite mode, remaining=None
        For quantity mode, remaining=count
        
        Args:
            params: Loop parameters dictionary
        """
        start_id = self["current_id"]
        mode = params.get("mode", "quantidade")
        
        if mode == "infinito":
            # Infinite loop
            self._loop_stack.append({
                "start": start_id,
                "remaining": None,
                "mode": "infinito"
            })
        else:
            # Quantity-based loop
            count = int(params.get("count", 0))
            self._loop_stack.append({
                "start": start_id,
                "remaining": count,
                "mode": "quantidade"
            })
    
    def peek_loop(self):
        """
        Get the current loop information without modifying the stack.
        
        Returns:
            Tuple of (start_id, remaining)
        """
        if not self._loop_stack:
            raise ValueError("No active loops in the stack")
        
        top = self._loop_stack[-1]
        return top["start"], top["remaining"]
    
    def update_loop_count(self, new_count):
        """
        Update the remaining count for the current loop.
        
        Args:
            new_count: New remaining count
        """
        if not self._loop_stack:
            raise ValueError("No active loops in the stack")
        
        self._loop_stack[-1]["remaining"] = new_count
    
    def jump_to(self, block_id):
        """
        Redirect execution flow to another block.
        
        Args:
            block_id: ID of the target block
        """
        if "set_current" not in self:
            raise ValueError("Context does not have a set_current function")
        
        self["set_current"](block_id)
    
    def pop_loop(self):
        """
        Remove the current loop from the stack.
        """
        if not self._loop_stack:
            raise ValueError("No active loops in the stack")
        
        self._loop_stack.pop()
    
    def has_active_loops(self):
        """
        Check if there are any active loops.
        
        Returns:
            True if there are active loops, False otherwise
        """
        return len(self._loop_stack) > 0
    
    def get_loop_stack_depth(self):
        """
        Get the current depth of the loop stack.
        
        Returns:
            Number of active loops
        """
        return len(self._loop_stack)
    
    def get_current_loop_info(self):
        """
        Get detailed information about the current loop.
        
        Returns:
            Dictionary with loop information or None if no active loops
        """
        if not self._loop_stack:
            return None
        
        return self._loop_stack[-1].copy()
    
    def clear_loop_stack(self):
        """
        Clear all loops from the stack.
        """
        self._loop_stack.clear()
