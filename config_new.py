import os

class Config:
    PORT = int(os.getenv("PORT", "8000"))
    JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME")