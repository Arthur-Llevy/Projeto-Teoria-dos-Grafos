from flask import Blueprint, jsonify
from datetime import datetime

health_bp = Blueprint("health", __name__, url_prefix="/health")

@health_bp.route("/", methods=["GET"])
def health_check():
    now = datetime.now() 
    return jsonify({
        "status": "ok",
        "timestamp": now.isoformat(), 
        "message": "Application is running"
    })