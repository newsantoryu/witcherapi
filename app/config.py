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
    
    # Queue Configuration
    queue_size: int = 1000
    
    # Security Settings
    allowed_ips: List[str] = ["127.0.0.1", "::1"]  # localhost only by default
    max_payload_size: int = 64  # bytes
    
    # Rate Limiting
    rate_limit_events: int = 50  # events per second per client
    rate_limit_payload: int = 1024  # bytes per second per client
    
    # Network Configuration
    client_timeout: int = 30  # seconds for network operations
    
    # Heartbeat Configuration
    heartbeat_interval: int = 10  # seconds
    heartbeat_timeout: int = 30  # seconds
    
    # Reconnection Configuration
    max_reconnect_attempts: int = 5
    reconnect_delay: int = 5  # seconds
    
    # Logging
    log_level: str = "INFO"
    structured_logging: bool = True
    
    # Replay System
    enable_replay_log: bool = True
    replay_log_path: str = "logs/replay_events.jsonl"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )


settings = Settings()
