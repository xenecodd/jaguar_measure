from flask import Blueprint, jsonify
import logging
health_bp = Blueprint('health', __name__, url_prefix='/api')

@health_bp.route('/hello', methods=['GET'])
def hello_world():
    """Simple endpoint to test if server is running"""
    return jsonify(message="Bağlantı Kuruldu!")