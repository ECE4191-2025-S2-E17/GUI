from drive import DRIVE_URL, drive_bp, MAX_SPEED, MIN_SPEED
from status import status_manager
import requests

turn_speed = 50
wheel_speed = 100


def send_command(lwheel_speed, rwheel_speed):
    return requests.get(
        f"{DRIVE_URL}/drive",
        params={"lw": lwheel_speed, "rw": rwheel_speed},
        timeout=0.1,
    )


@drive_bp.route("/stop", methods=["GET"])
def stop_motors():
    send_command(0, 0)
    return "OK"


@drive_bp.route("/forward", methods=["GET"])
def forward():
    send_command(wheel_speed, wheel_speed)
    return "OK"


@drive_bp.route("/backward", methods=["GET"])
def backward():
    send_command(-wheel_speed, -wheel_speed)
    return "OK"


@drive_bp.route("/left", methods=["GET"])
def left():
    send_command(-turn_speed, turn_speed)
    return "OK"


@drive_bp.route("/right", methods=["GET"])
def right():
    send_command(turn_speed, -turn_speed)
    return "OK"


@drive_bp.route("/faster", methods=["GET"])
def faster():
    global wheel_speed
    wheel_speed = min(MAX_SPEED, wheel_speed + 10)
    status_manager.update_status(wheel_speed=wheel_speed)
    return "OK"


@drive_bp.route("/slower", methods=["GET"])
def slower():
    global wheel_speed
    wheel_speed = max(MIN_SPEED, wheel_speed - 10)
    status_manager.update_status(wheel_speed=wheel_speed)
    return "OK"


@drive_bp.route("/turn_faster", methods=["GET"])
def turn_faster():
    global turn_speed
    turn_speed = min(MAX_SPEED, turn_speed + 10)
    status_manager.update_status(turn_speed=turn_speed)
    return "OK"


@drive_bp.route("/turn_slower", methods=["GET"])
def turn_slower():
    global turn_speed
    turn_speed = max(MIN_SPEED, turn_speed - 10)
    status_manager.update_status(turn_speed=turn_speed)
    return "OK"
