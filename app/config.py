"""
Configuration settings for Cyber-Visceral Link API.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application configuration."""
    
    # WebSocket Configuration
    ws_host: str = "0.0.0.0"
    ws_port: int = 8000
    ws_path: str = "/ws"
    
    # RAM Disk Log Path
    ram_disk_log_path: str = "/dev/shm/witcher_events.log"
    
    # Security Settings
    allowed_ips: List[str] = ["127.0.0.1", "::1"]  # localhost only by default
    max_payload_size: int = 64  # bytes
    
    # Heartbeat Configuration
    heartbeat_interval: int = 30  # seconds
    heartbeat_timeout: int = 60  # seconds
    
    # Reconnection Configuration
    max_reconnect_attempts: int = 5
    reconnect_delay: int = 5  # seconds
    
    # Logging
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )


settings = Settings()
