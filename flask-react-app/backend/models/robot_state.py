import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, List
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
    di_values: List[int] = None  # DI0-DI15
    tcp_status: List[float] = None
    mode: int = 1
    profiler: Profiler = Profiler()
    error_count: int = 0
    last_successful_status: Dict[str, Any] = None

    def __post_init__(self):
        if self.di_values is None:
            self.di_values = [0] * 16  # DI0-DI15 initialize to 0
        if self.tcp_status is None:
            self.tcp_status = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # x, y, z, rx, ry, rz

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            status = {
                "DI0": self.di_values[0],
                "DI1": self.di_values[1],
                "DI2": self.di_values[2],
                "DI3": self.di_values[3],
                "DI4": self.di_values[4],
                "DI5": self.di_values[5],
                "DI6": self.di_values[6],
                "DI7": self.di_values[7],
                "DI8": self.di_values[8],
                "DI9": self.di_values[9],
                "DI10": self.di_values[10],
                "DI11": self.di_values[11],
                "DI12": self.di_values[12],
                "DI13": self.di_values[13],
                "DI14": self.di_values[14],
                "DI15": self.di_values[15],
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
                "DI0": 0, "DI1": 0, "DI2": 0, "DI3": 0, "DI4": 0, "DI5": 0, "DI6": 0, "DI7": 0,
                "DI8": 0, "DI9": 0, "DI10": 0, "DI11": 0, "DI12": 0, "DI13": 0, "DI14": 0, "DI15": 0,
                "scan_active": False, "monitor_active": False,
                "timestamp": time.time()
            }

    def update_di_values(self, di_values: List[int] = None, tcp=None, mode=None):
        with self._lock:
            if di_values is not None and len(di_values) == 16:
                self.di_values = di_values.copy()
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