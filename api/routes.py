# routes.py
from flask import Blueprint, jsonify, request, current_app, abort
from tools.auth import require_token  # new decorator below

bp = Blueprint("api", __name__)

@bp.get("/health")
def health():
    return jsonify(status="ok"), 200

@bp.post("/chat")
# @require_token(optional=False)  # Disabled for demo - add back for production
def chat():
    data = request.get_json(force=True, silent=True) or {}
    # call into mcp_server.py
    resp = current_app.mcp.handle_chat(data)
    return jsonify(resp), 200

@bp.get("/")
def root():
    from flask import send_from_directory
    return send_from_directory("static", "chat.html")

@bp.get("/mcp/info")
def mcp_info():
    return jsonify(current_app.mcp.get_info()), 200

@bp.get("/stream")
# @require_token(optional=False)  # Disabled for demo - add back for production
def stream():
    from flask import Response, stream_with_context, request, current_app
    import json, time

    session_id = request.args.get("session_id") or "default"
    q = current_app.event_bus.get(session_id)

    def _sse(data: dict, event: str | None = None):
        # format: optional "event:" then "data:"; blank line to end
        lines = []
        if event: lines.append(f"event: {event}")
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
                except Exception:
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