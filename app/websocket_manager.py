"""
WebSocket connection manager for Cyber-Visceral Link.
"""
import asyncio
import logging
from typing import Dict, Set, Optional, Callable
from datetime import datetime
import uuid
import json

from fastapi import WebSocket, WebSocketDisconnect

from app.config import settings
from app.state import system_state, ClientInfo
from app.protocol import MessageParser, ProtocolError

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and message handling."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._message_handlers: Dict[str, Callable] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def connect(self, websocket: WebSocket, client_ip: str) -> str:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            client_ip: Client IP address
            
        Returns:
            Client ID
        """
        await websocket.accept()
        
        # Generate unique client ID
        client_id = str(uuid.uuid4())
        
        # Register connection
        self.active_connections[client_id] = websocket
        
        # Update system state
        await system_state.add_client(client_id, client_ip)
        
        logger.info(f"[WS CONNECTED] Client {client_id} from {client_ip}")
        
        return client_id
    
    async def disconnect(self, client_id: str) -> None:
        """
        Disconnect and remove a client.
        
        Args:
            client_id: Client ID to disconnect
        """
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].close()
            except Exception as e:
                logger.error(f"Error closing connection for {client_id}: {e}")
            
            del self.active_connections[client_id]
            await system_state.remove_client(client_id)
    
    async def send_message(self, client_id: str, message: str) -> bool:
        """
        Send a message to a specific client.
        
        Args:
            client_id: Target client ID
            message: Message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if client_id not in self.active_connections:
            logger.warning(f"Client {client_id} not found")
            return False
        
        try:
            await asyncio.wait_for(
                self.active_connections[client_id].send_text(message),
                timeout=settings.client_timeout
            )
            await system_state.increment_messages_sent()
            logger.debug(f"[MESSAGE SENT] To {client_id}: {message}")
            return True
        except asyncio.TimeoutError:
            logger.error(f"[TIMEOUT] Sending to {client_id}")
            await self.disconnect(client_id)
            return False
        except Exception as e:
            logger.error(f"Error sending to {client_id}: {e}")
            await self.disconnect(client_id)
            return False
    
    async def broadcast(self, message: str) -> int:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: Message to broadcast
            
        Returns:
            Number of clients message was sent to
        """
        if not self.active_connections:
            return 0
        
        # Create tasks for all sends
        tasks = []
        for client_id in list(self.active_connections.keys()):
            tasks.append(self.send_message(client_id, message))
        
        # Execute all sends concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful sends
        successful = sum(1 for r in results if r is True)
        
        logger.info(f"[BROADCAST] Sent to {successful}/{len(self.active_connections)} clients")
        return successful
    
    async def receive_message(self, client_id: str, message: str) -> None:
        """
        Process a received message from a client.
        
        Args:
            client_id: Client ID that sent the message
            message: Received message
        """
        await system_state.increment_messages_received()
        
        # Rate limiting check
        client = await system_state.get_client(client_id)
        if client and not client.check_rate_limit(len(message)):
            logger.warning(f"[RATE LIMIT] Client {client_id} exceeded limits")
            await self.disconnect(client_id)
            return
            
        # Validate payload size
        if not MessageParser.validate_payload(message, settings.max_payload_size):
            logger.warning(f"[PAYLOAD EXCEEDED] Client {client_id}: {len(message)} bytes")
            await self.disconnect(client_id)
            return
            
        # Handle PONG for RTT calculation
        if message == "HEARTBEAT:PONG":
            if client and client._ping_timestamps:
                # Get the oldest ping timestamp
                ping_id = min(client._ping_timestamps.keys())
                ping_time = client._ping_timestamps.pop(ping_id)
                
                rtt = (time.time() - ping_time) * 1000  # ms
                
                # Calculate jitter (difference between current RTT and previous RTT)
                if client.rtt_ms > 0:
                    client.jitter_ms = abs(rtt - client.rtt_ms)
                    
                client.rtt_ms = rtt
                await system_state.record_latency(rtt)
                await system_state.update_heartbeat(client_id)
            return
        
        # Parse message
        try:
            parsed = MessageParser.parse(message)
            logger.info(f"[INPUT RECEIVED] From {client_id}: {parsed}")
            
            # Log for replay system
            if settings.enable_replay_log:
                try:
                    import aiofiles
                    async with aiofiles.open(settings.replay_log_path, mode='a') as f:
                        replay_event = {
                            "timestamp": time.time(),
                            "client_id": client_id,
                            "raw_message": message,
                            "parsed": parsed
                        }
                        await f.write(json.dumps(replay_event) + '\n')
                except Exception as e:
                    logger.error(f"Failed to write replay log: {e}")
            
            # Update heartbeat
            await system_state.update_heartbeat(client_id)
            
            # Call registered handler if exists
            handler = self._message_handlers.get(parsed["message_type"])
            if handler:
                await handler(client_id, parsed)
            
        except ProtocolError as e:
            logger.error(f"[PROTOCOL ERROR] From {client_id}: {e}")
        except Exception as e:
            logger.error(f"[ERROR] Processing message from {client_id}: {e}")
    
    def register_handler(self, message_type: str, handler: Callable) -> None:
        """
        Register a message handler for a specific message type.
        
        Args:
            message_type: Message type to handle
            handler: Async handler function
        """
        self._message_handlers[message_type] = handler
    
    async def start_heartbeat(self) -> None:
        """Start heartbeat monitoring task."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("[HEARTBEAT] Monitoring started")
    
    async def stop_heartbeat(self) -> None:
        """Stop heartbeat monitoring task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info("[HEARTBEAT] Monitoring stopped")
    
    async def _heartbeat_loop(self) -> None:
        """Heartbeat monitoring loop."""
        import time
        while True:
            try:
                await asyncio.sleep(settings.heartbeat_interval)
                
                # Send ping to all clients
                for client_id in list(self.active_connections.keys()):
                    try:
                        client = await system_state.get_client(client_id)
                        if client:
                            ping_id = str(time.time())
                            client._ping_timestamps[ping_id] = time.time()
                            
                            # Clean up old unacknowledged pings (packet loss)
                            now = time.time()
                            lost_pings = [pid for pid, ts in client._ping_timestamps.items() 
                                        if now - ts > settings.heartbeat_timeout]
                            
                            for pid in lost_pings:
                                client._ping_timestamps.pop(pid)
                                
                            if lost_pings:
                                total_pings = len(client._ping_timestamps) + len(lost_pings)
                                client.packet_loss = len(lost_pings) / total_pings if total_pings > 0 else 0.0
                                
                        await asyncio.wait_for(
                            self.active_connections[client_id].send_text("HEARTBEAT:PING"),
                            timeout=settings.client_timeout
                        )
                    except asyncio.TimeoutError:
                        logger.error(f"[TIMEOUT] Heartbeat to {client_id}")
                        await self.disconnect(client_id)
                    except Exception as e:
                        logger.error(f"Heartbeat failed for {client_id}: {e}")
                        await self.disconnect(client_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
    
    async def start_cleanup(self) -> None:
        """Start dead client cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("[CLEANUP] Task started")
    
    async def stop_cleanup(self) -> None:
        """Stop dead client cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("[CLEANUP] Task stopped")
    
    async def _cleanup_loop(self) -> None:
        """Dead client cleanup loop."""
        while True:
            try:
                await asyncio.sleep(settings.heartbeat_interval)
                
                # Remove dead clients
                dead_count = await system_state.cleanup_dead_clients(settings.heartbeat_timeout)
                
                if dead_count > 0:
                    logger.info(f"[CLEANUP] Removed {dead_count} dead clients")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
    
    async def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)
    
    async def shutdown(self) -> None:
        """Shutdown manager and close all connections."""
        logger.info("[SHUTDOWN] Closing all connections...")
        
        # Stop background tasks
        await self.stop_heartbeat()
        await self.stop_cleanup()
        
        # Close all connections
        for client_id in list(self.active_connections.keys()):
            await self.disconnect(client_id)
        
        logger.info("[SHUTDOWN] Complete")


# Global manager instance
websocket_manager = WebSocketManager()
