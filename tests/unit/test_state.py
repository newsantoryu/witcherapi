"""
Unit tests for state management module.
"""
import pytest
from datetime import datetime, timedelta

from app.state import SystemState, ClientInfo


@pytest.mark.unit
class TestClientInfo:
    """Test ClientInfo dataclass."""
    
    def test_client_info_creation(self, sample_client_info):
        """Test ClientInfo can be created."""
        assert sample_client_info.client_id == "test-client-123"
        assert sample_client_info.ip_address == "127.0.0.1"
        assert isinstance(sample_client_info.connected_at, datetime)
        assert isinstance(sample_client_info.last_heartbeat, datetime)
    
    def test_is_alive_within_timeout(self, sample_client_info):
        """Test is_alive returns True when within timeout."""
        assert sample_client_info.is_alive(timeout_seconds=60) is True
    
    def test_is_alive_expired(self, sample_client_info):
        """Test is_alive returns False when heartbeat expired."""
        # Set heartbeat to past
        sample_client_info.last_heartbeat = datetime.now() - timedelta(seconds=120)
        assert sample_client_info.is_alive(timeout_seconds=60) is False
    
    def test_is_alive_exact_timeout(self, sample_client_info):
        """Test is_alive at exact timeout boundary."""
        # Set heartbeat to exactly timeout
        sample_client_info.last_heartbeat = datetime.now() - timedelta(seconds=60)
        assert sample_client_info.is_alive(timeout_seconds=60) is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestSystemState:
    """Test SystemState class."""
    
    async def test_state_initialization(self, system_state_instance):
        """Test SystemState initializes with correct defaults."""
        assert system_state_instance.clients == {}
        assert system_state_instance.is_running is False
        assert system_state_instance.total_events_processed == 0
        assert system_state_instance.total_messages_sent == 0
        assert system_state_instance.total_messages_received == 0
    
    async def test_add_client(self, system_state_instance):
        """Test adding a new client."""
        client_id = "test-client-1"
        ip_address = "192.168.1.1"
        
        await system_state_instance.add_client(client_id, ip_address)
        
        assert client_id in system_state_instance.clients
        assert system_state_instance.clients[client_id].client_id == client_id
        assert system_state_instance.clients[client_id].ip_address == ip_address
    
    async def test_add_duplicate_client(self, system_state_instance):
        """Test adding duplicate client overwrites existing."""
        client_id = "test-client-1"
        ip_address_1 = "192.168.1.1"
        ip_address_2 = "192.168.1.2"
        
        await system_state_instance.add_client(client_id, ip_address_1)
        await system_state_instance.add_client(client_id, ip_address_2)
        
        assert system_state_instance.clients[client_id].ip_address == ip_address_2
    
    async def test_remove_client(self, system_state_instance):
        """Test removing an existing client."""
        client_id = "test-client-1"
        await system_state_instance.add_client(client_id, "192.168.1.1")
        
        await system_state_instance.remove_client(client_id)
        
        assert client_id not in system_state_instance.clients
    
    async def test_remove_nonexistent_client(self, system_state_instance):
        """Test removing nonexistent client does not raise error."""
        # Should not raise an exception
        await system_state_instance.remove_client("nonexistent-client")
    
    async def test_update_heartbeat(self, system_state_instance):
        """Test updating client heartbeat."""
        client_id = "test-client-1"
        await system_state_instance.add_client(client_id, "192.168.1.1")
        
        old_heartbeat = system_state_instance.clients[client_id].last_heartbeat
        # Small delay to ensure timestamp changes
        import asyncio
        await asyncio.sleep(0.01)
        
        await system_state_instance.update_heartbeat(client_id)
        
        new_heartbeat = system_state_instance.clients[client_id].last_heartbeat
        assert new_heartbeat > old_heartbeat
    
    async def test_update_heartbeat_nonexistent(self, system_state_instance):
        """Test updating heartbeat for nonexistent client."""
        # Should not raise an exception
        await system_state_instance.update_heartbeat("nonexistent-client")
    
    async def test_get_client(self, system_state_instance):
        """Test getting existing client."""
        client_id = "test-client-1"
        await system_state_instance.add_client(client_id, "192.168.1.1")
        
        client = await system_state_instance.get_client(client_id)
        
        assert client is not None
        assert client.client_id == client_id
    
    async def test_get_client_nonexistent(self, system_state_instance):
        """Test getting nonexistent client returns None."""
        client = await system_state_instance.get_client("nonexistent-client")
        assert client is None
    
    async def test_get_all_clients(self, system_state_instance, multiple_clients):
        """Test getting all clients."""
        # Add multiple clients
        for client_id, client_info in multiple_clients.items():
            system_state_instance.clients[client_id] = client_info
        
        all_clients = await system_state_instance.get_all_clients()
        
        assert len(all_clients) == len(multiple_clients)
        assert all(client_id in all_clients for client_id in multiple_clients.keys())
    
    async def test_get_client_count(self, system_state_instance):
        """Test getting client count."""
        assert await system_state_instance.get_client_count() == 0
        
        await system_state_instance.add_client("client-1", "192.168.1.1")
        assert await system_state_instance.get_client_count() == 1
        
        await system_state_instance.add_client("client-2", "192.168.1.2")
        assert await system_state_instance.get_client_count() == 2
    
    async def test_cleanup_dead_clients(self, system_state_instance):
        """Test removing dead clients."""
        # Add clients
        await system_state_instance.add_client("alive-client", "192.168.1.1")
        await system_state_instance.add_client("dead-client", "192.168.1.2")
        
        # Make one client dead
        system_state_instance.clients["dead-client"].last_heartbeat = \
            datetime.now() - timedelta(seconds=120)
        
        dead_count = await system_state_instance.cleanup_dead_clients(timeout_seconds=60)
        
        assert dead_count == 1
        assert "alive-client" in system_state_instance.clients
        assert "dead-client" not in system_state_instance.clients
    
    async def test_cleanup_no_dead_clients(self, system_state_instance):
        """Test cleanup when no clients are dead."""
        await system_state_instance.add_client("client-1", "192.168.1.1")
        await system_state_instance.add_client("client-2", "192.168.1.2")
        
        dead_count = await system_state_instance.cleanup_dead_clients(timeout_seconds=60)
        
        assert dead_count == 0
        assert len(system_state_instance.clients) == 2
    
    async def test_increment_events_processed(self, system_state_instance):
        """Test incrementing events processed counter."""
        initial = system_state_instance.total_events_processed
        await system_state_instance.increment_events_processed()
        assert system_state_instance.total_events_processed == initial + 1
    
    async def test_increment_messages_sent(self, system_state_instance):
        """Test incrementing messages sent counter."""
        initial = system_state_instance.total_messages_sent
        await system_state_instance.increment_messages_sent()
        assert system_state_instance.total_messages_sent == initial + 1
    
    async def test_increment_messages_received(self, system_state_instance):
        """Test incrementing messages received counter."""
        initial = system_state_instance.total_messages_received
        await system_state_instance.increment_messages_received()
        assert system_state_instance.total_messages_received == initial + 1
    
    async def test_get_stats(self, system_state_instance):
        """Test getting system statistics."""
        # Add some data
        await system_state_instance.add_client("client-1", "192.168.1.1")
        await system_state_instance.increment_events_processed()
        await system_state_instance.increment_messages_sent()
        await system_state_instance.increment_messages_received()
        
        stats = await system_state_instance.get_stats()
        
        assert stats["connected_clients"] == 1
        assert stats["events_processed"] == 1
        assert stats["messages_sent"] == 1
        assert stats["messages_received"] == 1
        assert "queue_size" in stats
    
    async def test_concurrent_client_operations(self, system_state_instance):
        """Test concurrent client operations are thread-safe."""
        import asyncio
        
        async def add_client_task(i):
            await system_state_instance.add_client(f"client-{i}", "192.168.1.1")
        
        # Add multiple clients concurrently
        tasks = [add_client_task(i) for i in range(10)]
        await asyncio.gather(*tasks)
        
        assert await system_state_instance.get_client_count() == 10
    
    async def test_event_queue_operations(self, system_state_instance):
        """Test event queue operations."""
        # Put items in queue
        await system_state_instance.event_queue.put("event1")
        await system_state_instance.event_queue.put("event2")
        
        assert system_state_instance.event_queue.qsize() == 2
        
        # Get items
        event1 = await system_state_instance.event_queue.get()
        event2 = await system_state_instance.event_queue.get()
        
        assert event1 == "event1"
        assert event2 == "event2"
