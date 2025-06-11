import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from mecheye.profiler import Profiler

@dataclass
class RobotState:
    """Thread-safe container for robot state data"""
    _lock: threading.RLock = threading.RLock()
    scan_process: Optional = None
    scan_started: bool = False
    stop_event: Optional = None
    restart_event: Optional = None
    monitor_thread: Optional = None
    auto_monitor_running: bool = False
    alt_button_pressed: bool = False
    pressed: bool = False
    di0_status: Tuple[int, int] = (0, 0)
    di8_status: Tuple[int, int] = (0, 0)
    di9_status: Tuple[int, int] = (0, 0)
    tcp_status: Tuple[float, float, float, float, float, float] = (0, 0, 0, 0, 0, 0)
    mode: int = 1
    profiler: Profiler = Profiler()
    error_count: int = 0
    last_successful_status: Dict[str, Any] = None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            status = {
                "DI8": self.di8_status[1],
                "DI9": self.di9_status[1],
                "DI0": self.di0_status[1],
                "TCP": self.tcp_status,
                "MODE": self.mode,
                "scan_active": self.scan_started,
                "monitor_active": self.auto_monitor_running
            }
            self.last_successful_status = status.copy()
            return status

    def get_last_status(self) -> Dict[str, Any]:
        with self._lock:
            return self.last_successful_status or {
                "DI8": 0, "DI9": 0, "DI0": 0,
                "scan_active": False, "monitor_active": False,
                "timestamp": time.time()
            }

    def update_di_values(self, di0=None, di8=None, di9=None, tcp=None, mode=None):
        with self._lock:
            if di0 is not None:
                self.di0_status = di0
            if di8 is not None:
                self.di8_status = di8
            if di9 is not None:
                self.di9_status = di9
            if tcp is not None:
                self.tcp_status = tcp
            if mode is not None:
                self.mode = mode

    def set_scan_started(self, started: bool):
        with self._lock:
            self.scan_started = started

    def set_auto_monitor_running(self, running: bool):
        with self._lock:
            self.auto_monitor_running = running

    def set_scan_process(self, process):
        with self._lock:
            self.scan_process = process

    def increment_error_count(self):
        with self._lock:
            self.error_count += 1
            return self.error_count

    def reset_error_count(self):
        with self._lock:
            self.error_count = 0


state = RobotState()