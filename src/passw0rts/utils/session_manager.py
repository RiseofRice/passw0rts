"""
Session manager for auto-lock functionality
"""

import time
from typing import Optional
from threading import Thread, Event


class SessionManager:
    """
    Manages user session with auto-lock after inactivity.
    """
    
    def __init__(self, timeout_seconds: int = 300):
        """
        Initialize session manager.
        
        Args:
            timeout_seconds: Seconds of inactivity before auto-lock (default: 5 minutes)
        """
        self.timeout_seconds = timeout_seconds
        self.last_activity = time.time()
        self.is_locked = True
        self._stop_event = Event()
        self._monitor_thread: Optional[Thread] = None
        self._on_lock_callback = None
    
    def unlock(self):
        """Unlock the session"""
        self.is_locked = False
        self.last_activity = time.time()
        self._start_monitor()
    
    def lock(self):
        """Lock the session"""
        self.is_locked = True
        if self._on_lock_callback:
            self._on_lock_callback()
    
    def update_activity(self):
        """Update last activity timestamp"""
        if not self.is_locked:
            self.last_activity = time.time()
    
    def get_idle_time(self) -> float:
        """
        Get idle time in seconds.
        
        Returns:
            Seconds since last activity
        """
        return time.time() - self.last_activity
    
    def set_on_lock_callback(self, callback):
        """
        Set callback function to call when session locks.
        
        Args:
            callback: Function to call on lock
        """
        self._on_lock_callback = callback
    
    def _start_monitor(self):
        """Start monitoring for inactivity"""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._stop_event.clear()
            self._monitor_thread = Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
    
    def _monitor_loop(self):
        """Monitor loop that checks for inactivity"""
        while not self._stop_event.is_set():
            if not self.is_locked:
                idle_time = self.get_idle_time()
                if idle_time >= self.timeout_seconds:
                    self.lock()
                    break
            
            # Check every 10 seconds (sufficient for auto-lock precision)
            self._stop_event.wait(10)
    
    def stop(self):
        """Stop the session monitor"""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
    
    def set_timeout(self, timeout_seconds: int):
        """
        Set the auto-lock timeout.
        
        Args:
            timeout_seconds: New timeout in seconds
        """
        self.timeout_seconds = timeout_seconds
        self.update_activity()  # Reset timer
