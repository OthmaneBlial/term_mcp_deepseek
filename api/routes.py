"""HTTP transport and lightweight web routes."""

import json
import queue
import time

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    request,
    send_from_directory,
    stream_with_context,
)

bp = Blueprint("api", __name__)


@bp.get("/health")
def health():
    return jsonify(status="ok", version=current_app.extensions["term_mcp"]["version"]), 200


@bp.post("/chat")
def chat():
    data = request.get_json(force=True, silent=True) or {}
    resp = current_app.mcp.handle_chat(data)
    return jsonify(resp), 200


@bp.get("/")
def root():
    return send_from_directory(current_app.static_folder, "chat.html")


@bp.get("/mcp/info")
def mcp_info():
    return jsonify(current_app.mcp.get_info()), 200


@bp.post("/mcp")
def mcp_rpc():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify(
            jsonrpc="2.0",
            error={"code": -32700, "message": "Parse error"},
            id=None,
        ), 400
    response = current_app.jsonrpc.dispatch(payload)
    if response is None:
        return "", 204
    status = 200 if "result" in response else 400
    return jsonify(response), status


@bp.get("/stream")
def stream():
    session_id = request.args.get("session_id") or "default"
    q = current_app.event_bus.get(session_id)

    def _sse(data: dict, event: str | None = None):
        # format: optional "event:" then "data:"; blank line to end
        lines = []
        if event:
            lines.append(f"event: {event}")
        lines.append("data: " + json.dumps(data, ensure_ascii=False))
        lines.append("")  # terminator
        return "\n".join(lines) + "\n"

    @stream_with_context
    def generate():
        # initial hello
        yield _sse({"ok": True, "session": session_id}, event="hello")
        last_beat = time.time()
        try:
            while True:
                try:
                    item = q.get(timeout=10)
                    yield _sse(item, event=item.get("type"))
                except queue.Empty:
                    # heartbeat every 15s to keep proxies alive
                    now = time.time()
                    if now - last_beat >= 15:
                        last_beat = now
                        yield _sse({"ts": int(now)}, event="ping")
        except GeneratorExit:
            # client disconnected
            return

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Nginx
    }
    return Response(generate(), headers=headers)
