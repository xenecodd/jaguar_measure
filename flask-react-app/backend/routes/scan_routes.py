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
from services.scan_service import run_scan, auto_restart_monitor
from MecheyePackage.mecheye_trigger import robot
from services.scan_service import save_to_excel
from services.robot_service import safe_get_di
from services.scan_service import monitor_robot


scan_bp = Blueprint('scan', __name__, url_prefix='/api/scan')

logging.basicConfig(
    level=logging.INFO,
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
        print(ignored_index_list)
        ignored_points_path = os.path.join(BASE_DIR, "..", "MecheyePackage", "config.json")
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

@scan_bp.route('/latest', methods=['GET'])
def get_latest_scan():
    try:
        # Get file name from request parameters, default to scan_output.json
        file_name = request.args.get('file', 'scan_output.json')
        
        # Ensure we only accept specific files for security
        allowed_files = ['scan_output.json', 'firstpart_scan.json','3dprinter_scans.json','first64.json','sec64.json','last16.json']
        if file_name not in allowed_files:
            return jsonify({"message": f"Invalid file requested: {file_name}"}), 400
            
        file_path = os.path.join(Path(__file__).resolve().parent.resolve().parent, 'jsons', file_name)
        if not os.path.exists(file_path):
            return jsonify({"message": f"File {file_name} not found"}), 404

        with open(file_path, 'r') as f:
            lines = f.readlines()
            all_results = [json.loads(line.strip()) for line in lines if line.strip()]
            processed_data = generate_json_data(all_results)
            return jsonify(processed_data), 200
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

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
            save_to_excel(data)

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
        return jsonify({'colors': colors}), 200
    except Exception as e:
        # Gerekirse burada logging de ekleyebilirsiniz
        return jsonify({'error': 'Server error', 'message': str(e)}), 500