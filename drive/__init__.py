from flask import Blueprint


DRIVE_URL = "http://192.168.107.98:84/drive"
MAX_SPEED = 100
MIN_SPEED = 0

# Create the blueprint with URL prefix
drive_bp = Blueprint("drive", __name__, url_prefix="/drive")


# Import routes to register them with the blueprint
from drive import routes
