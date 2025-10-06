from flask import jsonify
from drive import drive_bp, drive_controller



# Flask Routes for Drive Control
@drive_bp.route("/connect", methods=["POST"])
def connect_drive():
    """Connect to drive controller"""
    if drive_controller:
        drive_controller.connect()
        return jsonify({"status": "connecting", "url": drive_controller.ws_url})
    return jsonify({"error": "Drive controller not initialized"}), 500


@drive_bp.route("/disconnect", methods=["POST"])
def disconnect_drive():
    """Disconnect from drive controller"""
    if drive_controller:
        drive_controller.disconnect()
        return jsonify({"status": "disconnected"})
    return jsonify({"error": "Drive controller not initialized"}), 500


@drive_bp.route("/status", methods=["GET"])
def get_drive_status():
    """Get drive controller connection status"""
    if drive_controller:
        return jsonify(
            {
                "connected": drive_controller.is_connected(),
                "left_speed": drive_controller.left_wheel_speed,
                "right_speed": drive_controller.right_wheel_speed,
            }
        )
    return jsonify({"error": "Drive controller not initialized"}), 500


# Wheel Control
@drive_bp.route("/wheels/<int:left_speed>/<int:right_speed>", methods=["POST"])
def drive_wheels(left_speed, right_speed):
    """Drive wheels with specific speeds"""
    if drive_controller and drive_controller.send_command(
        f"LW:{left_speed},RW:{right_speed}"
    ):
        status_manager.update_status(wheel_speed=max(abs(left_speed), abs(right_speed)))
        return jsonify({"status": "success", "left": left_speed, "right": right_speed})
    return jsonify({"error": "Failed to send command"}), 500


@drive_bp.route("/forward", methods=["POST", "GET"])
def forward():
    """Move forward"""
    if drive_controller:
        speed = 50  # Default forward speed
        if drive_controller.driveWheels(speed, speed):
            return jsonify({"status": "moving forward", "speed": speed})
    return jsonify({"error": "Failed to move forward"}), 500


@drive_bp.route("/backward", methods=["POST", "GET"])
def backward():
    """Move backward"""
    if drive_controller:
        speed = -50  # Negative for backward
        if drive_controller.driveWheels(speed, speed):
            return jsonify({"status": "moving backward", "speed": abs(speed)})
    return jsonify({"error": "Failed to move backward"}), 500


@drive_bp.route("/left", methods=["POST", "GET"])
def left():
    """Turn left"""
    if drive_controller:
        if drive_controller.driveWheels(-30, 30):  # Left wheel slower/reverse
            return jsonify({"status": "turning left"})
    return jsonify({"error": "Failed to turn left"}), 500


@drive_bp.route("/right", methods=["POST", "GET"])
def right():
    """Turn right"""
    if drive_controller:
        if drive_controller.driveWheels(30, -30):  # Right wheel slower/reverse
            return jsonify({"status": "turning right"})
    return jsonify({"error": "Failed to turn right"}), 500


@drive_bp.route("/stop", methods=["POST", "GET"])
def stop():
    """Stop all movement"""
    if drive_controller:
        if drive_controller.driveWheels(0, 0):
            return jsonify({"status": "stopped"})
    return jsonify({"error": "Failed to stop"}), 500


@drive_bp.route("/stopall", methods=["POST", "GET"])
def stop_all():
    """Stop all systems"""
    if drive_controller:
        if drive_controller.stop_all():
            return jsonify({"status": "all systems stopped"})
    return jsonify({"error": "Failed to stop all systems"}), 500


# Gimbal Control
@drive_bp.route("/gimbal/pan/left", methods=["POST"])
def gimbal_pan_left():
    """Pan gimbal left"""
    if drive_controller and drive_controller.driveGimbalPan(DriveDirection.FORWARD):
        return jsonify({"status": "panning left"})
    return jsonify({"error": "Failed to pan left"}), 500


@drive_bp.route("/gimbal/pan/right", methods=["POST"])
def gimbal_pan_right():
    """Pan gimbal right"""
    if drive_controller and drive_controller.driveGimbalPan(DriveDirection.BACKWARD):
        return jsonify({"status": "panning right"})
    return jsonify({"error": "Failed to pan right"}), 500


@drive_bp.route("/gimbal/pan/stop", methods=["POST"])
def gimbal_pan_stop():
    """Stop gimbal pan"""
    if drive_controller and drive_controller.driveGimbalPan(DriveDirection.STOP):
        return jsonify({"status": "pan stopped"})
    return jsonify({"error": "Failed to stop pan"}), 500


@drive_bp.route("/gimbal/tilt/up", methods=["POST"])
def gimbal_tilt_up():
    """Tilt gimbal up"""
    if drive_controller and drive_controller.driveGimbalTilt(DriveDirection.FORWARD):
        return jsonify({"status": "tilting up"})
    return jsonify({"error": "Failed to tilt up"}), 500


@drive_bp.route("/gimbal/tilt/down", methods=["POST"])
def gimbal_tilt_down():
    """Tilt gimbal down"""
    if drive_controller and drive_controller.driveGimbalTilt(DriveDirection.BACKWARD):
        return jsonify({"status": "tilting down"})
    return jsonify({"error": "Failed to tilt down"}), 500


@drive_bp.route("/gimbal/tilt/stop", methods=["POST"])
def gimbal_tilt_stop():
    """Stop gimbal tilt"""
    if drive_controller and drive_controller.driveGimbalTilt(DriveDirection.STOP):
        return jsonify({"status": "tilt stopped"})
    return jsonify({"error": "Failed to stop tilt"}), 500


# Suspension Control
@drive_bp.route("/suspension/up", methods=["POST"])
def suspension_up():
    """Raise suspension"""
    if drive_controller and drive_controller.driveSuspension(DriveDirection.FORWARD):
        return jsonify({"status": "raising suspension"})
    return jsonify({"error": "Failed to raise suspension"}), 500


@drive_bp.route("/suspension/down", methods=["POST"])
def suspension_down():
    """Lower suspension"""
    if drive_controller and drive_controller.driveSuspension(DriveDirection.BACKWARD):
        return jsonify({"status": "lowering suspension"})
    return jsonify({"error": "Failed to lower suspension"}), 500


@drive_bp.route("/suspension/stop", methods=["POST"])
def suspension_stop():
    """Stop suspension movement"""
    if drive_controller and drive_controller.driveSuspension(DriveDirection.STOP):
        return jsonify({"status": "suspension stopped"})
    return jsonify({"error": "Failed to stop suspension"}), 500
