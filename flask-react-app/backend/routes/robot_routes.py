from flask import Blueprint, jsonify
from models.robot_state import state
from MecheyePackage.mecheye_trigger import robot

robot_bp = Blueprint('robot', __name__, url_prefix='/api/robot')

@robot_bp.route('/air', methods=['GET'])
def control_air():
    try:
        robot.SetDO(7, 0)
        state.pressed = True
        return jsonify({"success": True, "message": "Air signal sent successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
