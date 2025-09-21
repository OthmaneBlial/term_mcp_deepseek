"""
Input Validation and Sanitization
Provides security validation for user inputs and command execution
"""

import re
import os
from typing import Optional, List, Dict, Any
from config import Config
config = Config()

class InputValidator:
    """Comprehensive input validation and sanitization"""

    # Dangerous commands and patterns
    DANGEROUS_COMMANDS = [
        'rm -rf /',
        'rm -rf /*',
        'rm -rf ~',
        'rm -rf .*',
        'dd if=',
        'mkfs',
        'fdisk',
        'format',
        'shutdown',
        'reboot',
        'halt',
        'poweroff',
        'systemctl stop',
        'service stop',
        'killall',
        'pkill -9',
        'chmod 777',
        'chown root',
        'su root',
        'sudo',
        'passwd',
        'usermod',
        'userdel',
        'groupmod',
        'mount',
        'umount',
        'fsck',
        'e2fsck'
    ]

    # Dangerous patterns (regex)
    DANGEROUS_PATTERNS = [
        r'rm\s+-rf\s+/?',  # rm -rf / or rm -rf /*
        r'rm\s+-rf\s+\*',  # rm -rf *
        r'rm\s+-rf\s+\.\*',  # rm -rf .*
        r'>\s*/dev/',  # redirect to device files
        r'\|.*sh\s*$',  # pipe to shell
        r';\s*rm\s+',  # command injection with rm
        r'`.*rm.*`',  # command substitution with rm
        r'\$\(.*rm.*\)',  # command substitution with rm
        r'curl.*\|\s*sh',  # curl pipe sh
        r'wget.*\|\s*sh',  # wget pipe sh
    ]

    @staticmethod
    def sanitize_command(command: str) -> str:
        """Sanitize a shell command"""
        if not command or not isinstance(command, str):
            raise ValueError("Command must be a non-empty string")

        # Remove leading/trailing whitespace
        command = command.strip()

        # Check length
        if len(command) > config.MAX_COMMAND_LENGTH:
            raise ValueError(f"Command too long (max {config.MAX_COMMAND_LENGTH} characters)")

        # Check for dangerous commands
        if InputValidator._is_dangerous_command(command):
            raise ValueError("Command contains potentially dangerous operations")

        # Basic sanitization - remove suspicious characters
        # Allow: alphanumeric, spaces, common symbols (-_./:), quotes
        if not re.match(r'^[a-zA-Z0-9\s\-_\./:\'\"]+$', command):
            # More permissive pattern for complex commands
            if not re.match(r'^[a-zA-Z0-9\s\-_\./:\'\"\|\&\;\<\>\(\)\[\]\{\}\?\*\+\^\$\@\#\%\=\!]+$', command):
                raise ValueError("Command contains invalid characters")

        return command

    @staticmethod
    def _is_dangerous_command(command: str) -> bool:
        """Check if command contains dangerous operations"""
        command_lower = command.lower()

        # Check exact dangerous commands
        for dangerous in InputValidator.DANGEROUS_COMMANDS:
            if dangerous in command_lower:
                return True

        # Check dangerous patterns
        for pattern in InputValidator.DANGEROUS_PATTERNS:
            if re.search(pattern, command_lower):
                return True

        return False

    @staticmethod
    def validate_json_input(data: Any) -> Dict[str, Any]:
        """Validate JSON input data"""
        if not isinstance(data, dict):
            raise ValueError("Input must be a JSON object")

        # Check for required fields based on common patterns
        return data

    @staticmethod
    def sanitize_file_path(file_path: str) -> str:
        """Sanitize file paths to prevent directory traversal"""
        if not file_path or not isinstance(file_path, str):
            raise ValueError("File path must be a non-empty string")

        # Remove dangerous path components
        if '..' in file_path:
            raise ValueError("Path traversal not allowed (..)")

        if file_path.startswith('/'):
            raise ValueError("Absolute paths not allowed")

        # Basic sanitization
        file_path = file_path.strip()

        # Remove leading/trailing slashes
        file_path = file_path.strip('/')

        # Check for suspicious characters
        if any(char in file_path for char in ['<', '>', '|', '&', ';', '`', '$', '(', ')']):
            raise ValueError("File path contains invalid characters")

        return file_path

    @staticmethod
    def validate_message(message: str) -> str:
        """Validate chat messages"""
        if not message or not isinstance(message, str):
            raise ValueError("Message must be a non-empty string")

        message = message.strip()

        # Check length (reasonable limit for chat messages)
        if len(message) > 10000:  # 10KB limit
            raise ValueError("Message too long (max 10000 characters)")

        # Basic content validation - allow common characters
        # This is permissive to allow various languages and symbols
        if not re.match(r'^[\w\s\.,!?\-_\'\"@#$%^&*()+=[\]{}|\\:;/<>~`]*$', message, re.UNICODE):
            # Allow newlines and tabs
            if not re.match(r'^[\w\s\.,!?\-_\'\"@#$%^&*()+=[\]{}|\\:;/<>~`\n\t\r]*$', message, re.UNICODE):
                raise ValueError("Message contains invalid characters")

        return message

    @staticmethod
    def validate_session_id(session_id: str) -> str:
        """Validate session ID format"""
        if not session_id or not isinstance(session_id, str):
            raise ValueError("Session ID must be a non-empty string")

        # Session IDs should be URL-safe and reasonable length
        if len(session_id) < 10 or len(session_id) > 100:
            raise ValueError("Session ID length invalid")

        # Allow URL-safe characters
        if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
            raise ValueError("Session ID contains invalid characters")

        return session_id

    @staticmethod
    def validate_user_id(user_id: str) -> str:
        """Validate user ID format"""
        if not user_id or not isinstance(user_id, str):
            raise ValueError("User ID must be a non-empty string")

        user_id = user_id.strip()

        if len(user_id) > 100:
            raise ValueError("User ID too long")

        # Allow alphanumeric, underscore, dash, dot
        if not re.match(r'^[a-zA-Z0-9_.-]+$', user_id):
            raise ValueError("User ID contains invalid characters")

        return user_id

    @staticmethod
    def validate_tool_name(tool_name: str) -> str:
        """Validate MCP tool name"""
        if not tool_name or not isinstance(tool_name, str):
            raise ValueError("Tool name must be a non-empty string")

        tool_name = tool_name.strip()

        # Allow specific tool names
        valid_tools = [
            'write_to_terminal',
            'read_terminal_output',
            'send_control_character'
        ]

        if tool_name not in valid_tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        return tool_name

    @staticmethod
    def validate_lines_of_output(lines: Any) -> int:
        """Validate lines of output parameter"""
        try:
            lines = int(lines)
        except (ValueError, TypeError):
            raise ValueError("Lines of output must be a number")

        if lines < 1 or lines > 1000:
            raise ValueError("Lines of output must be between 1 and 1000")

        return lines

    @staticmethod
    def validate_control_character(char: str) -> str:
        """Validate control character"""
        if not char or not isinstance(char, str):
            raise ValueError("Control character must be a single letter")

        char = char.upper().strip()

        if len(char) != 1 or not char.isalpha():
            raise ValueError("Control character must be a single letter (A-Z)")

        return char

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def validate_request_data(data: Dict[str, Any], required_fields: List[str] = None) -> Dict[str, Any]:
    """Validate request data structure"""
    if required_fields:
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")

    return data

# Convenience functions for common validations
def validate_chat_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate chat request data"""
    data = validate_request_data(data, ['message'])
    data['message'] = InputValidator.validate_message(data['message'])
    return data

def validate_tool_call(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate tool call data"""
    data = validate_request_data(data, ['name', 'arguments'])
    data['name'] = InputValidator.validate_tool_name(data['name'])

    # Validate arguments based on tool
    if data['name'] == 'write_to_terminal':
        data['arguments']['command'] = InputValidator.sanitize_command(data['arguments']['command'])
    elif data['name'] == 'read_terminal_output':
        data['arguments']['linesOfOutput'] = InputValidator.validate_lines_of_output(
            data['arguments'].get('linesOfOutput', 25)
        )
    elif data['name'] == 'send_control_character':
        data['arguments']['letter'] = InputValidator.validate_control_character(
            data['arguments']['letter']
        )

    return data