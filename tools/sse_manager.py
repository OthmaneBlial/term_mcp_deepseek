"""
Server-Sent Events Manager
Handles real-time streaming of terminal output to clients
"""

import json
import time
import threading
from typing import Dict, List, Callable, Any
from flask import Response

class SSEManager:
    """Manages Server-Sent Events for real-time communication"""

    def __init__(self):
        self.clients: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def add_client(self, client_id: str, session_id: str = None) -> str:
        """Add a new SSE client"""
        with self._lock:
            client_data = {
                "client_id": client_id,
                "session_id": session_id,
                "connected_at": time.time(),
                "last_ping": time.time(),
                "active": True
            }
            self.clients[client_id] = client_data
            return client_id

    def remove_client(self, client_id: str):
        """Remove an SSE client"""
        with self._lock:
            if client_id in self.clients:
                self.clients[client_id]["active"] = False
                del self.clients[client_id]

    def update_ping(self, client_id: str):
        """Update client's last ping time"""
        with self._lock:
            if client_id in self.clients:
                self.clients[client_id]["last_ping"] = time.time()

    def get_active_clients(self) -> List[str]:
        """Get list of active client IDs"""
        with self._lock:
            return [cid for cid, data in self.clients.items() if data["active"]]

    def send_event(self, client_id: str, event_type: str, data: Any):
        """Send an event to a specific client"""
        with self._lock:
            if client_id in self.clients and self.clients[client_id]["active"]:
                client_data = self.clients[client_id]
                # In a real implementation, this would queue the event
                # For now, we'll just mark it for processing
                client_data["pending_events"] = client_data.get("pending_events", [])
                client_data["pending_events"].append({
                    "type": event_type,
                    "data": data,
                    "timestamp": time.time()
                })

    def broadcast_event(self, event_type: str, data: Any, session_id: str = None):
        """Broadcast event to all clients or clients in a session"""
        with self._lock:
            for client_id, client_data in self.clients.items():
                if client_data["active"]:
                    if session_id is None or client_data.get("session_id") == session_id:
                        self.send_event(client_id, event_type, data)

    def get_pending_events(self, client_id: str) -> List[Dict[str, Any]]:
        """Get pending events for a client"""
        with self._lock:
            if client_id in self.clients:
                return self.clients[client_id].get("pending_events", [])
            return []

    def clear_pending_events(self, client_id: str):
        """Clear pending events for a client"""
        with self._lock:
            if client_id in self.clients:
                self.clients[client_id]["pending_events"] = []

def create_sse_response(client_id: str, sse_manager: SSEManager):
    """Create SSE response for a client"""

    def generate():
        """Generator function for SSE stream"""
        try:
            # Send initial connection event
            yield f"event: connected\ndata: {json.dumps({'client_id': client_id})}\n\n"

            while True:
                # Check for pending events
                events = sse_manager.get_pending_events(client_id)
                if events:
                    for event in events:
                        event_type = event.get("type", "message")
                        event_data = event.get("data", {})
                        timestamp = event.get("timestamp", time.time())

                        yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"

                    # Clear processed events
                    sse_manager.clear_pending_events(client_id)

                # Send ping every 30 seconds
                current_time = time.time()
                if current_time - sse_manager.clients.get(client_id, {}).get("last_ping", 0) > 30:
                    sse_manager.update_ping(client_id)
                    yield f"event: ping\ndata: {json.dumps({'timestamp': current_time})}\n\n"

                time.sleep(0.1)  # Small delay to prevent busy waiting

        except GeneratorExit:
            # Client disconnected
            sse_manager.remove_client(client_id)
        except Exception as e:
            # Send error event
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            sse_manager.remove_client(client_id)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )

# Global SSE manager instance
sse_manager = SSEManager()