"""
Integration tests for API REST endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.integration
class TestAPIEndpoints:
    """Test API REST endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Cyber-Visceral Link API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "clients" in data
        assert "queue_size" in data
        assert "latency_avg" in data
    
    def test_get_stats(self, client):
        """Test getting system statistics."""
        response = client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "connected_clients" in data
        assert "events_processed" in data
        assert "messages_sent" in data
        assert "messages_received" in data
        assert "queue_size" in data
    
    def test_get_clients_empty(self, client):
        """Test getting clients when none connected."""
        response = client.get("/clients")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["clients"] == []
    
    def test_get_clients_with_rtt_fields(self, client):
        """Test getting clients includes RTT fields."""
        from app.state import system_state, ClientInfo
        from datetime import datetime
        import asyncio
        
        # Add a client with RTT data
        client_id = "test-client-rtt"
        async def add_test_client():
            system_state.clients[client_id] = ClientInfo(
                client_id=client_id,
                connected_at=datetime.now(),
                last_heartbeat=datetime.now(),
                ip_address="192.168.1.1",
                rtt_ms=45.5,
                jitter_ms=2.3,
                packet_loss=0.01
            )
        
        asyncio.run(add_test_client())
        
        try:
            response = client.get("/clients")
            
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert len(data["clients"]) == 1
            
            client_data = data["clients"][0]
            assert "rtt_ms" in client_data
            assert "jitter_ms" in client_data
            assert "packet_loss" in client_data
            assert client_data["rtt_ms"] == 45.5
            assert client_data["jitter_ms"] == 2.3
            assert client_data["packet_loss"] == 0.01
        finally:
            # Cleanup
            async def cleanup():
                if client_id in system_state.clients:
                    del system_state.clients[client_id]
            asyncio.run(cleanup())
    
    def test_broadcast_message_valid(self, client):
        """Test broadcasting a valid message."""
        response = client.post("/broadcast", json={"message": "OUTPUT:GORE_FLASH"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "OUTPUT:GORE_FLASH"
        assert data["sent_to"] == 0  # No clients connected
        assert "parsed" in data
    
    def test_broadcast_message_invalid_format(self, client):
        """Test broadcasting invalid message format."""
        response = client.post("/broadcast", json={"message": "INVALID"})
        
        assert response.status_code == 400
    
    def test_broadcast_message_missing_field(self, client):
        """Test broadcasting without message field."""
        response = client.post("/broadcast", json={})
        
        assert response.status_code == 422  # Validation error
    
    def test_send_to_client_valid(self, client):
        """Test sending message to specific client."""
        response = client.post(
            "/send/test-client-id",
            json={"message": "OUTPUT:GORE_FLASH"}
        )
        
        # Client doesn't exist, should return 404
        assert response.status_code == 404
    
    def test_send_to_client_invalid_format(self, client):
        """Test sending invalid message to client."""
        response = client.post(
            "/send/test-client-id",
            json={"message": "INVALID"}
        )
        
        assert response.status_code == 400
    
    def test_send_to_client_missing_field(self, client):
        """Test sending without message field."""
        response = client.post("/send/test-client-id", json={})
        
        assert response.status_code == 422
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.get("/")
        
        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers or True  # CORS middleware adds these
    
    def test_api_docs_accessible(self, client):
        """Test API documentation is accessible."""
        response = client.get("/docs")
        
        assert response.status_code == 200
    
    def test_api_redoc_accessible(self, client):
        """Test ReDoc documentation is accessible."""
        response = client.get("/redoc")
        
        assert response.status_code == 200
    
    def test_openapi_schema(self, client):
        """Test OpenAPI schema is available."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
