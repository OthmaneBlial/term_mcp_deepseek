"""
Comprehensive Error Handling System
Provides structured error handling, logging, and recovery mechanisms
"""

import logging
import traceback
from typing import Dict, Any, Optional
from flask import jsonify
from tools.json_rpc import JSONRPCError

logger = logging.getLogger("error_handler")

class MCPError(Exception):
    """Base exception class for MCP errors"""

    def __init__(self, message: str, code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

class ValidationError(MCPError):
    """Validation error"""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, 400, {"field": field} if field else {})

class AuthenticationError(MCPError):
    """Authentication error"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, 401)

class AuthorizationError(MCPError):
    """Authorization error"""
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, 403)

class ResourceNotFoundError(MCPError):
    """Resource not found error"""
    def __init__(self, resource: str, resource_id: Optional[str] = None):
        details = {"resource": resource}
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(f"{resource} not found", 404, details)

class CommandExecutionError(MCPError):
    """Command execution error"""
    def __init__(self, command: str, error: str):
        super().__init__(f"Command execution failed: {command}", 500, {
            "command": command,
            "error": error
        })

class SessionError(MCPError):
    """Session management error"""
    def __init__(self, message: str, session_id: Optional[str] = None):
        details = {}
        if session_id:
            details["session_id"] = session_id
        super().__init__(message, 400, details)

class APIError(MCPError):
    """API error"""
    def __init__(self, message: str, endpoint: Optional[str] = None):
        details = {}
        if endpoint:
            details["endpoint"] = endpoint
        super().__init__(message, 500, details)

class ErrorHandler:
    """Centralized error handling"""

    @staticmethod
    def handle_flask_error(error: Exception) -> tuple:
        """Handle Flask application errors"""
        logger.error(f"Flask error: {error}")
        logger.error(traceback.format_exc())

        if isinstance(error, MCPError):
            return ErrorHandler._format_mcp_error(error)

        # Handle common Flask/Werkzeug errors
        if hasattr(error, 'code'):
            if error.code == 400:
                return jsonify({
                    "error": "Bad Request",
                    "message": "Invalid request format"
                }), 400
            elif error.code == 404:
                return jsonify({
                    "error": "Not Found",
                    "message": "Endpoint not found"
                }), 404
            elif error.code == 405:
                return jsonify({
                    "error": "Method Not Allowed",
                    "message": "HTTP method not supported"
                }), 405

        # Generic server error
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }), 500

    @staticmethod
    def handle_jsonrpc_error(error: Exception) -> Dict[str, Any]:
        """Handle JSON-RPC specific errors"""
        logger.error(f"JSON-RPC error: {error}")
        logger.error(traceback.format_exc())

        if isinstance(error, MCPError):
            return ErrorHandler._format_jsonrpc_error(error)

        # Generic JSON-RPC error
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(error)
            },
            "id": None
        }

    @staticmethod
    def handle_async_error(error: Exception, context: str = "") -> None:
        """Handle errors in async operations"""
        logger.error(f"Async error in {context}: {error}")
        logger.error(traceback.format_exc())

    @staticmethod
    def handle_command_error(command: str, error: Exception) -> CommandExecutionError:
        """Handle command execution errors"""
        logger.error(f"Command execution failed: {command}")
        logger.error(f"Error details: {error}")
        logger.error(traceback.format_exc())

        return CommandExecutionError(command, str(error))

    @staticmethod
    def handle_validation_error(field: str, value: Any, reason: str) -> ValidationError:
        """Handle validation errors"""
        logger.warning(f"Validation failed for field '{field}': {reason}")
        return ValidationError(f"Invalid {field}: {reason}", field)

    @staticmethod
    def handle_auth_error(message: str, user_id: Optional[str] = None) -> AuthenticationError:
        """Handle authentication errors"""
        details = f" for user {user_id}" if user_id else ""
        logger.warning(f"Authentication error{details}: {message}")
        return AuthenticationError(message)

    @staticmethod
    def _format_mcp_error(error: MCPError) -> tuple:
        """Format MCP error for HTTP response"""
        response = {
            "error": error.__class__.__name__,
            "message": error.message
        }

        if error.details:
            response["details"] = error.details

        return jsonify(response), error.code

    @staticmethod
    def _format_jsonrpc_error(error: MCPError) -> Dict[str, Any]:
        """Format MCP error for JSON-RPC response"""
        jsonrpc_error = {
            "code": error.code,
            "message": error.message
        }

        if error.details:
            jsonrpc_error["data"] = error.details

        return {
            "jsonrpc": "2.0",
            "error": jsonrpc_error,
            "id": None
        }

    @staticmethod
    def log_operation(operation: str, success: bool, details: Optional[Dict[str, Any]] = None):
        """Log operation results"""
        if success:
            logger.info(f"Operation '{operation}' completed successfully")
            if details:
                logger.debug(f"Operation details: {details}")
        else:
            logger.error(f"Operation '{operation}' failed")
            if details:
                logger.error(f"Failure details: {details}")

class ErrorRecovery:
    """Error recovery mechanisms"""

    @staticmethod
    def attempt_recovery(operation: callable, max_attempts: int = 3, *args, **kwargs):
        """Attempt operation with retry logic"""
        last_error = None

        for attempt in range(max_attempts):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    import time
                    time.sleep(0.5 * (2 ** attempt))  # Exponential backoff

        logger.error(f"All {max_attempts} attempts failed")
        raise last_error

    @staticmethod
    def graceful_degradation(operation: callable, fallback: callable, *args, **kwargs):
        """Attempt operation with fallback"""
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Operation failed, using fallback: {e}")
            return fallback(*args, **kwargs)

# Global error handler instance
error_handler = ErrorHandler()