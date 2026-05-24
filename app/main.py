"""
Main FastAPI application for Cyber-Visceral Link.
"""
import asyncio
import logging
import structlog
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.state import system_state
from app.websocket_manager import websocket_manager
from app.protocol import MessageParser, ProtocolError
from app.log_reader import log_reader
from app.input_handler import input_handler

# Configure structured logging
if settings.structured_logging:
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(message)s"
    )
    logger = structlog.get_logger(__name__)
else:
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("[STARTUP] Initializing Cyber-Visceral Link API...")
    system_state.is_running = True
    
    # Start background tasks
    await websocket_manager.start_heartbeat()
    await websocket_manager.start_cleanup()
    
    # Start log reader
    await log_reader.start()
    
    # Start input handler
    await input_handler.start()
    
    logger.info("[STARTUP] API ready")
    
    yield
    
    # Shutdown
    logger.info("[SHUTDOWN] Shutting down...")
    system_state.is_running = False
    
    # Stop log reader and input handler
    await log_reader.stop()
    await input_handler.stop()
    
    # Shutdown websocket manager
    await websocket_manager.shutdown()
    logger.info("[SHUTDOWN] Complete")


# Create FastAPI app
app = FastAPI(
    title="Cyber-Visceral Link API",
    description="WebSocket API for ESP32 integration with The Witcher 3",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Cyber-Visceral Link API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    stats = await system_state.get_stats()
    return {
        "status": "healthy",
        "clients": stats["connected_clients"],
        "queue_size": stats["queue_size"],
        "latency_avg": stats["avg_latency_ms"]
    }


@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    return await system_state.get_stats()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for ESP32 connections.
    
    Handles bidirectional communication with ESP32 devices.
    """
    # Get client IP
    client_host = websocket.client.host if websocket.client else "unknown"
    
    # Check IP whitelist
    if client_host not in settings.allowed_ips:
        logger.warning(f"[ACCESS DENIED] IP not in whitelist: {client_host}")
        await websocket.close(code=1008, reason="IP not allowed")
        return
    
    # Connect client
    client_id = await websocket_manager.connect(websocket, client_host)
    
    try:
        # Main message loop
        while True:
            # Receive message
            message = await websocket.receive_text()
            
            # Process message
            await websocket_manager.receive_message(client_id, message)
            
    except WebSocketDisconnect:
        logger.info(f"[WS DISCONNECT] Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"[WS ERROR] Client {client_id}: {e}")
    finally:
        # Ensure cleanup
        await websocket_manager.disconnect(client_id)


@app.post("/broadcast")
async def broadcast_message(message: str):
    """
    Broadcast a message to all connected clients.
    
    Args:
        message: Message to broadcast
        
    Returns:
        Number of clients message was sent to
    """
    # Validate message
    try:
        parsed = MessageParser.parse(message)
    except ProtocolError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Validate payload
    if not MessageParser.validate_payload(message, settings.max_payload_size):
        raise HTTPException(status_code=400, detail="Payload too large")
    
    # Broadcast
    count = await websocket_manager.broadcast(message)
    
    return {
        "message": message,
        "sent_to": count,
        "parsed": parsed
    }


@app.post("/send/{client_id}")
async def send_to_client(client_id: str, message: str):
    """
    Send a message to a specific client.
    
    Args:
        client_id: Target client ID
        message: Message to send
        
    Returns:
        Success status
    """
    # Validate message
    try:
        parsed = MessageParser.parse(message)
    except ProtocolError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Validate payload
    if not MessageParser.validate_payload(message, settings.max_payload_size):
        raise HTTPException(status_code=400, detail="Payload too large")
    
    # Send
    success = await websocket_manager.send_message(client_id, message)
    
    if not success:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return {
        "message": message,
        "client_id": client_id,
        "parsed": parsed
    }


@app.get("/clients")
async def get_clients():
    """Get list of connected clients."""
    clients = await system_state.get_all_clients()
    
    client_list = []
    for client_id, client_info in clients.items():
        client_list.append({
            "client_id": client_id,
            "connected_at": client_info.connected_at.isoformat(),
            "last_heartbeat": client_info.last_heartbeat.isoformat(),
            "ip_address": client_info.ip_address,
            "is_alive": client_info.is_alive(settings.heartbeat_timeout),
            "rtt_ms": round(client_info.rtt_ms, 2),
            "jitter_ms": round(client_info.jitter_ms, 2),
            "packet_loss": round(client_info.packet_loss, 4)
        })
    
    return {
        "count": len(client_list),
        "clients": client_list
    }


if __name__ == "__main__":
    import uvicorn
    import uvloop
    
    # Set uvloop as the event loop policy
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    uvicorn.run(
        "app.main:app",
        host=settings.ws_host,
        port=settings.ws_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
