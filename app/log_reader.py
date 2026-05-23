"""
Async RAM disk log reader for Cyber-Visceral Link.
"""
import asyncio
import logging
import os
from typing import Optional, AsyncIterator
from datetime import datetime

from app.config import settings
from app.state import system_state

logger = logging.getLogger(__name__)


class AsyncLogReader:
    """Non-blocking log reader for RAM disk files."""
    
    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path or settings.ram_disk_log_path
        self.file_handle: Optional[asyncio.FileIO] = None
        self.file_position: int = 0
        self._is_running: bool = False
        self._read_task: Optional[asyncio.Task] = None
        self._last_check: Optional[datetime] = None
    
    async def start(self) -> None:
        """Start the log reader."""
        if self._is_running:
            logger.warning("[LOG READER] Already running")
            return
        
        self._is_running = True
        self._read_task = asyncio.create_task(self._read_loop())
        logger.info(f"[LOG READER] Started monitoring {self.log_path}")
    
    async def stop(self) -> None:
        """Stop the log reader."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self.file_handle:
            try:
                self.file_handle.close()
            except Exception as e:
                logger.error(f"Error closing file handle: {e}")
            self.file_handle = None
        
        logger.info("[LOG READER] Stopped")
    
    async def _ensure_file_exists(self) -> bool:
        """Ensure log file exists, create if not."""
        try:
            if not os.path.exists(self.log_path):
                # Create empty file
                with open(self.log_path, 'a') as f:
                    pass
                logger.info(f"[LOG READER] Created log file: {self.log_path}")
                self.file_position = 0
                return True
            
            # Check if file was truncated
            current_size = os.path.getsize(self.log_path)
            if current_size < self.file_position:
                logger.warning(f"[LOG READER] File truncated, resetting position")
                self.file_position = 0
            
            return True
        except Exception as e:
            logger.error(f"[LOG READER] Error ensuring file exists: {e}")
            return False
    
    async def _read_loop(self) -> None:
        """Main read loop."""
        poll_interval = 0.1  # 100ms poll interval
        
        while self._is_running:
            try:
                await asyncio.sleep(poll_interval)
                
                # Ensure file exists
                if not await self._ensure_file_exists():
                    continue
                
                # Read new content
                async for line in self._read_new_lines():
                    await system_state.event_queue.put(line)
                    await system_state.increment_events_processed()
                    logger.debug(f"[LOG READER] New event: {line.strip()}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[LOG READER] Error in read loop: {e}")
                await asyncio.sleep(1)  # Back off on error
    
    async def _read_new_lines(self) -> AsyncIterator[str]:
        """
        Read new lines from the log file.
        
        Yields:
            New lines since last read
        """
        try:
            # Open file in read mode
            with open(self.log_path, 'r') as f:
                # Seek to last position
                f.seek(self.file_position)
                
                # Read new content
                new_content = f.read()
                
                # Update position
                self.file_position = f.tell()
                
                # Split into lines
                if new_content:
                    lines = new_content.split('\n')
                    for line in lines:
                        if line.strip():  # Skip empty lines
                            yield line
        
        except FileNotFoundError:
            logger.warning(f"[LOG READER] File not found: {self.log_path}")
            self.file_position = 0
        except Exception as e:
            logger.error(f"[LOG READER] Error reading file: {e}")
    
    async def read_all(self) -> list[str]:
        """
        Read all current content from the log file.
        
        Returns:
            List of all lines in the file
        """
        try:
            if not os.path.exists(self.log_path):
                return []
            
            with open(self.log_path, 'r') as f:
                content = f.read()
                self.file_position = f.tell()
                return [line for line in content.split('\n') if line.strip()]
        
        except Exception as e:
            logger.error(f"[LOG READER] Error reading all: {e}")
            return []
    
    def get_stats(self) -> dict:
        """Get reader statistics."""
        return {
            "log_path": self.log_path,
            "file_position": self.file_position,
            "is_running": self._is_running,
            "file_exists": os.path.exists(self.log_path) if self.log_path else False,
            "file_size": os.path.getsize(self.log_path) if self.log_path and os.path.exists(self.log_path) else 0
        }


# Global reader instance
log_reader = AsyncLogReader()
