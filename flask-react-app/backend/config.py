# backend/config.py
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()  # .env dosyasını yükler

BASE_DIR = Path(__file__).resolve().parent

class Config:
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "false").lower() == "false"
    LOG_FILE = str(BASE_DIR / "scan_process.log")
    SCAN_OUTPUTS = str(BASE_DIR / "jsons/scan_output.json")
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 10))
    ROBOT_TIMEOUT = float(os.getenv("ROBOT_TIMEOUT", 2.0))
    SOCKET_PING_INTERVAL = int(os.getenv("SOCKET_PING_INTERVAL", 1))
    SOCKET_PING_TIMEOUT = int(os.getenv("SOCKET_PING_TIMEOUT", 5))
    # Database configuration
    DB_HOST = os.getenv("DB_HOST", "192.168.1.180")
    DB_USER = os.getenv("DB_USER", "cobot_dbuser")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "um6vv$7*sJ@5Q*")
    DB_NAME = os.getenv("DB_NAME", "cobot")
    # SCAN_SCRIPT_PATH; ölçülecek dosyanın yolu:
    SCAN_SCRIPT_PATH = str(BASE_DIR.parent /"backend" / "MecheyePackage" / "scan.py")
    CONFIG_PATH = str(BASE_DIR.parent /"backend" / "MecheyePackage" / "config.json")