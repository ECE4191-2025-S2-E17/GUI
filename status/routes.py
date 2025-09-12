from flask import Blueprint, Response
import json
import time
from .status_manager import status_manager
from queue import Queue, Empty
import threading

status_bp = Blueprint("status", __name__, url_prefix="/status")

# Store active SSE connections
sse_clients = []
sse_lock = threading.Lock()


class SSEClient:
    def __init__(self):
        self.queue = Queue()
        self.is_active = True
    
    def send_update(self, data):
        if self.is_active:
            try:
                self.queue.put_nowait(data)
            except:
                self.is_active = False


def broadcast_to_clients(status_data):
    """Broadcast status update to all connected SSE clients"""
    with sse_lock:
        inactive_clients = []
        for client in sse_clients:
            if client.is_active:
                client.send_update(status_data)
            else:
                inactive_clients.append(client)
        
        # Remove inactive clients
        for client in inactive_clients:
            sse_clients.remove(client)


# Subscribe to status changes
status_manager.subscribe(broadcast_to_clients)


@status_bp.route("/stream")
def status_stream():
    """Server-Sent Events endpoint for real-time status updates"""
    
    def event_stream():
        client = SSEClient()
        
        with sse_lock:
            sse_clients.append(client)
        
        try:
            # Send initial status
            initial_status = status_manager.get_status()
            yield f"data: {json.dumps(initial_status)}\n\n"
            
            # Send updates as they come
            while client.is_active:
                try:
                    data = client.queue.get(timeout=30)  # 30 second timeout for keepalive
                    yield f"data: {json.dumps(data)}\n\n"
                except Empty:
                    # Send keepalive
                    yield f"data: {json.dumps({'keepalive': True})}\n\n"
                except:
                    break
        finally:
            client.is_active = False
            with sse_lock:
                if client in sse_clients:
                    sse_clients.remove(client)
    
    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'X-Accel-Buffering': 'no'  # Disable nginx buffering
        }
    )


@status_bp.route("/current")
def get_current_status():
    """Get current status as JSON"""
    return json.dumps(status_manager.get_status())
