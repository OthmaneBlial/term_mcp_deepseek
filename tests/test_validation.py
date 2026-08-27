import pytest

from term_mcp_deepseek.validation import validate_message, validate_session_id


def test_message_validation_is_not_a_command_policy():
    assert validate_message("  CMD: rm -rf /  ") == "CMD: rm -rf /"
    with pytest.raises(ValueError, match="required"):
        validate_message("   ")
    with pytest.raises(ValueError, match="exceed"):
        validate_message("x" * 10_001)


def test_session_id_validation():
    assert validate_session_id("session-1234") == "session-1234"
    with pytest.raises(ValueError, match="session_id"):
        validate_session_id("bad/id")
