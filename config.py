import os

class Config:
    # API Keys
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

    # Server settings
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/term_mcp_deepseek.log")
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "10485760"))
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    # Session Management
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))
    MAX_CONCURRENT_SESSIONS = int(os.getenv("MAX_CONCURRENT_SESSIONS", "10"))

    # Security Configuration
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here")
    JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME")
    MAX_COMMAND_LENGTH = int(os.getenv("MAX_COMMAND_LENGTH", "1000"))

    # DeepSeek Configuration
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_URL = os.getenv("DEEPSEEK_URL", "https://api.deepseek.com/chat/completions")

    # MCP Configuration
    MCP_VERSION = os.getenv("MCP_VERSION", "1.0.0")

# Create a config instance for backward compatibility
config = Config()