from flask import Blueprint, jsonify, request, send_file
import os
import json

from pathlib import Path
import logging
from models.robot_state import state
from services.scan_service import generate_json_data
from config import BASE_DIR, Config
import threading
import multiprocessing
import time
from services.scan_service import save_to_excel, get_available_files_from_directory, format_filename_to_label, run_scan, auto_restart_monitor, monitor_robot
from services.robot_service import safe_get_di, read_current_point_index, write_current_point_index
from MecheyePackage.mecheye_trigger import TriggerWithExternalDeviceAndFixedRate
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from services.scan_db_service import ScanDatabaseService

mech_eye = TriggerWithExternalDeviceAndFixedRate(vel_mul=1)
robot = mech_eye.robot

db_service = ScanDatabaseService()

scan_bp = Blueprint('scan', __name__, url_prefix='/api/scan')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE, encoding='utf-8', errors='replace'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
# Disable logging for /api/robot/status endpoint
logging.getLogger('werkzeug').setLevel(logging.ERROR)


@scan_bp.route('', methods=['POST'])
def scan():
    """API endpoint to control scanning process"""
    data = request.get_json()
    logger.info(f"Received scan request: {data}")
    
    # Validate request
    if not data:
        return jsonify(message="Invalid request"), 400

    if data.get('ignored_index_list') is not None:
        ignored_index_list = data['ignored_index_list']
        ignored_points_path = os.path.join(BASE_DIR,"MecheyePackage", "config.json")
        ignored_points_path = os.path.normpath(ignored_points_path)
        # Read the current config
        with open(ignored_points_path, "r") as f:
            config_data = json.load(f)
        # Update only ignored_points
        config_data["ignored_points"] = ignored_index_list
        # Save back the entire config
        with open(ignored_points_path, "w") as f:
            json.dump(config_data, f, indent=2)
        return jsonify(message="ignored_points updated"), 200
       
    else:
        # Process based on message type
        if data['message'] == 'START':
            # Reset any errors
            robot.ResetAllError()
            print("data:",data)
            if data['alt_button'] == True:
                state.alt_button_pressed = True
            # Start auto-restart monitor if not already running
            if not state.auto_monitor_running:
                auto_thread = threading.Thread(target=auto_restart_monitor, daemon=True)
                auto_thread.start()
                return jsonify(message="Scanning system ready, press start button on robot"), 200
            else:
                return jsonify(message="Scanning already in progress"), 200
        
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
        
        elif data['message'] == 'RESTART' or data['message'] == 'FORCE_RESTART':
            logger.error("Received restart command")
            # Force stop any running process
            if state.scan_started and state.stop_event:
                state.stop_event.set()
                state.set_scan_started(False)
                time.sleep(0.5)  # Give time for process to stop
            
            # Only restart if DI8 is safe
            if safe_get_di(98) == (0, 0) or data["FORCE_RESTART"]:
                logger.error("Restarting scan process")
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

@scan_bp.route('/history', methods=['GET'])
def get_scan_history():
    """Get historical scan data from database"""
    try:
        # Get date parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Default to last 7 days if no dates provided
        if not start_date or not end_date:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
        else:
            # Convert string dates to date objects
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get data from database
        raw_data = db_service.get_scan_data_by_date_range(start_date, end_date)
        
        if not raw_data:
            return jsonify({
                "message": "No data found for the specified date range",
                "data": [],
                "date_range": {
                    "start": start_date.strftime('%Y-%m-%d'),
                    "end": end_date.strftime('%Y-%m-%d')
                }
            }), 200
        
        # Process data using existing generate_json_data function
        processed_data = generate_json_data(raw_data)
        
        # Add metadata
        processed_data['data_source'] = 'database'
        processed_data['date_range'] = {
            "start": start_date.strftime('%Y-%m-%d'),
            "end": end_date.strftime('%Y-%m-%d')
        }
        
        return jsonify(processed_data), 200
        
    except ValueError as e:
        return jsonify({
            "message": f"Invalid date format. Use YYYY-MM-DD format. Error: {str(e)}"
        }), 400
    except Exception as e:
        return jsonify({
            "message": f"Error retrieving historical data: {str(e)}"
        }), 500

@scan_bp.route('/dates', methods=['GET'])
def get_available_dates():
    """Get list of available dates in database"""
    try:
        dates = db_service.get_available_dates()
        
        return jsonify({
            "available_dates": dates,
            "total_dates": len(dates)
        }), 200
        
    except Exception as e:
        return jsonify({
            "message": f"Error retrieving available dates: {str(e)}"
        }), 500

@scan_bp.route('/latest', methods=['GET'])
def get_latest_scan():
    try:
        # Get file name from request parameters, default to scan_output.json
        file_name = request.args.get('file', 'scan_output.json')
        
        # Get available files dynamically
        available_files = get_available_files_from_directory()
        
        file_path = os.path.join(Path(__file__).resolve().parent.resolve().parent, 'jsons', file_name)
        if not os.path.exists(file_path):
            return jsonify({
                "message": f"File {file_name} not found",
                "available_files": available_files
            }), 404

        with open(file_path, 'r') as f:
            lines = f.readlines()
            all_results = [json.loads(line.strip()) for line in lines if line.strip()]
            processed_data = generate_json_data(all_results)
            
            # Add metadata to distinguish from database data
            processed_data['data_source'] = 'json_file'
            processed_data['file_name'] = file_name
            processed_data['available_files'] = available_files
            
            return jsonify(processed_data), 200
            
    except Exception as e:
        # Even in error case, try to return available files
        try:
            available_files = get_available_files_from_directory()
        except:
            available_files = []
            
        return jsonify({
            "message": f"Error: {str(e)}",
            "available_files": available_files
        }), 500
    
@scan_bp.route('/download-excel', methods=['GET'])
def download_excel():
    try:
        file_name = request.args.get('file', 'scan_output.json')
        allowed_files = ['scan_output.json', 'firstpart_scan.json', '3dprinter_scans.json', 'first64.json', 'sec64.json','last16.json']
        
        if file_name not in allowed_files:
            return jsonify({"message": f"Invalid file requested: {file_name}"}), 400

        file_path = Path(__file__).resolve().parent.parent / 'jsons' / file_name
        if not os.path.exists(file_path):
            return jsonify({"message": f"File {file_name} not found"}), 404
        
        with open(file_path, 'r') as f:
            data = [json.loads(line) for line in f if line.strip()]

        latest_results_by_index = {}
        for result in data:
            idx = result.get("Index")
            latest_results_by_index[idx] = result

        filtered_sorted_data = sorted(
            [r for r in latest_results_by_index.values() if r.get("Index") is not None],
            key=lambda r: r["Index"]
        )
        save_to_excel(filtered_sorted_data)

        excel_file_path = Path(__file__).resolve().parent.parent / 'excel' / 'scan_results.xlsx'
        return send_file(excel_file_path,
                         as_attachment=True,
                         download_name='scan_results.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@scan_bp.route('/log', methods=['GET'])
def get_scan_log():
    try:
        with open('scan_process.log', 'r') as file:
            logs = file.readlines()
        return jsonify({'logs': logs}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scan_bp.route('/config', methods=['GET', 'POST'])
def update_config():
    try:
        if request.method == 'POST':
            if not request.is_json:
                return jsonify({
                    'error': 'Unsupported Media Type',
                    'message': "Lütfen Content-Type header'ını 'application/json' olarak ayarlayın."
                }), 415

            data = request.get_json()
            with open(Config.CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            return jsonify({'message': 'Configuration updated successfully'}), 200

        elif request.method == 'GET':
            with open(Config.CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify(data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scan_bp.route('/index/set', methods=['GET','POST'])
def set_current_point_index():
    try:
        data = request.get_json()
        index = int(data["index"])
        logger.info(f"Setting current point index to: {index}")
        
        if index is None:
            return jsonify({'error': 'Invalid index'}), 400
        
        write_current_point_index(index)
        logger.info(f"Current point index set to {index}")
        
        return jsonify({'message': f'Current point index set to {index} successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': 'Server error', 'message': str(e)}), 500
    
@scan_bp.route('/colors', methods=['GET'])
def get_colors():
    try:
        with open(Config.CONFIG_PATH, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        ignored = set(config_data.get("ignored_points", []))
        colors = ["black" if i in ignored else "gray" for i in range(64)]
        scan_outputs = []
        with open(Config.SCAN_OUTPUTS, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and line != '{}' and "Error" not in line:
                    scan_outputs.append(json.loads(line))
        for o in scan_outputs:
            idx = o.get("Index")
            if idx is not None and (idx) not in ignored:
                colors[idx] = "green" if o.get("OK") == "1" else "red"
        idx = read_current_point_index()
        colors[idx] = "yellow"
        
        return jsonify({'colors': colors}), 200
    
    except Exception as e:
        return jsonify({'error': 'Server error', 'message': str(e)}), 500