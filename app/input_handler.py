"""
Input handler for processing events from log reader and dispatching to WebSocket.
"""
import asyncio
import logging
from typing import Optional, Dict, Any

from app.state import system_state
from app.websocket_manager import websocket_manager
from app.protocol import OutputEvent, MessageParser

logger = logging.getLogger(__name__)


class InputHandler:
    """Processes events from log reader and dispatches to WebSocket clients."""
    
    def __init__(self):
        self._is_running: bool = False
        self._process_task: Optional[asyncio.Task] = None
        
        # Event mapping: log event -> protocol output event
        self.event_mapping: Dict[str, OutputEvent] = {
            "GORE_EVENT": OutputEvent.GORE_FLASH,
            "DAMAGE_EVENT": OutputEvent.DAMAGE_PULSE,
            "KILL_EVENT": OutputEvent.KILL_STREAK,
            "COMBO_EVENT": OutputEvent.COMBO_HIT,
            "CRITICAL_EVENT": OutputEvent.CRITICAL_HIT,
            "ADRENALINE_EVENT": OutputEvent.ADRENALINE,
            "LOW_HEALTH_EVENT": OutputEvent.LOW_HEALTH,
            "DEATH_EVENT": OutputEvent.DEATH
        }
    
    async def start(self) -> None:
        """Start the input handler."""
        if self._is_running:
            logger.warning("[INPUT HANDLER] Already running")
            return
        
        self._is_running = True
        self._process_task = asyncio.create_task(self._process_loop())
        logger.info("[INPUT HANDLER] Started")
    
    async def stop(self) -> None:
        """Stop the input handler."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._process_task and not self._process_task.done():
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
        
        logger.info("[INPUT HANDLER] Stopped")
    
    async def _process_loop(self) -> None:
        """Main event processing loop."""
        while self._is_running:
            try:
                # Wait for event from queue
                event = await asyncio.wait_for(
                    system_state.event_queue.get(),
                    timeout=1.0
                )
                
                # Process event
                await self._process_event(event)
                
            except asyncio.TimeoutError:
                # No events, continue
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[INPUT HANDLER] Error in process loop: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_event(self, event: str) -> None:
        """
        Process a single event from the log.
        
        Args:
            event: Raw event string from log
        """
        try:
            event = event.strip()
            
            if not event:
                return
            
            logger.debug(f"[INPUT HANDLER] Processing event: {event}")
            
            # Map event to protocol message
            output_event = self.event_mapping.get(event)
            
            if output_event:
                # Format as protocol message
                message = MessageParser.format_output(output_event)
                
                # Broadcast to all connected clients
                count = await websocket_manager.broadcast(message)
                
                logger.info(f"[EVENT DISPATCHED] {event} -> {message} (to {count} clients)")
            else:
                logger.debug(f"[INPUT HANDLER] Unknown event: {event}")
        
        except Exception as e:
            logger.error(f"[INPUT HANDLER] Error processing event: {e}")
    
    def add_event_mapping(self, log_event: str, output_event: OutputEvent) -> None:
        """
        Add a custom event mapping.
        
        Args:
            log_event: Log event name
            output_event: Corresponding output event
        """
        self.event_mapping[log_event] = output_event
        logger.info(f"[INPUT HANDLER] Added mapping: {log_event} -> {output_event}")
    
    def remove_event_mapping(self, log_event: str) -> None:
        """
        Remove an event mapping.
        
        Args:
            log_event: Log event name to remove
        """
        if log_event in self.event_mapping:
            del self.event_mapping[log_event]
            logger.info(f"[INPUT HANDLER] Removed mapping: {log_event}")
    
    def get_event_mappings(self) -> Dict[str, str]:
        """Get all event mappings."""
        return {k: v.value for k, v in self.event_mapping.items()}


# Global handler instance
input_handler = InputHandler()
