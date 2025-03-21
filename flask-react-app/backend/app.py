from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import json
import subprocess
import multiprocessing
import threading
import time
import logging
from Measure.MecheyePackage.mecheye_trigger import robot, TriggerWithExternalDeviceAndFixedRate
from mecheye.profiler import Profiler

# Set up logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scan_process.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# # Disable logging for /api/robot/status endpoint
# logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Load environment variables
load_dotenv('.env')

# Initialize Flask app
app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})  # Allow CORS for all API endpoints

# Global variables
scan_process = None
profiler = Profiler()
scan_started = False
stop_event = None
restart_event = None
monitor_thread = None
auto_monitor_running = False
pressed = False

def log_stdout(process, log_prefix="[SCAN]"):
    """Read and log the stdout of a process"""
    try:
        for line in iter(process.stdout.readline, ''):
            if line:
                logger.info(f"{log_prefix} {line.strip()}")
            else:
                break
    except Exception as e:
        logger.error(f"Error logging stdout: {e}")

def log_stderr(process, log_prefix="[SCAN_ERR]"):
    """Read and log the stderr of a process"""
    try:
        for line in iter(process.stderr.readline, ''):
            if line:
                logger.error(f"{log_prefix} {line.strip()}")
            else:
                break
    except Exception as e:
        logger.error(f"Error logging stderr: {e}")

def run_scan(stop_event):
    """Function that starts scan.py with current DI0 value"""
    global scan_process
    try:
        # Start the subprocess with stdin as a pipe
        scan_process = subprocess.Popen(
            ["python3", "/home/eypan/Documents/JaguarInterface/flask-react-app/Measure/MecheyePackage/scan.py"],
            stdin=subprocess.PIPE,  # Use PIPE for stdin to send data
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            bufsize=1,  # Line buffered
            universal_newlines=True  # Text mode
        )
        logger.info("Scan process started successfully")
        
        # Start threads for logging stdout and stderr
        stdout_thread = threading.Thread(target=log_stdout, args=(scan_process,), daemon=True)
        stderr_thread = threading.Thread(target=log_stderr, args=(scan_process,), daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        # Wait for stop signal
        while not stop_event.is_set():
            time.sleep(0.1)

        # Stop signal received, terminate subprocess
        if scan_process:
            try:
                scan_process.stdin.close()  # Close stdin pipe
                scan_process.terminate()
                logger.info("scan.py was closed")
            except Exception as e:
                logger.error(f"Error closing scan process: {e}")
            
        # Wait for logging threads to finish
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        
        return scan_process.stdout, scan_process.stderr
    except Exception as e:
        logger.error(f"Error in run_scan: {e}")
        return None, None

def monitor_robot(stop_event, restart_event):
    """Monitors robot status, stops scan process if necessary"""
    global scan_process, scan_started
    
    # Give the scan process time to start
    time.sleep(1)
    
    logger.info(f"Monitor robot thread started - Current DI8 status: {robot.GetDI(8, 0)}")
    
    while not stop_event.is_set():
        # IMPORTANT: Only check DI8 value, not scan_started here
        if robot.GetDI(8, 0) != (0, 0):
            logger.info(f"Stop condition detected: DI8={robot.GetDI(8, 0)}")
            profiler.stop_acquisition()
            profiler.disconnect()
            robot.StopMotion()
            stop_event.set()  # Send stop signal to subprocess
            logger.info("Stop signal sent, subprocess will stop!")
            scan_started = False  # Reset scan_started flag
            break  # Break the loop

        time.sleep(0.5)  # Check every half second
    
    logger.info("Monitor robot waiting for restart signal...")
    
    # Ask user if they want to restart
    start = time.time()
    while True:
        current_di9 = robot.GetDI(9, 0)
        if current_di9 == (0, 1):
            logger.info(f"Restart signal detected: DI9={current_di9}")
            restart_event.set()  # Send restart signal
            break
        elif time.time() - start > 3:
            logger.info("Press start button to restart")
            start = time.time()
    
    logger.info("Monitor robot thread exiting")

# Set up automatic restart capability based on DI9
def auto_restart_monitor():
    global restart_event, stop_event, scan_started, auto_monitor_running
    
    auto_monitor_running = True
    logger.info("Auto-restart monitor started")
    
    while True:
        try:
            # Check DI9 status
            current_di9 = robot.GetDI(9, 0)
            current_di8 = robot.GetDI(8, 0)
            
            # Only start a new scan when:
            # 1. No scan is currently running
            # 2. DI9 is (0,1) (start button pressed)
            # 3. DI8 is (0,0) (safe to start)
            if not scan_started and current_di9 == (0, 1) and current_di8 == (0, 0):
                logger.info(f"Auto-restart triggered by DI9={current_di9}, DI8={current_di8}")
                
                # Create new events
                stop_event = multiprocessing.Event()
                restart_event = multiprocessing.Event()
                
                # Start new scan process
                scan_process_thread = threading.Thread(target=run_scan, args=(stop_event,))
                scan_process_thread.start()
                
                # Start new monitor thread
                monitor_thread = threading.Thread(target=monitor_robot, args=(stop_event, restart_event), daemon=True)
                monitor_thread.start()
                
                scan_started = True
                logger.info("Scan started successfully")
                
                # Give the system time to initialize
                time.sleep(1)
            
            # Check if restart was requested
            if restart_event and restart_event.is_set() and not scan_started:
                logger.info("Processing restart event")
                restart_event.clear()  # Reset event
                
                # Check if conditions are safe to restart
                if current_di8 == (0, 0):
                    logger.info("Conditions are safe for restart")
                    # Create new events
                    stop_event = multiprocessing.Event()
                    
                    # Start new scan process
                    scan_process_thread = threading.Thread(target=run_scan, args=(stop_event,))
                    scan_process_thread.start()
                    
                    # Start new monitor thread
                    monitor_thread = threading.Thread(target=monitor_robot, args=(stop_event, restart_event), daemon=True)
                    monitor_thread.start()
                    
                    scan_started = True
                    logger.info("Scan restarted successfully")
                else:
                    logger.warning(f"Cannot restart: unsafe conditions DI8={current_di8}")
            
            time.sleep(0.5)  # Check every half second
            
        except Exception as e:
            logger.error(f"Error in auto_restart_monitor: {e}")
            time.sleep(1)  # Wait before retrying

@app.route('/api/hello', methods=['GET'])
def hello_world():
    """Simple API endpoint to test if server is running"""
    return jsonify(message="Hello! Greetings from Flask backend!")

@app.route('/api/scan', methods=['POST'])
def scan():
    """API endpoint to control scanning process"""
    global scan_started, scan_process, stop_event, restart_event, monitor_thread, auto_monitor_running
    
    data = request.get_json()
    logger.info(f"Received scan request: {data}")
    
    # Check JSON and 'message' key
    if not data or 'message' not in data:
        return jsonify(message="Invalid request"), 400
    
    # Start scanning
    if data['message'] == 'START':
        # Start auto-restart monitor if not already running
        robot.ResetAllError()
        if not auto_monitor_running:
            auto_thread = threading.Thread(target=auto_restart_monitor, daemon=True)
            auto_thread.start()
            
        # If scan is already running, return appropriate message
        if scan_started:
            return jsonify(message="Scanning already in progress"), 200
        else:
            return jsonify(message="Scanning system ready, press start button on robot"), 200
    
    # Stop scanning
    elif data['message'] == 'STOP':
        if scan_started and stop_event:
            stop_event.set()
            scan_started = False
            return jsonify(message="Scanning stopped"), 200
        else:
            return jsonify(message="No active scanning process found"), 200
    
    # Status check
    elif data['message'] == 'STATUS':
        status = "RUNNING" if scan_started else "STOPPED"
        return jsonify(message=status)
    
    # Force restart
    elif data['message'] == 'RESTART':
        # Force stop any running process
        if scan_started and stop_event:
            stop_event.set()
            scan_started = False
            time.sleep(0.5)  # Give time for process to stop
        
        # Only restart if DI8 is safe
        if robot.GetDI(8, 0) == (0, 0):
            # Create new events
            stop_event = multiprocessing.Event()
            restart_event = multiprocessing.Event()
            
            # Start new scan process
            scan_process_thread = threading.Thread(target=run_scan, args=(stop_event,))
            scan_process_thread.start()
            
            # Start new monitor thread
            monitor_thread = threading.Thread(target=monitor_robot, args=(stop_event, restart_event), daemon=True)
            monitor_thread.start()
            
            scan_started = True
            return jsonify(message="Scanning restarted"), 200
        else:
            return jsonify(message="Cannot restart: unsafe conditions"), 400
    
    return jsonify(message="Unknown command"), 400

@app.route('/api/robot/status', methods=['GET'])
def robot_status():
    global scan_started, scan_process
    """Endpoint to check robot status"""
    di8_status = robot.GetDI(8, 0)[1]
    di9_status = robot.GetDI(9, 0)[1]
    di0_status = robot.GetDI(0, 0)
    
    # Check if scan_process exists and is running before sending data
    if scan_process is not None and scan_process.poll() is None:
        try:
            # Use double quotes for valid JSON and ensure proper formatting
            data_to_send = json.dumps({
                "DI0": [di0_status[0], di0_status[1]]
            }) + "\n"
            scan_process.stdin.write(data_to_send)
            scan_process.stdin.flush()
            print(f"Sent DI0 value: {di0_status}")
        except BrokenPipeError:
            print("Pipe broken, subprocess may have closed")
        except Exception as e:
            logger.error(f"Error sending data to subprocess: {e}")
    
    return jsonify({
        "DI8": di8_status,
        "DI9": di9_status,
        "DI0": di0_status[1],
        "scan_active": scan_started,
        "monitor_active": auto_monitor_running
    })

@app.route('/api/robot/air', methods=['POST'])
def control_air():
    global pressed
    try:
        if pressed:
            robot.SetDO(7, 1)
            pressed = False
        else:
            robot.SetDO(7, 0)
            pressed = True
        return jsonify({"success": True, "message": "Air signal sent successfully"})
    except Exception as e:
        logger.error(f"Error sending air signal: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    # Ensure we start with a clean state
    scan_started = False
    auto_monitor_running = False
    
    # Start the auto-restart monitor
    auto_thread = threading.Thread(target=auto_restart_monitor, daemon=True)
    auto_thread.start()
    
    # Start the Flask server
    app.run(debug=True, port=5000)