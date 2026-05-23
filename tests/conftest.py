"""
Global configuration and fixtures for Cyber-Visceral Link tests.
"""
import asyncio
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.config import Settings
from app.state import SystemState, ClientInfo
from app.protocol import OutputEvent, InputEvent
from app.websocket_manager import WebSocketManager
from app.log_reader import AsyncLogReader
from app.input_handler import InputHandler


# Fixtures globais


@pytest.fixture
def mock_settings():
    """Mock settings instance with test values."""
    return Settings(
        ws_host="127.0.0.1",
        ws_port=8001,
        ws_path="/ws",
        ram_disk_log_path="/tmp/test_witcher_events.log",
        allowed_ips=["127.0.0.1", "::1"],
        max_payload_size=64,
        heartbeat_interval=1,
        heartbeat_timeout=2,
        max_reconnect_attempts=3,
        reconnect_delay=1,
        log_level="DEBUG"
    )


@pytest.fixture
def reset_system_state():
    """Reset system state before and after each test."""
    from app.state import system_state
    
    # Store original state
    original_clients = system_state.clients.copy()
    original_events_processed = system_state.total_events_processed
    original_messages_sent = system_state.total_messages_sent
    original_messages_received = system_state.total_messages_received
    
    yield
    
    # Restore state
    system_state.clients = original_clients
    system_state.total_events_processed = original_events_processed
    system_state.total_messages_sent = original_messages_sent
    system_state.total_messages_received = original_messages_received


@pytest.fixture
def system_state_instance():
    """Create a fresh SystemState instance for testing."""
    return SystemState()


@pytest.fixture
def sample_client_info():
    """Sample ClientInfo for testing."""
    return ClientInfo(
        client_id="test-client-123",
        connected_at=datetime.now(),
        last_heartbeat=datetime.now(),
        ip_address="127.0.0.1"
    )


@pytest.fixture
def multiple_clients():
    """Create multiple clients for testing."""
    clients = {}
    for i in range(3):
        clients[f"client-{i}"] = ClientInfo(
            client_id=f"client-{i}",
            connected_at=datetime.now(),
            last_heartbeat=datetime.now(),
            ip_address="127.0.0.1"
        )
    return clients


@pytest.fixture
def sample_messages():
    """Sample protocol messages for testing."""
    return {
        "output_gore": "OUTPUT:GORE_FLASH",
        "output_damage": "OUTPUT:DAMAGE_PULSE",
        "output_kill": "OUTPUT:KILL_STREAK",
        "input_panic": "INPUT:PANIC_BUTTON",
        "input_attack": "INPUT:ATTACK",
        "heartbeat_ping": "HEARTBEAT:PING",
        "output_with_data": "OUTPUT:GORE_FLASH:intensity:high",
        "input_with_data": "INPUT:PANIC_BUTTON:timestamp:123456"
    }


@pytest.fixture
def websocket_manager_instance():
    """Create a fresh WebSocketManager instance for testing."""
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    websocket = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.close = AsyncMock()
    websocket.receive_text = AsyncMock()
    websocket.client = MagicMock()
    websocket.client.host = "127.0.0.1"
    return websocket


@pytest.fixture
def log_reader_instance(tmp_path):
    """Create a fresh AsyncLogReader instance with temp file."""
    log_file = tmp_path / "test_events.log"
    return AsyncLogReader(str(log_file))


@pytest.fixture
def temp_log_file(tmp_path):
    """Create a temporary log file for testing."""
    log_file = tmp_path / "test_events.log"
    log_file.write_text("")
    return str(log_file)


@pytest.fixture
def sample_log_content():
    """Sample log content for testing."""
    return """2024-01-01T10:00:00 - GORE_EVENT
2024-01-01T10:00:01 - DAMAGE_EVENT
2024-01-01T10:00:02 - KILL_EVENT
2024-01-01T10:00:03 - COMBO_EVENT
2024-01-01T10:00:04 - DEATH_EVENT"""


@pytest.fixture
def input_handler_instance():
    """Create a fresh InputHandler instance for testing."""
    return InputHandler()


@pytest.fixture
def mock_websocket_manager():
    """Mock websocket_manager for testing."""
    manager = AsyncMock()
    manager.broadcast = AsyncMock(return_value=1)
    return manager


@pytest.fixture
def sample_events():
    """Sample events for testing."""
    return [
        "GORE_EVENT",
        "DAMAGE_EVENT",
        "KILL_EVENT",
        "COMBO_EVENT",
        "CRITICAL_EVENT",
        "ADRENALINE_EVENT",
        "LOW_HEALTH_EVENT",
        "DEATH_EVENT"
    ]


# Hooks


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test."""
    from app.state import system_state
    from app.websocket_manager import websocket_manager
    from app.log_reader import log_reader
    from app.input_handler import input_handler
    
    # Reset system state
    system_state.clients.clear()
    system_state.total_events_processed = 0
    system_state.total_messages_sent = 0
    system_state.total_messages_received = 0
    
    # Clear queue
    while not system_state.event_queue.empty():
        system_state.event_queue.get_nowait()
    
    yield
    
    # Cleanup after test
    # Stop any running tasks
    if log_reader._is_running:
        import asyncio
        asyncio.create_task(log_reader.stop())
    
    if input_handler._is_running:
        import asyncio
        asyncio.create_task(input_handler.stop())
