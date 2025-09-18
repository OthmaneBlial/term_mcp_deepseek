import os

class Config:
    # API Keys
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

    # Server settings
    PORT = int(os.getenv("PORT", "8000"))
    JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME")