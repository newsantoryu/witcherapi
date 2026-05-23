"""
Unit tests for protocol module.
"""
import pytest

from app.protocol import (
    MessageParser,
    OutputEvent,
    InputEvent,
    ProtocolError,
    MessageType
)


@pytest.mark.unit
class TestMessageParser:
    """Test message parsing."""
    
    def test_parse_output_message(self):
        """Test parsing output message."""
        message = "OUTPUT:GORE_FLASH"
        parsed = MessageParser.parse(message)
        
        assert parsed["message_type"] == "OUTPUT"
        assert parsed["event"] == "GORE_FLASH"
        assert parsed["data"] is None
    
    def test_parse_input_message(self):
        """Test parsing input message."""
        message = "INPUT:PANIC_BUTTON"
        parsed = MessageParser.parse(message)
        
        assert parsed["message_type"] == "INPUT"
        assert parsed["event"] == "PANIC_BUTTON"
        assert parsed["data"] is None
    
    def test_parse_message_with_data(self):
        """Test parsing message with optional data."""
        message = "OUTPUT:GORE_FLASH:intensity:high"
        parsed = MessageParser.parse(message)
        
        assert parsed["message_type"] == "OUTPUT"
        assert parsed["event"] == "GORE_FLASH"
        assert parsed["data"] == "intensity:high"
    
    def test_parse_empty_message(self):
        """Test parsing empty message raises error."""
        with pytest.raises(ProtocolError, match="Empty message"):
            MessageParser.parse("")
    
    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only message raises error."""
        with pytest.raises(ProtocolError, match="Empty message"):
            MessageParser.parse("   ")
    
    def test_parse_invalid_format(self):
        """Test parsing invalid format raises error."""
        with pytest.raises(ProtocolError, match="Invalid message format"):
            MessageParser.parse("INVALID_MESSAGE")
    
    def test_parse_missing_colon(self):
        """Test parsing message without colon raises error."""
        with pytest.raises(ProtocolError, match="Invalid message format"):
            MessageParser.parse("OUTPUTGORE_FLASH")
    
    def test_parse_only_type(self):
        """Test parsing message with only type raises error."""
        with pytest.raises(ProtocolError, match="Invalid message format"):
            MessageParser.parse("OUTPUT:")
    
    def test_parse_all_output_events(self, sample_messages):
        """Test parsing all output event types."""
        output_events = [
            "OUTPUT:GORE_FLASH",
            "OUTPUT:DAMAGE_PULSE",
            "OUTPUT:KILL_STREAK",
            "OUTPUT:COMBO_HIT",
            "OUTPUT:CRITICAL_HIT",
            "OUTPUT:ADRENALINE",
            "OUTPUT:LOW_HEALTH",
            "OUTPUT:DEATH"
        ]
        
        for message in output_events:
            parsed = MessageParser.parse(message)
            assert parsed["message_type"] == "OUTPUT"
            assert parsed["event"] is not None
    
    def test_parse_all_input_events(self):
        """Test parsing all input event types."""
        input_events = [
            "INPUT:PANIC_BUTTON",
            "INPUT:QUICK_SAVE",
            "INPUT:QUICK_LOAD",
            "INPUT:DODGE_LEFT",
            "INPUT:DODGE_RIGHT",
            "INPUT:ATTACK",
            "INPUT:SIGN"
        ]
        
        for message in input_events:
            parsed = MessageParser.parse(message)
            assert parsed["message_type"] == "INPUT"
            assert parsed["event"] is not None
    
    def test_parse_unicode_message(self):
        """Test parsing message with Unicode characters."""
        message = "OUTPUT:GORE_FLASH:café:日本語"
        parsed = MessageParser.parse(message)
        
        assert parsed["message_type"] == "OUTPUT"
        assert parsed["event"] == "GORE_FLASH"
        assert parsed["data"] == "café:日本語"
    
    def test_parse_whitespace_handling(self):
        """Test parsing handles leading/trailing whitespace."""
        message = "  OUTPUT:GORE_FLASH  "
        parsed = MessageParser.parse(message)
        
        assert parsed["message_type"] == "OUTPUT"
        assert parsed["event"] == "GORE_FLASH"
    
    def test_format_output(self):
        """Test formatting output message."""
        message = MessageParser.format_output(OutputEvent.GORE_FLASH)
        assert message == "OUTPUT:GORE_FLASH"
    
    def test_format_output_with_data(self):
        """Test formatting output message with data."""
        message = MessageParser.format_output(OutputEvent.GORE_FLASH, "intensity:high")
        assert message == "OUTPUT:GORE_FLASH:intensity:high"
    
    def test_format_input(self):
        """Test formatting input message."""
        message = MessageParser.format_input(InputEvent.PANIC_BUTTON)
        assert message == "INPUT:PANIC_BUTTON"
    
    def test_format_input_with_data(self):
        """Test formatting input message with data."""
        message = MessageParser.format_input(InputEvent.PANIC_BUTTON, "timestamp:123456")
        assert message == "INPUT:PANIC_BUTTON:timestamp:123456"
    
    def test_validate_payload_valid(self):
        """Test payload validation with valid size."""
        message = "OUTPUT:GORE_FLASH"
        assert MessageParser.validate_payload(message, 64) is True
    
    def test_validate_payload_invalid(self):
        """Test payload validation with invalid size."""
        message = "OUTPUT:GORE_FLASH" * 10  # Make it large
        assert MessageParser.validate_payload(message, 64) is False
    
    def test_validate_payload_exact_limit(self):
        """Test payload validation at exact limit."""
        message = "OUTPUT:GORE_FLASH"
        exact_size = len(message.encode('utf-8'))
        assert MessageParser.validate_payload(message, exact_size) is True
    
    def test_validate_payload_one_byte_over(self):
        """Test payload validation one byte over limit."""
        message = "OUTPUT:GORE_FLASH"
        exact_size = len(message.encode('utf-8'))
        assert MessageParser.validate_payload(message, exact_size - 1) is False
    
    def test_format_parse_consistency(self):
        """Test that format and parse are consistent."""
        original_event = OutputEvent.DAMAGE_PULSE
        formatted = MessageParser.format_output(original_event)
        parsed = MessageParser.parse(formatted)
        
        assert parsed["message_type"] == "OUTPUT"
        assert parsed["event"] == original_event.value
    
    def test_format_parse_consistency_with_data(self):
        """Test format/parse consistency with data."""
        original_event = OutputEvent.GORE_FLASH
        data = "intensity:high"
        formatted = MessageParser.format_output(original_event, data)
        parsed = MessageParser.parse(formatted)
        
        assert parsed["message_type"] == "OUTPUT"
        assert parsed["event"] == original_event.value
        assert parsed["data"] == data


@pytest.mark.unit
class TestOutputEvent:
    """Test output event enum."""
    
    def test_output_events_values(self):
        """Test all output events have correct values."""
        assert OutputEvent.GORE_FLASH.value == "GORE_FLASH"
        assert OutputEvent.DAMAGE_PULSE.value == "DAMAGE_PULSE"
        assert OutputEvent.KILL_STREAK.value == "KILL_STREAK"
        assert OutputEvent.COMBO_HIT.value == "COMBO_HIT"
        assert OutputEvent.CRITICAL_HIT.value == "CRITICAL_HIT"
        assert OutputEvent.ADRENALINE.value == "ADRENALINE"
        assert OutputEvent.LOW_HEALTH.value == "LOW_HEALTH"
        assert OutputEvent.DEATH.value == "DEATH"
    
    def test_output_events_count(self):
        """Test all output events are defined."""
        assert len(OutputEvent) == 8
    
    @pytest.mark.parametrize("event", [
        OutputEvent.GORE_FLASH,
        OutputEvent.DAMAGE_PULSE,
        OutputEvent.KILL_STREAK,
        OutputEvent.COMBO_HIT,
        OutputEvent.CRITICAL_HIT,
        OutputEvent.ADRENALINE,
        OutputEvent.LOW_HEALTH,
        OutputEvent.DEATH
    ])
    def test_all_output_events_format(self, event):
        """Test all output events can be formatted."""
        message = MessageParser.format_output(event)
        assert message.startswith("OUTPUT:")
        assert event.value in message


@pytest.mark.unit
class TestInputEvent:
    """Test input event enum."""
    
    def test_input_events_values(self):
        """Test all input events have correct values."""
        assert InputEvent.PANIC_BUTTON.value == "PANIC_BUTTON"
        assert InputEvent.QUICK_SAVE.value == "QUICK_SAVE"
        assert InputEvent.QUICK_LOAD.value == "QUICK_LOAD"
        assert InputEvent.DODGE_LEFT.value == "DODGE_LEFT"
        assert InputEvent.DODGE_RIGHT.value == "DODGE_RIGHT"
        assert InputEvent.ATTACK.value == "ATTACK"
        assert InputEvent.SIGN.value == "SIGN"
    
    def test_input_events_count(self):
        """Test all input events are defined."""
        assert len(InputEvent) == 7
    
    @pytest.mark.parametrize("event", [
        InputEvent.PANIC_BUTTON,
        InputEvent.QUICK_SAVE,
        InputEvent.QUICK_LOAD,
        InputEvent.DODGE_LEFT,
        InputEvent.DODGE_RIGHT,
        InputEvent.ATTACK,
        InputEvent.SIGN
    ])
    def test_all_input_events_format(self, event):
        """Test all input events can be formatted."""
        message = MessageParser.format_input(event)
        assert message.startswith("INPUT:")
        assert event.value in message


@pytest.mark.unit
class TestMessageType:
    """Test message type enum."""
    
    def test_message_types_values(self):
        """Test all message types have correct values."""
        assert MessageType.OUTPUT.value == "OUTPUT"
        assert MessageType.INPUT.value == "INPUT"
        assert MessageType.HEARTBEAT.value == "HEARTBEAT"
        assert MessageType.ERROR.value == "ERROR"
    
    def test_message_types_count(self):
        """Test all message types are defined."""
        assert len(MessageType) == 4


@pytest.mark.unit
class TestProtocolError:
    """Test ProtocolError exception."""
    
    def test_protocol_error_creation(self):
        """Test ProtocolError can be created."""
        error = ProtocolError("Test error")
        assert str(error) == "Test error"
    
    def test_protocol_error_is_exception(self):
        """Test ProtocolError is an Exception."""
        assert issubclass(ProtocolError, Exception)
    
    def test_protocol_error_can_be_raised(self):
        """Test ProtocolError can be raised."""
        with pytest.raises(ProtocolError):
            raise ProtocolError("Test error")
