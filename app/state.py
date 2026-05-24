"""
Application state management for Cyber-Visceral Link.
"""
import asyncio
from typing import Dict, Set, Optional
from datetime import datetime
from dataclasses import dataclass, field
import logging
import time
from collections import deque

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ClientInfo:
    """Information about a connected WebSocket client."""
    client_id: str
    connected_at: datetime
    last_heartbeat: datetime
    ip_address: str
    
    # RTT Tracking
    rtt_ms: float = 0.0
    jitter_ms: float = 0.0
    packet_loss: float = 0.0
    _ping_timestamps: Dict[str, float] = field(default_factory=dict)
    
    # Rate Limiting
    events_this_second: int = 0
    bytes_this_second: int = 0
    last_rate_limit_reset: float = field(default_factory=time.time)
    
    def is_alive(self, timeout_seconds: int = 60) -> bool:
        """Check if client is still alive based on heartbeat."""
        delta = datetime.now() - self.last_heartbeat
        return delta.total_seconds() < timeout_seconds
        
    def check_rate_limit(self, payload_size: int) -> bool:
        """Check if client has exceeded rate limits."""
        now = time.time()
        if now - self.last_rate_limit_reset >= 1.0:
            self.events_this_second = 0
            self.bytes_this_second = 0
            self.last_rate_limit_reset = now
            
        self.events_this_second += 1
        self.bytes_this_second += payload_size
        
        if self.events_this_second > settings.rate_limit_events:
            return False
        if self.bytes_this_second > settings.rate_limit_payload:
            return False
            
        return True


@dataclass
class SystemState:
    """Global application state."""
    clients: Dict[str, ClientInfo] = field(default_factory=dict)
    event_queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=settings.queue_size))
    is_running: bool = False
    
    # Metrics
    total_events_processed: int = 0
    total_messages_sent: int = 0
    total_messages_received: int = 0
    dropped_events: int = 0
    reconnects: int = 0
    peak_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    _latency_history: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Lock for thread-safe operations
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    async def add_client(self, client_id: str, ip_address: str) -> None:
        """Add a new client to the state."""
        async with self._lock:
            self.clients[client_id] = ClientInfo(
                client_id=client_id,
                connected_at=datetime.now(),
                last_heartbeat=datetime.now(),
                ip_address=ip_address
            )
            logger.info(f"[WS CONNECT] Client {client_id} from {ip_address}")
    
    async def remove_client(self, client_id: str) -> None:
        """Remove a client from the state."""
        async with self._lock:
            if client_id in self.clients:
                del self.clients[client_id]
                logger.info(f"[WS DISCONNECT] Client {client_id}")
    
    async def update_heartbeat(self, client_id: str) -> None:
        """Update client heartbeat timestamp."""
        async with self._lock:
            if client_id in self.clients:
                self.clients[client_id].last_heartbeat = datetime.now()
    
    async def get_client(self, client_id: str) -> Optional[ClientInfo]:
        """Get client information."""
        async with self._lock:
            return self.clients.get(client_id)
    
    async def get_all_clients(self) -> Dict[str, ClientInfo]:
        """Get all connected clients."""
        async with self._lock:
            return self.clients.copy()
    
    async def get_client_count(self) -> int:
        """Get number of connected clients."""
        async with self._lock:
            return len(self.clients)
    
    async def cleanup_dead_clients(self, timeout_seconds: int = 60) -> int:
        """Remove clients that haven't sent heartbeat within timeout."""
        dead_clients = []
        async with self._lock:
            for client_id, client_info in self.clients.items():
                if not client_info.is_alive(timeout_seconds):
                    dead_clients.append(client_id)
            
            for client_id in dead_clients:
                del self.clients[client_id]
                logger.info(f"[WS TIMEOUT] Client {client_id} removed")
        
        return len(dead_clients)
    
    async def increment_events_processed(self) -> None:
        """Increment events processed counter."""
        self.total_events_processed += 1
    
    async def increment_messages_sent(self) -> None:
        """Increment messages sent counter."""
        self.total_messages_sent += 1
    
    async def increment_messages_received(self) -> None:
        """Increment messages received counter."""
        self.total_messages_received += 1
    
    async def record_latency(self, latency_ms: float) -> None:
        """Record latency for metrics."""
        self._latency_history.append(latency_ms)
        self.peak_latency_ms = max(self.peak_latency_ms, latency_ms)
        self.avg_latency_ms = sum(self._latency_history) / len(self._latency_history)

    async def get_stats(self) -> Dict[str, float]:
        """Get system statistics."""
        async with self._lock:
            return {
                "connected_clients": len(self.clients),
                "events_processed": self.total_events_processed,
                "messages_sent": self.total_messages_sent,
                "messages_received": self.total_messages_received,
                "queue_size": self.event_queue.qsize(),
                "dropped_events": self.dropped_events,
                "reconnects": self.reconnects,
                "avg_latency_ms": round(self.avg_latency_ms, 2),
                "peak_latency_ms": round(self.peak_latency_ms, 2)
            }


# Global state instance
system_state = SystemState()
