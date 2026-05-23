"""
Unit tests for input handler module.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from app.input_handler import InputHandler
from app.protocol import OutputEvent


@pytest.mark.unit
@pytest.mark.asyncio
class TestInputHandler:
    """Test InputHandler class."""
    
    async def test_handler_initialization(self, input_handler_instance):
        """Test InputHandler initializes correctly."""
        assert input_handler_instance._is_running is False
        assert input_handler_instance._process_task is None
        assert len(input_handler_instance.event_mapping) == 8
    
    async def test_handler_initialization_default_mappings(self, input_handler_instance):
        """Test default event mappings are set."""
        assert "GORE_EVENT" in input_handler_instance.event_mapping
        assert "DAMAGE_EVENT" in input_handler_instance.event_mapping
        assert "KILL_EVENT" in input_handler_instance.event_mapping
        assert "COMBO_EVENT" in input_handler_instance.event_mapping
        assert "CRITICAL_EVENT" in input_handler_instance.event_mapping
        assert "ADRENALINE_EVENT" in input_handler_instance.event_mapping
        assert "LOW_HEALTH_EVENT" in input_handler_instance.event_mapping
        assert "DEATH_EVENT" in input_handler_instance.event_mapping
    
    async def test_start_already_running(self, input_handler_instance):
        """Test starting handler when already running."""
        await input_handler_instance.start()
        await input_handler_instance.start()  # Should not raise error
        await input_handler_instance.stop()
    
    async def test_stop_not_running(self, input_handler_instance):
        """Test stopping handler when not running."""
        # Should not raise error
        await input_handler_instance.stop()
    
    async def test_process_event_valid(self, input_handler_instance):
        """Test processing a valid event."""
        from app.websocket_manager import websocket_manager
        from unittest.mock import AsyncMock, patch
        
        # Mock the broadcast method
        with patch.object(websocket_manager, 'broadcast', new_callable=AsyncMock, return_value=1):
            # Process event
            await input_handler_instance._process_event("GORE_EVENT")
            
            # Verify broadcast was called
            websocket_manager.broadcast.assert_called_once()
    
    async def test_process_event_empty(self, input_handler_instance):
        """Test processing empty event."""
        # Should not raise error
        await input_handler_instance._process_event("")
        await input_handler_instance._process_event("   ")
    
    async def test_process_event_unknown(self, input_handler_instance):
        """Test processing unknown event."""
        from app.websocket_manager import websocket_manager
        from unittest.mock import AsyncMock, patch
        
        # Mock the broadcast method
        with patch.object(websocket_manager, 'broadcast', new_callable=AsyncMock, return_value=1):
            # Unknown event should not trigger broadcast
            await input_handler_instance._process_event("UNKNOWN_EVENT")
            
            # Broadcast should not be called
            websocket_manager.broadcast.assert_not_called()
    
    async def test_process_event_with_whitespace(self, input_handler_instance):
        """Test processing event with whitespace."""
        from app.websocket_manager import websocket_manager
        from unittest.mock import AsyncMock, patch
        
        # Mock the broadcast method
        with patch.object(websocket_manager, 'broadcast', new_callable=AsyncMock, return_value=1):
            await input_handler_instance._process_event("  GORE_EVENT  ")
            
            # Should still process correctly
            websocket_manager.broadcast.assert_called_once()
    
    async def test_add_event_mapping(self, input_handler_instance):
        """Test adding custom event mapping."""
        input_handler_instance.add_event_mapping("CUSTOM_EVENT", OutputEvent.GORE_FLASH)
        
        assert "CUSTOM_EVENT" in input_handler_instance.event_mapping
        assert input_handler_instance.event_mapping["CUSTOM_EVENT"] == OutputEvent.GORE_FLASH
    
    async def test_add_event_mapping_overwrites(self, input_handler_instance):
        """Test adding mapping overwrites existing."""
        original_mapping = input_handler_instance.event_mapping["GORE_EVENT"]
        
        input_handler_instance.add_event_mapping("GORE_EVENT", OutputEvent.DAMAGE_PULSE)
        
        assert input_handler_instance.event_mapping["GORE_EVENT"] == OutputEvent.DAMAGE_PULSE
        assert input_handler_instance.event_mapping["GORE_EVENT"] != original_mapping
    
    async def test_remove_event_mapping(self, input_handler_instance):
        """Test removing event mapping."""
        assert "GORE_EVENT" in input_handler_instance.event_mapping
        
        input_handler_instance.remove_event_mapping("GORE_EVENT")
        
        assert "GORE_EVENT" not in input_handler_instance.event_mapping
    
    async def test_remove_nonexistent_mapping(self, input_handler_instance):
        """Test removing nonexistent mapping."""
        # Should not raise error
        input_handler_instance.remove_event_mapping("NONEXISTENT_EVENT")
    
    async def test_get_event_mappings(self, input_handler_instance):
        """Test getting all event mappings."""
        mappings = input_handler_instance.get_event_mappings()
        
        assert isinstance(mappings, dict)
        assert len(mappings) == 8
        assert "GORE_EVENT" in mappings
        assert mappings["GORE_EVENT"] == "GORE_FLASH"
    
    async def test_process_loop_integration(self, input_handler_instance):
        """Test process loop integration with event queue."""
        from app.state import system_state
        from app.websocket_manager import websocket_manager
        from unittest.mock import AsyncMock, patch
        
        # Mock the broadcast method
        with patch.object(websocket_manager, 'broadcast', new_callable=AsyncMock, return_value=1):
            # Start handler
            await input_handler_instance.start()
            
            # Put events in queue
            await system_state.event_queue.put("GORE_EVENT")
            await system_state.event_queue.put("DAMAGE_EVENT")
            
            # Wait for processing
            await asyncio.sleep(0.2)
            
            # Verify events were processed
            assert websocket_manager.broadcast.call_count >= 1
            
            # Stop handler
            await input_handler_instance.stop()
    
    async def test_process_loop_timeout(self, input_handler_instance):
        """Test process loop handles timeout gracefully."""
        from app.state import system_state
        
        # Start handler
        await input_handler_instance.start()
        
        # Queue is empty, should timeout and continue
        await asyncio.sleep(0.2)
        
        # Should still be running
        assert input_handler_instance._is_running is True
        
        # Stop handler
        await input_handler_instance.stop()
    
    async def test_start_stop_lifecycle(self, input_handler_instance):
        """Test complete start/stop lifecycle."""
        # Initial state
        assert input_handler_instance._is_running is False
        assert input_handler_instance._process_task is None
        
        # Start
        await input_handler_instance.start()
        assert input_handler_instance._is_running is True
        assert input_handler_instance._process_task is not None
        
        # Stop
        await input_handler_instance.stop()
        assert input_handler_instance._is_running is False
        # Task may be cancelled but not None, check if done or cancelled
        assert input_handler_instance._process_task is None or input_handler_instance._process_task.done()
    
    async def test_all_default_events_mapped(self, input_handler_instance):
        """Test all default events are mapped correctly."""
        expected_mappings = {
            "GORE_EVENT": OutputEvent.GORE_FLASH,
            "DAMAGE_EVENT": OutputEvent.DAMAGE_PULSE,
            "KILL_EVENT": OutputEvent.KILL_STREAK,
            "COMBO_EVENT": OutputEvent.COMBO_HIT,
            "CRITICAL_EVENT": OutputEvent.CRITICAL_HIT,
            "ADRENALINE_EVENT": OutputEvent.ADRENALINE,
            "LOW_HEALTH_EVENT": OutputEvent.LOW_HEALTH,
            "DEATH_EVENT": OutputEvent.DEATH
        }
        
        for log_event, output_event in expected_mappings.items():
            assert input_handler_instance.event_mapping[log_event] == output_event
    
    @pytest.mark.parametrize("log_event,output_event", [
        ("GORE_EVENT", OutputEvent.GORE_FLASH),
        ("DAMAGE_EVENT", OutputEvent.DAMAGE_PULSE),
        ("KILL_EVENT", OutputEvent.KILL_STREAK),
        ("COMBO_EVENT", OutputEvent.COMBO_HIT),
        ("CRITICAL_EVENT", OutputEvent.CRITICAL_HIT),
        ("ADRENALINE_EVENT", OutputEvent.ADRENALINE),
        ("LOW_HEALTH_EVENT", OutputEvent.LOW_HEALTH),
        ("DEATH_EVENT", OutputEvent.DEATH)
    ])
    async def test_each_event_mapping(self, input_handler_instance, log_event, output_event):
        """Test each event mapping individually."""
        from app.websocket_manager import websocket_manager
        from unittest.mock import AsyncMock, patch
        
        # Mock the broadcast method
        with patch.object(websocket_manager, 'broadcast', new_callable=AsyncMock, return_value=1):
            await input_handler_instance._process_event(log_event)
            
            # Verify broadcast was called
            websocket_manager.broadcast.assert_called_once()
            
            # Get the message that was broadcast
            call_args = websocket_manager.broadcast.call_args
            message = call_args[0][0]
            
            # Verify message format
            assert message.startswith("OUTPUT:")
            assert output_event.value in message
