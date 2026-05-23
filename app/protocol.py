"""
Message protocol definitions for Cyber-Visceral Link.
"""
from enum import Enum
from typing import Optional, Dict, Any
import re


class MessageType(str, Enum):
    """Message type enumeration."""
    OUTPUT = "OUTPUT"
    INPUT = "INPUT"
    HEARTBEAT = "HEARTBEAT"
    ERROR = "ERROR"


class OutputEvent(str, Enum):
    """Output event types sent to ESP32."""
    GORE_FLASH = "GORE_FLASH"
    DAMAGE_PULSE = "DAMAGE_PULSE"
    KILL_STREAK = "KILL_STREAK"
    COMBO_HIT = "COMBO_HIT"
    CRITICAL_HIT = "CRITICAL_HIT"
    ADRENALINE = "ADRENALINE"
    LOW_HEALTH = "LOW_HEALTH"
    DEATH = "DEATH"


class InputEvent(str, Enum):
    """Input event types received from ESP32."""
    PANIC_BUTTON = "PANIC_BUTTON"
    QUICK_SAVE = "QUICK_SAVE"
    QUICK_LOAD = "QUICK_LOAD"
    DODGE_LEFT = "DODGE_LEFT"
    DODGE_RIGHT = "DODGE_RIGHT"
    ATTACK = "ATTACK"
    SIGN = "SIGN"


class ProtocolError(Exception):
    """Protocol-specific errors."""
    pass


class MessageParser:
    """Parse and validate protocol messages."""
    
    # Pattern: TYPE:EVENT[:optional_data]
    MESSAGE_PATTERN = re.compile(r'^([A-Z_]+):([A-Z_]+)(?::(.+))?$')
    
    @staticmethod
    def parse(message: str) -> Dict[str, Any]:
        """
        Parse a protocol message.
        
        Args:
            message: Raw message string (e.g., "OUTPUT:GORE_FLASH")
            
        Returns:
            Dictionary with message_type, event, and optional data
            
        Raises:
            ProtocolError: If message format is invalid
        """
        message = message.strip()
        
        if not message:
            raise ProtocolError("Empty message")
        
        match = MessageParser.MESSAGE_PATTERN.match(message)
        if not match:
            raise ProtocolError(f"Invalid message format: {message}")
        
        message_type, event, data = match.groups()
        
        return {
            "message_type": message_type,
            "event": event,
            "data": data
        }
    
    @staticmethod
    def format_output(event: OutputEvent, data: Optional[str] = None) -> str:
        """
        Format an output message.
        
        Args:
            event: Output event type
            data: Optional data string
            
        Returns:
            Formatted message string
        """
        if data:
            return f"OUTPUT:{event.value}:{data}"
        return f"OUTPUT:{event.value}"
    
    @staticmethod
    def format_input(event: InputEvent, data: Optional[str] = None) -> str:
        """
        Format an input message.
        
        Args:
            event: Input event type
            data: Optional data string
            
        Returns:
            Formatted message string
        """
        if data:
            return f"INPUT:{event.value}:{data}"
        return f"INPUT:{event.value}"
    
    @staticmethod
    def validate_payload(message: str, max_size: int = 64) -> bool:
        """
        Validate message payload size.
        
        Args:
            message: Message to validate
            max_size: Maximum allowed size in bytes
            
        Returns:
            True if valid, False otherwise
        """
        return len(message.encode('utf-8')) <= max_size
