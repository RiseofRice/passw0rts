"""
Clipboard handler with timeout functionality
"""

import threading
import pyperclip


class ClipboardHandler:
    """
    Handles clipboard operations with automatic clearing.
    """
    
    @staticmethod
    def copy(text: str):
        """
        Copy text to clipboard.
        
        Args:
            text: Text to copy
        """
        try:
            pyperclip.copy(text)
        except Exception as e:
            # Fallback for systems without clipboard support
            import sys
            print(f"Warning: Clipboard operation failed: {e}", file=sys.stderr)
    
    @staticmethod
    def clear():
        """Clear the clipboard"""
        try:
            pyperclip.copy("")
        except Exception as e:
            # Silent failure is acceptable for clipboard clearing
            pass
    
    @staticmethod
    def copy_with_timeout(text: str, timeout: int = 30):
        """
        Copy text to clipboard and clear after timeout.
        
        Args:
            text: Text to copy
            timeout: Seconds before clearing (default: 30)
        """
        ClipboardHandler.copy(text)
        
        # Set up timer to clear
        timer = threading.Timer(timeout, ClipboardHandler.clear)
        timer.daemon = True
        timer.start()
    
    @staticmethod
    def paste() -> str:
        """
        Get text from clipboard.
        
        Returns:
            Clipboard content
        """
        try:
            return pyperclip.paste()
        except Exception as e:
            import sys
            print(f"Warning: Clipboard paste failed: {e}", file=sys.stderr)
            return ""
