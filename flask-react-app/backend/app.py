"""
Jaguar Interface Flask Backend
A Flask-based API server that interfaces with robot hardware and camera systems.
"""
import json
import logging
import multiprocessing
import os
import subprocess
import threading
import time
import numpy as np
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
from mecheye.profiler import Profiler
from Measure.MecheyePackage.config import config

# Local imports
from Measure.MecheyePackage.mecheye_trigger import robot

import threading
# Diğer importlar: time, logger vs.

# Global robot lock tanımı
robot_lock = threading.Lock()

# Load environment variables
load_dotenv('.env')

API_BASE_URL = os.getenv('API_BASE_URL', '192.168.43.80')

# Configuration constants
CONFIG = {
    'HOST': os.getenv('HOST', API_BASE_URL),
    'PORT': int(os.getenv('PORT', 5000)),
    'DEBUG': os.getenv('DEBUG', 'False').lower() == 'true',
    'SCAN_SCRIPT_PATH': os.getenv('SCAN_SCRIPT_PATH', 
        str(Path(__file__).parent.parent / 'Measure' / 'MecheyePackage' / 'scan.py')),
    'LOG_FILE': os.getenv('LOG_FILE', 'scan_process.log'),
    'MAX_RETRIES': int(os.getenv('MAX_RETRIES', 10)),
    'ROBOT_TIMEOUT': float(os.getenv('ROBOT_TIMEOUT', 2.0)),
    'SOCKET_PING_INTERVAL': int(os.getenv('SOCKET_PING_INTERVAL', 10)),
    'SOCKET_PING_TIMEOUT': int(os.getenv('SOCKET_PING_TIMEOUT', 5))
}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CONFIG['LOG_FILE'], encoding='utf-8', errors='replace'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
# Disable logging for /api/robot/status endpoint
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure SocketIO with better settings
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='threading',
    ping_timeout=CONFIG['SOCKET_PING_TIMEOUT'],
    ping_interval=CONFIG['SOCKET_PING_INTERVAL'],
    max_http_buffer_size=1024 * 1024
)

@dataclass
class RobotState:
    """Thread-safe container for robot state data"""
    _lock: threading.RLock = threading.RLock()
    scan_process: Optional[subprocess.Popen] = None
    scan_started: bool = False
    stop_event: Optional[multiprocessing.Event] = None
    restart_event: Optional[multiprocessing.Event] = None
    monitor_thread: Optional[threading.Thread] = None
    auto_monitor_running: bool = False
    pressed: bool = False
    di0_status: Tuple[int, int] = (0, 0)
    di8_status: Tuple[int, int] = (0, 0)
    di9_status: Tuple[int, int] = (0, 0)
    tcp_status: Tuple[float, float, float, float, float, float] = (0, 0, 0, 0, 0, 0)
    profiler: Profiler = Profiler()
    error_count: int = 0
    last_successful_status: Dict[str, Any] = None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current robot status as a dictionary for the frontend"""
        with self._lock:
            status = {
                "DI8": self.di8_status[1] if isinstance(self.di8_status, tuple) else 0,
                "DI9": self.di9_status[1] if isinstance(self.di9_status, tuple) else 0,
                "DI0": self.di0_status[1] if isinstance(self.di0_status, tuple) else 1,
                "TCP": self.tcp_status,
                "scan_active": self.scan_started,
                "monitor_active": self.auto_monitor_running,
                "timestamp": time.time()
            }
            # Update last successful status
            self.last_successful_status = status.copy()
            return status
    
    def get_last_status(self) -> Dict[str, Any]:
        """Get the last successful status if available, or a default status"""
        with self._lock:
            if self.last_successful_status:
                return self.last_successful_status
            return {
                "DI8": 0, "DI9": 0, "DI0": 0,
                "scan_active": False, "monitor_active": False,
                "timestamp": time.time()
            }
            
    def update_di_values(self, di0=None, di8=None, di9=None, tcp=None):
        """Update DI values with thread safety"""
        with self._lock:
            if di0 is not None:
                self.di0_status = di0
            if di8 is not None:
                self.di8_status = di8
            if di9 is not None:
                self.di9_status = di9
            if tcp is not None:
                self.tcp_status = tcp
                
    def set_scan_started(self, started: bool):
        """Thread-safe update of scan_started flag"""
        with self._lock:
            self.scan_started = started
            
    def set_auto_monitor_running(self, running: bool):
        """Thread-safe update of auto_monitor_running flag"""
        with self._lock:
            self.auto_monitor_running = running
            
    def set_scan_process(self, process: Optional[subprocess.Popen]):
        """Thread-safe update of scan process"""
        with self._lock:
            self.scan_process = process
    
    def increment_error_count(self):
        """Thread-safe increment of error count"""
        with self._lock:
            self.error_count += 1
            return self.error_count
    
    def reset_error_count(self):
        """Thread-safe reset of error count"""
        with self._lock:
            self.error_count = 0

# Create global state object
state = RobotState()

def safe_get_di(channel, index, max_retries=CONFIG['MAX_RETRIES']):
    """
    Safely get DI value from robot with reconnection handling and timeout
    
    Args:
        channel: DI channel to read
        index: Index to read
        max_retries: Maximum number of retries before giving up
        
    Returns:
        Tuple of (value, error_code)
    """
    retries = 0
    while retries < max_retries:
        try:
            result_container = []
            
            def _get_di():
                try:
                    # Robot erişimini lock altında gerçekleştiriyoruz.
                    with robot_lock:
                        result = robot.GetDI(channel, index)
                    if isinstance(result, tuple) and result[1] == -1:
                        logger.error(f"GetDI({channel}, {index}) returned -1. (Source: GetDI call)")
                        raise Exception("接收机器人状态字节 -1")
                    result_container.append(result)
                except Exception as e:
                    result_container.append(e)
            
            # Thread oluşturup başlatılıyor
            di_thread = threading.Thread(target=_get_di)
            di_thread.daemon = True
            di_thread.start()
            
            # Belirlenen süre kadar bekliyoruz
            di_thread.join(CONFIG['ROBOT_TIMEOUT'])
            
            if di_thread.is_alive():
                logger.error(f"GetDI({channel}, {index}) timed out after {CONFIG['ROBOT_TIMEOUT']} seconds")
                retries += 1
                try:
                    with robot_lock:
                        robot.reconnect()
                except Exception as recon_e:
                    logger.error(f"RPC reconnection failed after timeout: {recon_e}")
                time.sleep(0.5)
                continue
            
            if not result_container:
                logger.error(f"GetDI({channel}, {index}) returned no result")
                retries += 1
                continue
                
            if isinstance(result_container[0], Exception):
                raise result_container[0]
                
            return result_container[0]
            
        except Exception as e:
            retries += 1
            if "接收机器人状态字节 -1" in str(e) and retries < max_retries:
                logger.error(f"Robot communication error: {e}. Reconnecting RPC... (Attempt {retries}/{max_retries})")
                try:
                    with robot_lock:
                        robot.reconnect()
                except Exception as recon_e:
                    logger.error(f"RPC reconnection failed: {recon_e}")
                    time.sleep(1)
                time.sleep(0.5)
            else:
                if retries >= max_retries:
                    logger.error(f"Max retries reached for GetDI({channel}, {index})")
                    return (-1, -1)
                raise e
    
    return (-1, -1)

def safe_get_tcp(max_retries=CONFIG['MAX_RETRIES']):
    retries = 0
    while retries < max_retries:
        result_container = []
        try:
            def _get_tcp():
                try:
                    # Robot erişimini lock altında gerçekleştiriyoruz.
                    with robot_lock:
                        tcp = robot.GetActualTCPPose()
                    if isinstance(tcp, tuple) and tcp[1] == -1:
                        logger.error("GetTCP returned -1. (Source: GetTCP call)")
                        raise Exception("接收机器人状态字节 -1")
                    result_container.append(tcp)
                except Exception as e:
                    result_container.append(e)
        
            tcp_thread = threading.Thread(target=_get_tcp)
            tcp_thread.daemon = True
            tcp_thread.start()
            
            tcp_thread.join(CONFIG['ROBOT_TIMEOUT'])
            
            if tcp_thread.is_alive():
                logger.error(f"GetTCP timed out after {CONFIG['ROBOT_TIMEOUT']} seconds")
                retries += 1
                try:
                    with robot_lock:
                        robot.reconnect()
                except Exception as recon_e:
                    logger.error(f"RPC reconnection failed after timeout: {recon_e}")
                time.sleep(0.5)
                continue
            
            if not result_container:
                logger.error("GetTCP returned no result")
                retries += 1
                continue
                
            if isinstance(result_container[0], Exception):
                raise result_container[0]
                
            return result_container[0]
            
        except Exception as e:
            retries += 1
            if "接收机器人状态字节 -1" in str(e) and retries < max_retries:
                logger.error(f"Robot communication error: {e}. Reconnecting RPC... (Attempt {retries}/{max_retries})")
                try:
                    with robot_lock:
                        robot.reconnect()
                except Exception as recon_e:
                    logger.error(f"RPC reconnection failed: {recon_e}")
                    time.sleep(1)
                time.sleep(0.5)
            else:
                if retries >= max_retries:
                    logger.error("Max retries reached for GetTCP")
                    return (-1, -1, -1, -1, -1, -1)
                raise e
    
    return (-1, -1, -1, -1, -1, -1)

def calculate_tolerance_distance(value: float, target: float) -> float:
    """Calculate the absolute distance between a value and its target."""
    return np.abs(value - target)

def get_gradient_color(distance: float, tolerance: float) -> str:
    """
    Generate a color hex code based on how far a value is from its tolerance range.
    
    Args:
        distance: The absolute distance from the target value
        tolerance: The allowed tolerance range
    
    Returns:
        A hex color code string (e.g., "FF0000" for red)
    """
    if distance > tolerance:
        return "FF0000"  # Red for values outside tolerance
    
    ratio = distance / tolerance
    red = int(255 * ratio)
    green = int(255 * (1 - ratio))
    blue = 0
    
    return f"{red:02X}{green:02X}{blue:02X}"

def make_json_serializable(obj):
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    elif isinstance(obj, (np.bool_,)):  # numpy bool varsa
        return bool(obj)
    elif isinstance(obj, (np.integer, np.int64, np.float64)):
        return obj.item()  # numpy sayıları
    else:
        return obj

def generate_json_data(results, tolerances=config.tolerances):
    """
    Generates JSON data from scan results, with tolerance checks and color coding.
    
    Args:
        results (list): List of dictionaries containing scan result data
        tolerances (dict, optional): Dictionary of feature tolerances with format {feature: (target, tolerance)}
    
    Returns:
        dict: JSON-compatible data structure containing processed results with color coding
    """
    if tolerances is None:
        tolerances = {}
    
    processed_data = {
        "scan_results": [],
        "summary": {
            "total_iterations": len(results),
            "passed_iterations": 0
        }
    }
    
    for iteration, result in enumerate(results, start=1):
        iteration_ok = True
        
        # Determine iteration background color (alternating)
        iteration_color = "FCE4D6" if iteration % 2 == 0 else "D9EAD3"
        
        iteration_data = {
            "iteration": iteration,
            "background_color": iteration_color,
            "features": [],
            "status": {
                "ok": True,
                "color": "00B050"  # Default to green (will be updated if any test fails)
            }
        }
        
        for feature, value in result.items():
            feature_data = {
                "name": feature,
                "value": value,
                "background_color": iteration_color
            }
            
            # Handle dictionary values
            if isinstance(value, dict):
                feature_data["value"] = value
            
            # Handle non-serializable values
            try:
                json.dumps(feature_data["value"])
            except TypeError:
                feature_data["value"] = str(value)
            
            # Tolerance check and color coding
            if feature in tolerances:
                target, tolerance = tolerances[feature]
                
                try:
                    # Try to convert to numeric for tolerance check
                    numeric_value = float(value) if isinstance(value, str) else value
                    
                    # Calculate distance from target
                    distance = calculate_tolerance_distance(numeric_value, target)
                    within_tolerance = distance <= tolerance
                    
                    # Generate color code
                    color_code = get_gradient_color(distance, tolerance)
                    
                    tolerance_data = {
                        "target": target,
                        "tolerance": tolerance,
                        "distance": distance,
                        "tolerance_remaining": tolerance - distance,
                        "within_tolerance": within_tolerance,
                        "color": "00B050" if within_tolerance else "FF0000"  # Green if within tolerance, red if not
                    }
                    
                    # Add gradient color for visualization
                    tolerance_data["gradient_color"] = color_code
                    
                    feature_data["tolerance_check"] = tolerance_data
                    feature_data["value_color"] = tolerance_data["color"]
                    
                    # Update iteration status if tolerance check fails
                    if not within_tolerance:
                        iteration_data["status"]["ok"] = False
                        iteration_data["status"]["color"] = "FF0000"  # Red for failed iteration
                        if "failure_reasons" not in iteration_data["status"]:
                            iteration_data["status"]["failure_reasons"] = []
                        iteration_data["status"]["failure_reasons"].append(f"{feature} out of tolerance")
                        
                except (ValueError, TypeError):
                    # If value can't be converted to numeric, no tolerance check possible
                    feature_data["tolerance_check"] = {
                        "error": "Value cannot be numerically compared",
                        "target": target,
                        "tolerance": tolerance
                    }
            
            iteration_data["features"].append(feature_data)
        
        # Update summary data
        if iteration_data["status"]["ok"]:
            processed_data["summary"]["passed_iterations"] += 1
            
        processed_data["scan_results"].append(iteration_data)
    
    # Add pass rate to summary
    processed_data["summary"]["pass_rate"] = (
        processed_data["summary"]["passed_iterations"] / processed_data["summary"]["total_iterations"] 
        if processed_data["summary"]["total_iterations"] > 0 else 0
    )
    
    # Add color coding to summary
    pass_rate = processed_data["summary"]["pass_rate"]
    if pass_rate == 1.0:
        processed_data["summary"]["color"] = "00B050"  # Green for 100% pass
    elif pass_rate >= 0.8:
        processed_data["summary"]["color"] = "FFFF00"  # Yellow for 80%+ pass
    else:
        processed_data["summary"]["color"] = "FF0000"  # Red for <80% pass
    
    # Make JSON serializable
    serializable_data = make_json_serializable(processed_data)
    
    # Save to file for debugging
    try:
        with open("processed_data.json", "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving processed data to file: {e}")
    
    return serializable_data

def log_subprocess_output(process, log_prefix="[SCAN]", error_prefix="[SCAN_ERR]"):
    """
    Log subprocess stdout and stderr in separate threads
    
    Args:
        process: Subprocess.Popen object to monitor
        log_prefix: Prefix for stdout log messages
        error_prefix: Prefix for stderr log messages
    """
    def _log_stdout():
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    # logger.info(f"{log_prefix} {line.strip()}")
                    pass
                else:
                    break
        except Exception as e:
            logger.error(f"Error logging stdout: {e}")

    def _log_stderr():
        try:
            for line in iter(process.stderr.readline, ''):
                if not line:
                    break
                # Filter out specific error messages
                if "Failed to obtain the IP address" in line:
                    continue
                logger.error(f"{error_prefix} {line.strip()}")
        except Exception as e:
            logger.error(f"Error logging stderr: {e}")
            
    # Start logging threads
    stdout_thread = threading.Thread(target=_log_stdout, daemon=True)
    stderr_thread = threading.Thread(target=_log_stderr, daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    
    return stdout_thread, stderr_thread

def cleanup_scan_process(process):
    """Safely clean up a subprocess"""
    if process:
        try:
            if process.stdin:
                process.stdin.close()
            if process.poll() is None:  # Still running
                process.terminate()
                try:
                    process.wait(timeout=5)  # Wait up to 5 seconds
                except subprocess.TimeoutExpired:
                    process.kill()  # Force kill if terminate hangs
                    process.wait()
            logger.info("scan.py was closed")
        except Exception as e:
            logger.error(f"Error closing scan process: {e}")

def run_scan(stop_event):
    """
    Function that starts scan.py subprocess with proper input/output handling
    
    Args:
        stop_event: Event to signal when to stop scanning
    """
    try:
        # Start the subprocess with stdin as a pipe
        scan_process = subprocess.Popen(
            ["python3", CONFIG['SCAN_SCRIPT_PATH']],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True
        )
        logger.info("Scan process started successfully")
        
        # Update global state
        state.set_scan_process(scan_process)
        
        # Start logging threads
        stdout_thread, stderr_thread = log_subprocess_output(scan_process)
        
        # Monitor subprocess to prevent zombies
        start_time = time.time()
        
        while not stop_event.is_set():
            # Check if process has terminated unexpectedly
            if scan_process.poll() is not None:
                logger.warning(f"Scan process terminated with code {scan_process.returncode}")
                break
                
            # Check if process has been running too long (timeout)
            if time.time() - start_time > 3600:  # 1 hour timeout
                logger.warning("Scan process timeout - terminating")
                break
                
            time.sleep(0.1)

        # Stop signal received, terminate subprocess
        cleanup_scan_process(scan_process)
        
        # Wait for logging threads to finish
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        
        return scan_process.stdout, scan_process.stderr
    except Exception as e:
        logger.error(f"Error in run_scan: {e}")
        return None, None

def monitor_robot(stop_event, restart_event):
    """
    Monitor robot status and control scan process based on DI values
    
    Args:
        stop_event: Event to signal scan process to stop
        restart_event: Event to signal scan process to restart
    """
    # Allow time for scan process to initialize
    time.sleep(1)

    logger.info(f"Monitor robot thread started - Current DI8 status: {safe_get_di(8, 0)}")

    # Monitor DI8 for safety condition
    while not stop_event.is_set():
        try:
            di8 = safe_get_di(8, 0)
        except Exception as e:
            logger.error(f"Error getting DI8: {e}")
            break

        # Stop scan if DI8 is not in safe state
        if di8 != (0, 0):
            logger.info(f"Stop condition detected: DI8={di8}")
            state.profiler.stop_acquisition()
            state.profiler.disconnect()
            robot.StopMotion()
            stop_event.set()
            state.set_scan_started(False)
            break

        time.sleep(0.5)

    logger.info("Monitor robot waiting for restart signal...")

    # Wait for restart signal from DI9
    wait_time = 5
    start = time.time()
    while True:
        try:
            current_di9 = safe_get_di(9, 0)
        except Exception as e:
            logger.error(f"Error getting DI9: {e}")
            break

        if current_di9 == (0, 1):
            logger.info(f"Restart signal detected: DI9={current_di9}")
            restart_event.set()
            break
        elif time.time() - start > wait_time:
            logger.info("Press start button to restart")
            wait_time += 5
            start = time.time()

    logger.info("Monitor robot thread exiting")

def update_robot_status():
    """
    Continuously update robot status and send to frontend via SocketIO
    """
    while True:
        di_data = {}  # Store DI data temporarily
        try:
            # Get DI Status
            di8 = safe_get_di(8, 0)
            di9 = safe_get_di(9, 0)
            di0 = safe_get_di(0, 0)
            # tcp = safe_get_tcp()
            # Update state
            state.update_di_values(di0=di0, di8=di8, di9=di9, tcp=[0,0,0,0,0,0])
            
            # Store for subprocess
            di_data['di8'] = di8[1] if isinstance(di8, tuple) else 0
            di_data['di9'] = di9[1] if isinstance(di9, tuple) else 0
            di_data['di0_tuple'] = di0 if isinstance(di0, tuple) else 1

            # Create status dictionary with TCP pose
            status = state.get_status()
            
            # Send status to frontend
            with app.app_context():
                socketio.emit('robot_status', status)

        except Exception as e:
            logger.error(f"Error getting robot status or emitting: {e}")

        # Send data to subprocess if active
        if 'di0_tuple' in di_data and state.scan_process is not None and state.scan_process.poll() is None:
            try:
                data_to_send = json.dumps({
                    "DI0": [di_data['di0_tuple'][0], di_data['di0_tuple'][1]]
                }) + "\n"
                state.scan_process.stdin.write(data_to_send)
                state.scan_process.stdin.flush()
            except BrokenPipeError:
                logger.error("Pipe broken while sending DI0, subprocess may have closed.")
            except Exception as e:
                logger.error(f"Error sending DI0 data to subprocess: {e}")

        time.sleep(0.2)

def auto_restart_monitor():
    """
    Monitor for automatic restart conditions based on DI values
    """
    state.set_auto_monitor_running(True)
    logger.info("Auto-restart monitor started")

    while True:
        # Check conditions for starting a new scan:
        # 1. Scan is not already running
        # 2. DI9 (start button) is (0,1)
        # 3. DI8 (safety button) is (0,0)
        if (not state.scan_started and 
            state.di9_status == (0, 1) and 
            state.di8_status == (0, 0)):
            
            logger.info(f"Auto-restart triggered by DI9={state.di9_status}, DI8={state.di8_status}")

            # Create new events
            state.stop_event = multiprocessing.Event()
            state.restart_event = multiprocessing.Event()

            # Start new scan process
            scan_process_thread = threading.Thread(
                target=run_scan, 
                args=(state.stop_event,)
            )
            scan_process_thread.start()

            # Start new monitor thread
            state.monitor_thread = threading.Thread(
                target=monitor_robot, 
                args=(state.stop_event, state.restart_event), 
                daemon=True
            )
            state.monitor_thread.start()

            state.set_scan_started(True)
            logger.info("Scan started successfully")

            # Wait for initialization
            time.sleep(1)

        # Check for restart request
        if state.restart_event and state.restart_event.is_set() and not state.scan_started:
            logger.info("Processing restart event")
            state.restart_event.clear()

            if state.di8_status == (0, 0):
                logger.info("Conditions are safe for restart")
                state.stop_event = multiprocessing.Event()

                scan_process_thread = threading.Thread(
                    target=run_scan, 
                    args=(state.stop_event,)
                )
                scan_process_thread.start()

                state.monitor_thread = threading.Thread(
                    target=monitor_robot, 
                    args=(state.stop_event, state.restart_event), 
                    daemon=True
                )
                state.monitor_thread.start()

                state.set_scan_started(True)
                logger.info("Scan restarted successfully")
            else:
                logger.warning(f"Cannot restart: unsafe conditions DI8={state.di8_status}")

        time.sleep(0.5)

# API Routes
@app.route('/api/hello', methods=['GET'])
def hello_world():
    """Simple API endpoint to test if server is running"""
    return jsonify(message="Bağlantı Kuruldu!")

@app.route('/api/scan', methods=['POST'])
def scan():
    """API endpoint to control scanning process"""
    data = request.get_json()
    logger.info(f"Received scan request: {data}")
    
    # Validate request
    if not data or 'message' not in data:
        return jsonify(message="Invalid request"), 400
    
    # Process based on message type
    if data['message'] == 'START':
        # Reset any errors
        robot.ResetAllError()
        
        # Start auto-restart monitor if not already running
        if not state.auto_monitor_running:
            auto_thread = threading.Thread(target=auto_restart_monitor, daemon=True)
            auto_thread.start()
            
        # Return appropriate message based on current state
        if state.scan_started:
            return jsonify(message="Scanning already in progress"), 200
        else:
            return jsonify(message="Scanning system ready, press start button on robot"), 200
    
    elif data['message'] == 'STOP':
        if state.scan_started and state.stop_event:
            state.stop_event.set()
            state.set_scan_started(False)
            return jsonify(message="Scanning stopped"), 200
        else:
            return jsonify(message="No active scanning process found"), 200
    
    elif data['message'] == 'STATUS':
        status = "RUNNING" if state.scan_started else "STOPPED"
        return jsonify(message=status)
    
    elif data['message'] == 'RESTART':
        # Force stop any running process
        if state.scan_started and state.stop_event:
            state.stop_event.set()
            state.set_scan_started(False)
            time.sleep(0.5)  # Give time for process to stop
        
        # Only restart if DI8 is safe
        if safe_get_di(8, 0) == (0, 0):
            # Create new events
            state.stop_event = multiprocessing.Event()
            state.restart_event = multiprocessing.Event()
            
            # Start new scan process
            scan_process_thread = threading.Thread(
                target=run_scan, 
                args=(state.stop_event,)
            )
            scan_process_thread.start()
            
            # Start new monitor thread
            state.monitor_thread = threading.Thread(
                target=monitor_robot, 
                args=(state.stop_event, state.restart_event), 
                daemon=True
            )
            state.monitor_thread.start()
            
            state.set_scan_started(True)
            return jsonify(message="Scanning restarted"), 200
        else:
            return jsonify(message="Cannot restart: unsafe conditions"), 400
    
    return jsonify(message="Unknown command"), 400

@app.route('/api/scan/latest', methods=['GET'])
def get_latest_scan():
    try:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scan_output.json')
        if not os.path.exists(file_path):
            return jsonify({"message": "Veri bulunamadı"}), 404
            
        with open(file_path, 'r') as f:
            lines = f.readlines()
            if not lines:
                return jsonify({"message": "Veri bulunamadı"}), 404
            
            # Parse all lines into a list of scan results
            all_results = []
            for line in lines:
                line = line.strip()
                if line:  # Skip empty lines
                    try:
                        scan_data = json.loads(line)
                        all_results.append(scan_data)
                    except json.JSONDecodeError:
                        # Skip invalid JSON lines
                        continue
            
            if not all_results:
                return jsonify({"message": "Veri bulunamadı"}), 404
                
            # Process all results with generate_json_data
            processed_data = generate_json_data(all_results)
            
            # Ensure all values are JSON serializable
            def convert_to_json_serializable(obj):
                if isinstance(obj, dict):
                    return {k: convert_to_json_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_to_json_serializable(i) for i in obj]
                elif isinstance(obj, (bool, int, float, str, type(None))):
                    # Handle boolean values explicitly
                    if isinstance(obj, bool):
                        return str(obj).lower()  # Convert True to "true" and False to "false"
                    return obj
                else:
                    return str(obj)  # Convert any other type to string
            
            json_serializable_data = convert_to_json_serializable(processed_data)
            return jsonify(json_serializable_data), 200
            
    except json.JSONDecodeError:
        return jsonify({"message": "Geçersiz JSON formatı"}), 500
    except Exception as e:
        return jsonify({"message": f"Hata: {str(e)}"}), 500

@app.route('/api/scan/log', methods=['GET'])
def get_scan_log():
    """API endpoint to retrieve scan logs"""
    try:
        with open(CONFIG['LOG_FILE'], 'r') as file:
            logs = file.readlines()
        
        # Filter out unwanted log messages
        filtered_logs = [
            log for log in logs 
            if "Failed to obtain the IP address" not in log
        ]
        
        return jsonify({'logs': filtered_logs}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/robot/air', methods=['POST'])
def control_air():
    """API endpoint to control air signal"""
    try:
        # Toggle state and set appropriate DO
        if state.pressed:
            robot.SetDO(7, 1)
            state.pressed = False
        else:
            robot.SetDO(7, 0)
            state.pressed = True
        return jsonify({
            "success": True, 
            "message": "Air signal sent successfully"
        })
    except Exception as e:
        logger.error(f"Error sending air signal: {str(e)}")
        return jsonify({
            "success": False, 
            "message": str(e)
        }), 500

if __name__ == '__main__':
    # Initialize state
    state.set_scan_started(False)
    state.set_auto_monitor_running(False)
    
    # Start status update thread
    status_thread = threading.Thread(target=update_robot_status, daemon=False)
    status_thread.start()
    
    # # Start auto-restart monitor
    # auto_thread = threading.Thread(target=auto_restart_monitor, daemon=False)
    # auto_thread.start()
    
    # Start Flask SocketIO server
    socketio.run(
        app, 
        host=CONFIG['HOST'], 
        port=CONFIG['PORT'], 
        debug=CONFIG['DEBUG']
    )