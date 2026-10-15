import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "RemoDesk Remote Desktop Gateway"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Security & Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "remodesk-ultra-secure-signaling-jwt-secret-key-32chars-min")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./remodesk.db")

    # STUN / TURN Configuration
    STUN_SERVERS: List[str] = [
        "stun:stun.l.google.com:19302",
        "stun:stun1.l.google.com:19302",
        "stun:stun2.l.google.com:19302",
        "stun:stun.cloudflare.com:3478",
    ]
    TURN_SERVER_URL: str = os.getenv("TURN_SERVER_URL", "")
    TURN_SECRET: str = os.getenv("TURN_SECRET", "remodesk-coturn-shared-secret")
    TURN_TTL_SECONDS: int = 3600 * 4

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Session Management
    SESSION_TIMEOUT_SECONDS: int = 300
    HEARTBEAT_INTERVAL_SECONDS: int = 15

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="allow")


settings = Settings()
