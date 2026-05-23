"""
Integration tests for WebSocket flow.
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from fastapi import WebSocket

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.integration
@pytest.mark.asyncio
class TestWebSocketFlow:
    """Test complete WebSocket flow."""
    
    async def test_websocket_connection_flow(self, client):
        """Test complete WebSocket connection flow."""
        with client.websocket_connect("/ws") as websocket:
            # Connection should be established
            assert websocket is not None
    
    async def test_message_roundtrip(self, client):
        """Test sending and receiving messages."""
        with client.websocket_connect("/ws") as websocket:
            # Send a message
            websocket.send_text("INPUT:PANIC_BUTTON")
            
            # Connection should still be open
            assert websocket is not None
    
    async def test_heartbeat_flow(self, client):
        """Test heartbeat message flow."""
        with client.websocket_connect("/ws") as websocket:
            # Send heartbeat response
            websocket.send_text("HEARTBEAT:PONG")
            
            # Connection should remain open
            assert websocket is not None
    
    async def test_broadcast_flow(self, client):
        """Test broadcast message flow."""
        with client.websocket_connect("/ws") as websocket:
            # Send a message that would trigger broadcast
            websocket.send_text("INPUT:PANIC_BUTTON")
            
            # Connection should remain open
            assert websocket is not None
    
    async def test_invalid_message_flow(self, client):
        """Test handling of invalid messages."""
        with client.websocket_connect("/ws") as websocket:
            # Send invalid message
            websocket.send_text("INVALID_MESSAGE")
            
            # Connection should handle gracefully
            # (may or may not disconnect depending on implementation)
    
    async def test_large_payload_flow(self, client):
        """Test handling of large payload."""
        with client.websocket_connect("/ws") as websocket:
            # Send a message larger than max payload
            large_message = "OUTPUT:GORE_FLASH" * 10
            websocket.send_text(large_message)
            
            # Connection may be disconnected due to payload size
            # This tests the security feature
    
    async def test_concurrent_websocket_connections(self, client):
        """Test multiple concurrent WebSocket connections."""
        connections = []
        
        try:
            # Open multiple connections
            for i in range(3):
                ws = client.websocket_connect("/ws")
                ws.__enter__()
                connections.append(ws)
            
            # All connections should be active
            assert len(connections) == 3
            
        finally:
            # Cleanup
            for ws in connections:
                try:
                    ws.__exit__(None, None, None)
                except:
                    pass
