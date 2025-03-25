import logging
import datetime
import json
import os
from typing import Dict, List, Any, Optional, Callable

# Set up logger
logger = logging.getLogger("application_state")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler("application_state.log")
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)

class ApplicationState:
    """
    Centralized state management for the application.
    Uses the Observer pattern to notify components of state changes.
    """
    def __init__(self, history_size=10):
        self._demo_mode = False
        self._observers = []
        self._state_history = []
        self._history_size = history_size
        self._start_time = datetime.datetime.now()
        
        # Record initial state
        self._record_state_change(False, False, self._start_time)
        logger.info("ApplicationState initialized")
        
    def register_observer(self, observer):
        """Register a component to be notified of state changes"""
        observer_name = observer.__class__.__name__
        logger.info(f"Registering observer: {observer_name}")
        self._observers.append(observer)
        
        # Immediately notify new observer of current state
        logger.info(f"Sending current state to new observer {observer_name}")
        try:
            observer.on_demo_mode_changed(self._demo_mode)
            logger.info(f"{observer_name} successfully initialized with current state")
        except Exception as e:
            logger.error(f"Error notifying {observer_name} of current state: {str(e)}")
        
    def set_demo_mode(self, is_active):
        """Set demo mode and notify all observers"""
        if self._demo_mode == is_active:
            logger.info(f"Demo mode already {'active' if is_active else 'inactive'}, ignoring redundant state change")
            return
            
        previous_state = self._demo_mode
        self._demo_mode = is_active
        logger.info(f"Application state changed: demo_mode {previous_state} -> {is_active}")
        
        # Record state change
        self._record_state_change(previous_state, is_active)
        
        # Notify observers
        for observer in self._observers:
            observer_name = observer.__class__.__name__
            logger.info(f"Notifying {observer_name} of demo mode change")
            try:
                observer.on_demo_mode_changed(is_active)
                logger.info(f"{observer_name} successfully processed state change")
            except Exception as e:
                logger.error(f"Error notifying {observer_name} of state change: {str(e)}")
            
    def is_demo_mode(self):
        """Get current demo mode state"""
        return self._demo_mode
    
    def _record_state_change(self, previous, current, timestamp=None):
        """Record a state transition in the history"""
        if timestamp is None:
            timestamp = datetime.datetime.now()
            
        self._state_history.append({
            "timestamp": timestamp,
            "previous_state": previous,
            "new_state": current,
            "observer_count": len(self._observers)
        })
        
        # Maintain limited history size
        if len(self._state_history) > self._history_size:
            self._state_history.pop(0)
            
        # Also log to persistent storage
        try:
            with open("state_history.jsonl", "a") as f:
                f.write(json.dumps({
                    "timestamp": timestamp.isoformat(),
                    "previous": previous,
                    "current": current,
                    "observer_count": len(self._observers)
                }) + "\n")
        except Exception as e:
            logger.error(f"Error writing state history to disk: {str(e)}")
    
    def request_state_refresh(self, observer):
        """Force a state update for a specific observer"""
        observer_name = observer.__class__.__name__
        logger.info(f"State refresh requested by {observer_name}")
        try:
            observer.on_demo_mode_changed(self._demo_mode)
            logger.info(f"State successfully refreshed for {observer_name}")
            return True
        except Exception as e:
            logger.error(f"Error refreshing state for {observer_name}: {str(e)}")
            return False
    
    def health_check(self):
        """Returns detailed health status of all components"""
        now = datetime.datetime.now()
        status = {
            "timestamp": now.isoformat(),
            "uptime": str(now - self._start_time),
            "app_state": {
                "status": "healthy",
                "demo_mode": self._demo_mode,
                "observer_count": len(self._observers),
                "last_state_change": self._state_history[-1]["timestamp"].isoformat() if self._state_history else None
            }
        }
        
        # Collect observer health status
        observer_status = {}
        for observer in self._observers:
            observer_name = observer.__class__.__name__
            if hasattr(observer, "health_status"):
                observer_status[observer_name] = observer.health_status()
            else:
                observer_status[observer_name] = {"status": "unknown", "reason": "health_status method not implemented"}
        
        status["components"] = observer_status
        return status 