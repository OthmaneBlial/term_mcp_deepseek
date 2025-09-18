import pytest
from tools.input_validator import InputValidator, ValidationError


class TestInputValidator:
    """Test input validation functionality"""

    def test_sanitize_command_valid(self):
        """Test sanitizing valid commands"""
        command = "ls -la"
        result = InputValidator.sanitize_command(command)
        assert result == command

    def test_sanitize_command_dangerous(self):
        """Test blocking dangerous commands"""
        dangerous_commands = [
            "rm -rf /",
            "rm -rf /*",
            "dd if=/dev/zero of=/dev/sda",
            "shutdown now",
            "sudo rm -rf /"
        ]

        for cmd in dangerous_commands:
            with pytest.raises(ValueError, match="contains potentially dangerous"):
                InputValidator.sanitize_command(cmd)

    def test_sanitize_command_length_limit(self):
        """Test command length limits"""
        long_command = "ls " + "a" * 1000
        with pytest.raises(ValueError, match="too long"):
            InputValidator.sanitize_command(long_command)

    def test_validate_message_valid(self):
        """Test validating valid messages"""
        message = "Hello, how can I help you?"
        result = InputValidator.validate_message(message)
        assert result == message

    def test_validate_message_too_long(self):
        """Test message length limits"""
        long_message = "a" * 10001
        with pytest.raises(ValueError, match="too long"):
            InputValidator.validate_message(long_message)

    def test_validate_session_id_valid(self):
        """Test validating valid session IDs"""
        session_id = "abc123def456"
        result = InputValidator.validate_session_id(session_id)
        assert result == session_id

    def test_validate_session_id_invalid_length(self):
        """Test session ID length validation"""
        # Too short
        with pytest.raises(ValueError, match="length invalid"):
            InputValidator.validate_session_id("abc")

        # Too long
        with pytest.raises(ValueError, match="length invalid"):
            InputValidator.validate_session_id("a" * 200)

    def test_validate_session_id_invalid_chars(self):
        """Test session ID character validation"""
        with pytest.raises(ValueError, match="invalid characters"):
            InputValidator.validate_session_id("abc@123")

    def test_validate_control_character_valid(self):
        """Test validating valid control characters"""
        result = InputValidator.validate_control_character("C")
        assert result == "C"

    def test_validate_control_character_invalid(self):
        """Test invalid control characters"""
        with pytest.raises(ValueError, match="single letter"):
            InputValidator.validate_control_character("CC")

        with pytest.raises(ValueError, match="single letter"):
            InputValidator.validate_control_character("1")

    def test_validate_tool_name_valid(self):
        """Test validating valid tool names"""
        valid_tools = ["write_to_terminal", "read_terminal_output", "send_control_character"]

        for tool in valid_tools:
            result = InputValidator.validate_tool_name(tool)
            assert result == tool

    def test_validate_tool_name_invalid(self):
        """Test invalid tool names"""
        with pytest.raises(ValueError, match="Unknown tool"):
            InputValidator.validate_tool_name("invalid_tool")

    def test_validate_lines_of_output_valid(self):
        """Test validating valid lines of output"""
        result = InputValidator.validate_lines_of_output(25)
        assert result == 25

    def test_validate_lines_of_output_invalid(self):
        """Test invalid lines of output"""
        with pytest.raises(ValueError, match="between 1 and 1000"):
            InputValidator.validate_lines_of_output(0)

        with pytest.raises(ValueError, match="between 1 and 1000"):
            InputValidator.validate_lines_of_output(1001)

    def test_sanitize_file_path_valid(self):
        """Test sanitizing valid file paths"""
        path = "documents/file.txt"
        result = InputValidator.sanitize_file_path(path)
        assert result == path

    def test_sanitize_file_path_dangerous(self):
        """Test blocking dangerous file paths"""
        dangerous_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "..",
            "file/../../../root"
        ]

        for path in dangerous_paths:
            with pytest.raises(ValueError):
                InputValidator.sanitize_file_path(path)