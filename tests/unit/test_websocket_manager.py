"""
Unit tests for WebSocket manager module.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.websocket_manager import WebSocketManager
from app.protocol import ProtocolError


@pytest.mark.unit
@pytest.mark.asyncio
class TestWebSocketManager:
    """Test WebSocketManager class."""
    
    async def test_manager_initialization(self, websocket_manager_instance):
        """Test WebSocketManager initializes correctly."""
        assert websocket_manager_instance.active_connections == {}
        assert websocket_manager_instance._message_handlers == {}
        assert websocket_manager_instance._heartbeat_task is None
        assert websocket_manager_instance._cleanup_task is None
    
    async def test_connect_client(self, websocket_manager_instance, mock_websocket):
        """Test connecting a client."""
        client_ip = "127.0.0.1"
        
        client_id = await websocket_manager_instance.connect(mock_websocket, client_ip)
        
        assert client_id is not None
        assert client_id in websocket_manager_instance.active_connections
        mock_websocket.accept.assert_called_once()
    
    async def test_disconnect_client(self, websocket_manager_instance, mock_websocket):
        """Test disconnecting a client."""
        client_ip = "127.0.0.1"
        client_id = await websocket_manager_instance.connect(mock_websocket, client_ip)
        
        await websocket_manager_instance.disconnect(client_id)
        
        assert client_id not in websocket_manager_instance.active_connections
        mock_websocket.close.assert_called_once()
    
    async def test_disconnect_nonexistent_client(self, websocket_manager_instance):
        """Test disconnecting nonexistent client."""
        # Should not raise error
        await websocket_manager_instance.disconnect("nonexistent-client")
    
    async def test_send_message_success(self, websocket_manager_instance, mock_websocket):
        """Test sending message successfully."""
        client_ip = "127.0.0.1"
        client_id = await websocket_manager_instance.connect(mock_websocket, client_ip)
        message = "OUTPUT:GORE_FLASH"
        
        result = await websocket_manager_instance.send_message(client_id, message)
        
        assert result is True
        mock_websocket.send_text.assert_called_once_with(message)
    
    async def test_send_message_nonexistent_client(self, websocket_manager_instance):
        """Test sending message to nonexistent client."""
        result = await websocket_manager_instance.send_message("nonexistent-client", "OUTPUT:GORE_FLASH")
        
        assert result is False
    
    async def test_send_message_failure(self, websocket_manager_instance, mock_websocket):
        """Test sending message when WebSocket fails."""
        client_ip = "127.0.0.1"
        client_id = await websocket_manager_instance.connect(mock_websocket, client_ip)
        
        # Make send_text raise an exception
        mock_websocket.send_text.side_effect = Exception("Connection error")
        
        result = await websocket_manager_instance.send_message(client_id, "OUTPUT:GORE_FLASH")
        
        assert result is False
        assert client_id not in websocket_manager_instance.active_connections
    
    async def test_broadcast_no_clients(self, websocket_manager_instance):
        """Test broadcasting with no clients."""
        message = "OUTPUT:GORE_FLASH"
        
        count = await websocket_manager_instance.broadcast(message)
        
        assert count == 0
    
    async def test_broadcast_with_clients(self, websocket_manager_instance, mock_websocket):
        """Test broadcasting with connected clients."""
        # Connect multiple clients
        client_ids = []
        for i in range(3):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
            ws.close = AsyncMock()
            client_id = await websocket_manager_instance.connect(ws, "127.0.0.1")
            client_ids.append(client_id)
        
        message = "OUTPUT:GORE_FLASH"
        count = await websocket_manager_instance.broadcast(message)
        
        assert count == 3
        
        # Cleanup
        for client_id in client_ids:
            await websocket_manager_instance.disconnect(client_id)
    
    async def test_broadcast_partial_failure(self, websocket_manager_instance, mock_websocket):
        """Test broadcasting when some clients fail."""
        # Connect multiple clients
        client_ids = []
        for i in range(3):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
            ws.close = AsyncMock()
            
            # Make second client fail
            if i == 1:
                ws.send_text.side_effect = Exception("Connection error")
            
            client_id = await websocket_manager_instance.connect(ws, "127.0.0.1")
            client_ids.append(client_id)
        
        message = "OUTPUT:GORE_FLASH"
        count = await websocket_manager_instance.broadcast(message)
        
        # Should succeed for 2 clients, fail for 1
        assert count == 2
        
        # Cleanup
        for client_id in client_ids:
            await websocket_manager_instance.disconnect(client_id)
    
    async def test_receive_message_valid(self, websocket_manager_instance, mock_websocket):
        """Test receiving valid message."""
        client_ip = "127.0.0.1"
        client_id = await websocket_manager_instance.connect(mock_websocket, client_ip)
        message = "INPUT:PANIC_BUTTON"
        
        await websocket_manager_instance.receive_message(client_id, message)
        
        # Should not raise error
        assert True
    
    async def test_receive_message_invalid_payload(self, websocket_manager_instance, mock_websocket):
        """Test receiving message with invalid payload size."""
        client_ip = "127.0.0.1"
        client_id = await websocket_manager_instance.connect(mock_websocket, client_ip)
        
        # Create a message larger than max payload
        large_message = "OUTPUT:GORE_FLASH" * 10
        
        await websocket_manager_instance.receive_message(client_id, large_message)
        
        # Client should be disconnected
        assert client_id not in websocket_manager_instance.active_connections
    
    async def test_receive_message_invalid_format(self, websocket_manager_instance, mock_websocket):
        """Test receiving message with invalid format."""
        client_ip = "127.0.0.1"
        client_id = await websocket_manager_instance.connect(mock_websocket, client_ip)
        message = "INVALID_MESSAGE_FORMAT"
        
        # Should not raise error, just log
        await websocket_manager_instance.receive_message(client_id, message)
        
        # Client should still be connected (invalid format doesn't disconnect)
        assert client_id in websocket_manager_instance.active_connections
    
    async def test_register_handler(self, websocket_manager_instance):
        """Test registering message handler."""
        async def dummy_handler(client_id, message):
            pass
        
        websocket_manager_instance.register_handler("INPUT", dummy_handler)
        
        assert "INPUT" in websocket_manager_instance._message_handlers
        assert websocket_manager_instance._message_handlers["INPUT"] == dummy_handler
    
    async def test_register_handler_overwrites(self, websocket_manager_instance):
        """Test registering handler overwrites existing."""
        async def handler1(client_id, message):
            pass
        
        async def handler2(client_id, message):
            pass
        
        websocket_manager_instance.register_handler("INPUT", handler1)
        websocket_manager_instance.register_handler("INPUT", handler2)
        
        assert websocket_manager_instance._message_handlers["INPUT"] == handler2
    
    async def test_start_stop_heartbeat(self, websocket_manager_instance):
        """Test starting and stopping heartbeat."""
        await websocket_manager_instance.start_heartbeat()
        
        assert websocket_manager_instance._heartbeat_task is not None
        assert not websocket_manager_instance._heartbeat_task.done()
        
        await websocket_manager_instance.stop_heartbeat()
        
        # Task may be cancelled but not None, check if done or cancelled
        assert websocket_manager_instance._heartbeat_task is None or websocket_manager_instance._heartbeat_task.done()
    
    async def test_start_heartbeat_already_running(self, websocket_manager_instance):
        """Test starting heartbeat when already running."""
        await websocket_manager_instance.start_heartbeat()
        original_task = websocket_manager_instance._heartbeat_task
        
        await websocket_manager_instance.start_heartbeat()
        
        # Should not create new task
        assert websocket_manager_instance._heartbeat_task == original_task
        
        await websocket_manager_instance.stop_heartbeat()
    
    async def test_stop_heartbeat_not_running(self, websocket_manager_instance):
        """Test stopping heartbeat when not running."""
        # Should not raise error
        await websocket_manager_instance.stop_heartbeat()
    
    async def test_start_stop_cleanup(self, websocket_manager_instance):
        """Test starting and stopping cleanup."""
        await websocket_manager_instance.start_cleanup()
        
        assert websocket_manager_instance._cleanup_task is not None
        assert not websocket_manager_instance._cleanup_task.done()
        
        await websocket_manager_instance.stop_cleanup()
        
        # Task may be cancelled but not None, check if done or cancelled
        assert websocket_manager_instance._cleanup_task is None or websocket_manager_instance._cleanup_task.done()
    
    async def test_start_cleanup_already_running(self, websocket_manager_instance):
        """Test starting cleanup when already running."""
        await websocket_manager_instance.start_cleanup()
        original_task = websocket_manager_instance._cleanup_task
        
        await websocket_manager_instance.start_cleanup()
        
        # Should not create new task
        assert websocket_manager_instance._cleanup_task == original_task
        
        await websocket_manager_instance.stop_cleanup()
    
    async def test_stop_cleanup_not_running(self, websocket_manager_instance):
        """Test stopping cleanup when not running."""
        # Should not raise error
        await websocket_manager_instance.stop_cleanup()
    
    async def test_get_connection_count(self, websocket_manager_instance, mock_websocket):
        """Test getting connection count."""
        assert await websocket_manager_instance.get_connection_count() == 0
        
        await websocket_manager_instance.connect(mock_websocket, "127.0.0.1")
        assert await websocket_manager_instance.get_connection_count() == 1
        
        await websocket_manager_instance.connect(mock_websocket, "127.0.0.1")
        assert await websocket_manager_instance.get_connection_count() == 2
    
    async def test_shutdown(self, websocket_manager_instance, mock_websocket):
        """Test complete shutdown."""
        # Connect clients
        client_id = await websocket_manager_instance.connect(mock_websocket, "127.0.0.1")
        
        # Start background tasks
        await websocket_manager_instance.start_heartbeat()
        await websocket_manager_instance.start_cleanup()
        
        # Shutdown
        await websocket_manager_instance.shutdown()
        
        # All clients should be disconnected
        assert client_id not in websocket_manager_instance.active_connections
        # Tasks may be cancelled but not None, check if done or cancelled
        assert websocket_manager_instance._heartbeat_task is None or websocket_manager_instance._heartbeat_task.done()
        assert websocket_manager_instance._cleanup_task is None or websocket_manager_instance._cleanup_task.done()
    
    async def test_shutdown_with_no_clients(self, websocket_manager_instance):
        """Test shutdown with no connected clients."""
        await websocket_manager_instance.start_heartbeat()
        await websocket_manager_instance.start_cleanup()
        
        await websocket_manager_instance.shutdown()
        
        # Tasks may be cancelled but not None, check if done or cancelled
        assert websocket_manager_instance._heartbeat_task is None or websocket_manager_instance._heartbeat_task.done()
        assert websocket_manager_instance._cleanup_task is None or websocket_manager_instance._cleanup_task.done()
    
    async def test_concurrent_connections(self, websocket_manager_instance):
        """Test handling concurrent connections."""
        async def connect_client(i):
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
            ws.close = AsyncMock()
            return await websocket_manager_instance.connect(ws, "127.0.0.1")
        
        # Connect multiple clients concurrently
        tasks = [connect_client(i) for i in range(10)]
        client_ids = await asyncio.gather(*tasks)
        
        assert await websocket_manager_instance.get_connection_count() == 10
        
        # Cleanup
        for client_id in client_ids:
            await websocket_manager_instance.disconnect(client_id)
