from flask import Blueprint, current_app
from drive.controllers import WebSocketDriveController
import atexit

# Create the blueprint with URL prefix
drive_bp = Blueprint("drive", __name__, url_prefix="/drive")

WS_URL = current_app.config["DRIVE_WS_URL"]
if not WS_URL:
    raise ValueError("DRIVE_WS_URL is not set in app config")

drive_controller = WebSocketDriveController(WS_URL)

atexit.register(drive_controller.disconnect)

# Import routes to register them with the blueprint
from drive import routes
