"""HTTP transport and lightweight web routes."""

import json
import queue
import time

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    make_response,
    request,
    send_from_directory,
    stream_with_context,
)

from term_mcp_deepseek.demo import DEMO_SCENARIOS
from term_mcp_deepseek.protocol import stamp_modern_result, validate_http_request
from term_mcp_deepseek.receipts import (
    receipt_report,
    receipt_schema,
    redact_receipt_for_sharing,
)
from tools.json_rpc import JSONRPCError, create_jsonrpc_error

bp = Blueprint("api", __name__)


@bp.get("/health")
def health():
    return jsonify(status="ok", version=current_app.extensions["term_mcp"]["version"]), 200


@bp.get("/schemas/receipt-1.0.json")
def receipt_schema_api():
    return jsonify(receipt_schema()), 200


@bp.get("/demo/scenarios")
def demo_scenarios():
    return jsonify(scenarios=DEMO_SCENARIOS), 200


@bp.post("/chat")
def chat():
    data = request.get_json(force=True, silent=True) or {}
    resp = current_app.mcp.handle_chat(data)
    return jsonify(resp), 200


@bp.post("/sessions")
def create_session():
    return jsonify(current_app.mcp.create_session()), 201


@bp.post("/receipts/validate")
def validate_receipt_api():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="receipt_object_required"), 400
    receipt = payload.get("receipt", payload)
    settings = current_app.extensions["term_mcp"]["settings"]
    report = receipt_report(receipt, settings.auth_token)
    return jsonify(report), 200 if report["schema_valid"] else 400


@bp.post("/receipts/redact")
def redact_receipt_api():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="receipt_object_required"), 400
    receipt = payload.get("receipt", payload)
    settings = current_app.extensions["term_mcp"]["settings"]
    try:
        redacted = redact_receipt_for_sharing(receipt, settings.auth_token)
    except ValueError as error:
        return jsonify(error=str(error)), 400
    return jsonify(receipt=redacted), 200


@bp.delete("/sessions/<session_id>")
def close_session(session_id: str):
    return jsonify(current_app.mcp.close_session(session_id)), 200


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
    if not isinstance(payload, dict):
        return jsonify(create_jsonrpc_error(-32600, "Invalid Request")), 400
    try:
        protocol = validate_http_request(
            payload,
            request.headers,
            current_app.extensions["mcp_http_sessions"],
        )
    except JSONRPCError as error:
        return (
            jsonify(create_jsonrpc_error(error.code, error.message, payload.get("id"), error.data)),
            error.http_status,
        )

    response = current_app.jsonrpc.dispatch(payload)
    if protocol.modern:
        response = stamp_modern_result(response)
    if response is None:
        return "", 202

    status = 200
    if "error" in response:
        status = 404 if protocol.modern and response["error"]["code"] == -32601 else 400
    http_response = make_response(jsonify(response), status)
    http_response.headers["MCP-Protocol-Version"] = protocol.version
    if protocol.initialize and "result" in response:
        session = current_app.extensions["mcp_http_sessions"].create(
            response["result"]["protocolVersion"]
        )
        http_response.headers["Mcp-Session-Id"] = session.id
    return http_response


@bp.delete("/mcp")
def terminate_mcp_session():
    session_id = request.headers.get("Mcp-Session-Id", "")
    if not session_id:
        return jsonify(error="missing_mcp_session_id"), 400
    closed = current_app.extensions["mcp_http_sessions"].close(session_id)
    return ("", 200) if closed else (jsonify(error="unknown_mcp_session_id"), 404)


@bp.get("/stream")
def stream():
    session_id = request.args.get("session_id") or "default"
    current_app.mcp.execution.sessions.get(session_id)
    event_bus = current_app.event_bus
    subscriber_id, q = event_bus.subscribe(session_id)

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
            return
        finally:
            event_bus.unsubscribe(session_id, subscriber_id)

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # Nginx
    }
    response = Response(generate(), headers=headers)
    response.call_on_close(lambda: event_bus.unsubscribe(session_id, subscriber_id))
    return response
