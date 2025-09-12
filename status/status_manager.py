import threading
import time
import json
from typing import Dict, Any, List, Callable
from queue import Queue


class StatusManager:
    def __init__(self):
        self._status = {
            "camera_connected": False,
            "recording": False,
            "wheel_speed": 100,
            "turn_speed": 50,
            "timestamp": time.strftime("%H:%M:%S")
        }
        self._lock = threading.Lock()
        self._subscribers = []
        self._update_queue = Queue()
        
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        with self._lock:
            return self._status.copy()
    
    def update_status(self, **kwargs) -> bool:
        """Update status and notify subscribers if changed"""
        changed = False
        with self._lock:
            for key, value in kwargs.items():
                if key in self._status and self._status[key] != value:
                    self._status[key] = value
                    changed = True
            
            if changed:
                self._status["timestamp"] = time.strftime("%H:%M:%S")
                # Notify all subscribers
                for callback in self._subscribers:
                    try:
                        callback(self._status.copy())
                    except Exception as e:
                        print(f"Error notifying subscriber: {e}")
        
        return changed
    
    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to status changes"""
        with self._lock:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """Unsubscribe from status changes"""
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
    
    def get_camera_status(self) -> bool:
        with self._lock:
            return self._status["camera_connected"]
    
    def get_recording_status(self) -> bool:
        with self._lock:
            return self._status["recording"]
    
    def get_wheel_speed(self) -> int:
        with self._lock:
            return self._status["wheel_speed"]
    
    def get_turn_speed(self) -> int:
        with self._lock:
            return self._status["turn_speed"]


# Global instance
status_manager = StatusManager()
