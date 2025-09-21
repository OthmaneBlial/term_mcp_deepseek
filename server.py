"""
Main MCP Server Application
Entry point for the terminal MCP server with DeepSeek integration
"""

import os
import logging
import logging.handlers
import asyncio
import requests
from flask import Flask, request, g
import pexpect

from config import config
from mcp_server import MCPServer
from api.routes import APIRoutes
from models.conversation_store import conversation_store
from tools.auth import init_oauth_app, require_auth
from tools.json_rpc import JSONRPCServer
from tools.error_handler import error_handler, MCPError
from tools.rate_limiter import security_middleware, require_security_check

# Setup logging
def setup_logging():
    """Setup comprehensive logging system"""
    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(levelname)s - %(message)s'
    ))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Initialize logging
logger = setup_logging()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# Add security and MCP headers
@app.after_request
def add_security_headers(response):
    """Add security, MCP, and CORS headers to all responses"""
    # MCP headers
    response.headers['Content-Type'] = 'application/json'
    response.headers['X-MCP-Version'] = config.MCP_VERSION
    response.headers['X-MCP-Transport'] = 'http'
    response.headers['Cache-Control'] = 'no-cache'

    # CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'

    # Security headers
    security_headers = security_middleware.get_security_headers()
    for header, value in security_headers.items():
        response.headers[header] = value

    return response

# Apply security checks before processing requests
@app.before_request
def security_check():
    """Apply security checks before processing requests"""
    from flask import request as flask_request

    # Skip security checks for health endpoint and static files
    if hasattr(flask_request, 'endpoint') and flask_request.endpoint in ['health_check', 'serve_chat', 'static']:
        return

    # Apply security middleware
    allowed, reason = security_middleware.check_rate_limits()
    if not allowed:
        security_middleware.log_security_event('rate_limit', {'reason': reason})
        return {'error': reason}, 429

    allowed, reason = security_middleware.check_request_size()
    if not allowed:
        security_middleware.log_security_event('request_size_exceeded', {'reason': reason})
        return {'error': reason}, 413

    allowed, reason = security_middleware.check_suspicious_content()
    if not allowed:
        security_middleware.log_security_event('suspicious_content', {'reason': reason})
        return {'error': reason}, 400

    # Store security info
    g.client_ip = security_middleware.get_client_ip()
    g.security_checks_passed = True

# Handle OPTIONS requests for CORS
@app.route('/mcp/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    response = app.response_class()
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    return response

# Initialize OAuth2
app = init_oauth_app(app)

# Global shell session
shell = pexpect.spawn('/bin/bash', encoding='utf-8', echo=False)

# Initialize MCP server
mcp_server = MCPServer(shell)

# Initialize API routes
api_routes = APIRoutes(app, mcp_server, conversation_store)

# Register error handlers
@app.errorhandler(Exception)
def handle_exception(error):
    return error_handler.handle_flask_error(error)

@app.errorhandler(MCPError)
def handle_mcp_error(error):
    return error_handler.handle_flask_error(error)

#######################################
# Helper Functions
#######################################
async def run_shell_command(cmd: str) -> str:
    """
    2-step approach behind the scenes:
     1) write_to_terminal => run the command
     2) read_terminal_output => retrieve newly produced lines
    Return the actual lines as a string
    """
    from tools.command_executor import CommandExecutor
    from tools.tty_output_reader import TtyOutputReader
    from tools.utils import sleep
    import re

    # We'll do it similarly to the 'call_tool' approach
    executor = CommandExecutor(shell)

    before_buffer = TtyOutputReader.get_buffer()
    before_lines = len(before_buffer.split("\n"))

    # run command
    await executor.execute_command(cmd)

    after_buffer = TtyOutputReader.get_buffer()
    after_lines = len(after_buffer.split("\n"))
    diff = after_lines - before_lines
    # read new lines
    lines_of_output = diff if diff > 0 else 25
    new_output = TtyOutputReader.call(lines_of_output)

    # Attempt to remove a trailing prompt line if present
    last_line = new_output.strip().split("\n")[-1]
    if re.search(r'(\$|%|#)\s*$', last_line):
        # If the last line looks like a prompt, remove it
        splitted = new_output.strip().split("\n")
        splitted.pop()
        new_output = "\n".join(splitted)
    return new_output.strip() or "(No output)"

def call_deepseek_api(messages):
    """
    Sends the conversation to DeepSeek. Returns the model's text.
    For reference:
      POST /chat/completions
      {
        "model": "deepseek-chat",
        "messages": [ {role, content}, ... ],
        "stream": false
      }
    With header "Authorization: Bearer <DEEPSEEK_API_KEY>"
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"
    }
    payload = {
        "model": config.DEEPSEEK_MODEL,
        "messages": messages,
        "stream": False
    }
    resp = requests.post(config.DEEPSEEK_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    # DeepSeek might store the model's text in data["choices"][0]["message"]["content"]
    return data["choices"][0]["message"]["content"]


#######################################
# Helper: run a command behind the scenes
#######################################
async def run_shell_command(cmd: str) -> str:
    """
    2-step approach behind the scenes:
     1) write_to_terminal => run the command
     2) read_terminal_output => retrieve newly produced lines
    Return the actual lines as a string
    """
    # We'll do it similarly to the 'call_tool' approach
    from tools.command_executor import CommandExecutor
    executor = CommandExecutor(shell)

    before_buffer = TtyOutputReader.get_buffer()
    before_lines = len(before_buffer.split("\n"))

    # run command
    await executor.execute_command(cmd)

    after_buffer = TtyOutputReader.get_buffer()
    after_lines = len(after_buffer.split("\n"))
    diff = after_lines - before_lines
    # read new lines
    lines_of_output = diff if diff > 0 else 25
    new_output = TtyOutputReader.call(lines_of_output)

    # Attempt to remove a trailing prompt line if present
    last_line = new_output.strip().split("\n")[-1]
    if re.search(r'(\$|%|#)\s*$', last_line):
        # If the last line looks like a prompt, remove it
        splitted = new_output.strip().split("\n")
        splitted.pop()
        new_output = "\n".join(splitted)
    return new_output.strip() or "(No output)"

#######################################
# DeepSeek Chat
#######################################
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"   # adjust if you have a different model name

def call_deepseek_api(messages):
    """
    Sends the conversation to DeepSeek. Returns the model's text.
    For reference:
      POST /chat/completions
      {
        "model": "deepseek-chat",
        "messages": [ {role, content}, ... ],
        "stream": false
      }
    With header "Authorization: Bearer <DEEPSEEK_API_KEY>"
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "stream": False
    }
    resp = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    # DeepSeek might store the model's text in data["choices"][0]["message"]["content"]
    return data["choices"][0]["message"]["content"]








def cleanup_sessions():
    """Background task to clean up expired sessions"""
    import threading
    import time

    def cleanup_worker():
        while True:
            time.sleep(300)  # Clean up every 5 minutes
            try:
                conversation_store.cleanup_expired_sessions()
                logger.info("Cleaned up expired sessions")
            except Exception as e:
                logger.error(f"Error during session cleanup: {e}")

    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    return cleanup_thread

if __name__ == '__main__':
    logger.info("Starting terminal+DeepSeek MCP server")
    logger.info(f"DeepSeek API Key configured: {'Yes' if config.DEEPSEEK_API_KEY else 'No'}")
    logger.info("MCP methods registered: tools/list, tools/call, prompts/list, prompts/get, resources/list, resources/read, roots/list")
    logger.info("Session management enabled")
    logger.info(f"Server starting on http://{config.HOST}:{config.PORT}")

    print("Starting terminal+DeepSeek server:")
    print("  DEEPSEEK_API_KEY:", "Configured" if config.DEEPSEEK_API_KEY else "Not configured")
    print("  Logs will be written to:", config.LOG_FILE)
    print(f"  Server will run on: http://{config.HOST}:{config.PORT}")
    print("  Session management: Enabled")
    print("  Authentication: OAuth2")

    # Start session cleanup background task
    cleanup_thread = cleanup_sessions()
    logger.info("Session cleanup background task started")

    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
