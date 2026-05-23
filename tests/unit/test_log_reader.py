"""
Unit tests for log reader module.
"""
import pytest
import asyncio
from pathlib import Path

from app.log_reader import AsyncLogReader


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncLogReader:
    """Test AsyncLogReader class."""
    
    async def test_reader_initialization(self, log_reader_instance):
        """Test AsyncLogReader initializes correctly."""
        assert log_reader_instance.log_path is not None
        assert log_reader_instance.file_position == 0
        assert log_reader_instance._is_running is False
        assert log_reader_instance._read_task is None
    
    async def test_reader_initialization_with_custom_path(self, tmp_path):
        """Test AsyncLogReader with custom log path."""
        custom_path = tmp_path / "custom.log"
        reader = AsyncLogReader(str(custom_path))
        assert reader.log_path == str(custom_path)
    
    async def test_start_already_running(self, log_reader_instance):
        """Test starting reader when already running."""
        await log_reader_instance.start()
        await log_reader_instance.start()  # Should not raise error
        await log_reader_instance.stop()
    
    async def test_stop_not_running(self, log_reader_instance):
        """Test stopping reader when not running."""
        # Should not raise error
        await log_reader_instance.stop()
    
    async def test_ensure_file_exists_creates(self, log_reader_instance):
        """Test creating log file if it doesn't exist."""
        # File should not exist initially
        assert not Path(log_reader_instance.log_path).exists()
        
        # Ensure file exists
        result = await log_reader_instance._ensure_file_exists()
        
        assert result is True
        assert Path(log_reader_instance.log_path).exists()
    
    async def test_ensure_file_exists_existing(self, temp_log_file):
        """Test ensuring file exists when it already exists."""
        reader = AsyncLogReader(temp_log_file)
        result = await reader._ensure_file_exists()
        assert result is True
    
    async def test_ensure_file_exists_truncated(self, log_reader_instance, tmp_path):
        """Test detecting file truncation."""
        # Create file and set position
        await log_reader_instance._ensure_file_exists()
        log_reader_instance.file_position = 1000
        
        # Truncate file
        Path(log_reader_instance.log_path).write_text("")
        
        # Should detect truncation and reset position
        result = await log_reader_instance._ensure_file_exists()
        assert result is True
        assert log_reader_instance.file_position == 0
    
    async def test_read_new_lines(self, log_reader_instance, sample_log_content):
        """Test reading new lines from log file."""
        # Write sample content
        Path(log_reader_instance.log_path).write_text(sample_log_content)
        
        lines = []
        async for line in log_reader_instance._read_new_lines():
            lines.append(line)
        
        assert len(lines) == 5
        assert "GORE_EVENT" in lines[0]
        assert "DEATH_EVENT" in lines[4]
    
    async def test_read_new_lines_empty(self, log_reader_instance):
        """Test reading from empty file."""
        Path(log_reader_instance.log_path).write_text("")
        
        lines = []
        async for line in log_reader_instance._read_new_lines():
            lines.append(line)
        
        assert len(lines) == 0
    
    async def test_read_new_lines_incremental(self, log_reader_instance):
        """Test incremental reading (position tracking)."""
        # Write initial content
        Path(log_reader_instance.log_path).write_text("line1\nline2\n")
        
        # Read first batch
        lines1 = []
        async for line in log_reader_instance._read_new_lines():
            lines1.append(line)
        
        assert len(lines1) == 2
        assert log_reader_instance.file_position > 0
        
        # Add more content
        with open(log_reader_instance.log_path, 'a') as f:
            f.write("line3\nline4\n")
        
        # Read new content only
        lines2 = []
        async for line in log_reader_instance._read_new_lines():
            lines2.append(line)
        
        assert len(lines2) == 2
        assert "line3" in lines2
        assert "line4" in lines2
    
    async def test_read_all(self, log_reader_instance, sample_log_content):
        """Test reading all content from log file."""
        Path(log_reader_instance.log_path).write_text(sample_log_content)
        
        lines = await log_reader_instance.read_all()
        
        assert len(lines) == 5
        assert "GORE_EVENT" in lines[0]
    
    async def test_read_all_nonexistent(self, log_reader_instance):
        """Test reading all from nonexistent file."""
        # Remove file if it exists
        Path(log_reader_instance.log_path).unlink(missing_ok=True)
        
        lines = await log_reader_instance.read_all()
        
        assert lines == []
    
    async def test_get_stats(self, log_reader_instance):
        """Test getting reader statistics."""
        stats = log_reader_instance.get_stats()
        
        assert "log_path" in stats
        assert "file_position" in stats
        assert "is_running" in stats
        assert "file_exists" in stats
        assert "file_size" in stats
    
    async def test_get_stats_with_file(self, log_reader_instance):
        """Test stats when file exists."""
        Path(log_reader_instance.log_path).write_text("test content\n")
        
        stats = log_reader_instance.get_stats()
        
        assert stats["file_exists"] is True
        assert stats["file_size"] > 0
    
    async def test_get_stats_without_file(self, log_reader_instance):
        """Test stats when file doesn't exist."""
        Path(log_reader_instance.log_path).unlink(missing_ok=True)
        
        stats = log_reader_instance.get_stats()
        
        assert stats["file_exists"] is False
        assert stats["file_size"] == 0
    
    async def test_file_position_tracking(self, log_reader_instance):
        """Test file position is tracked correctly."""
        # Write content
        content = "line1\nline2\nline3\n"
        Path(log_reader_instance.log_path).write_text(content)
        
        # Initial position should be 0
        assert log_reader_instance.file_position == 0
        
        # Read content
        await log_reader_instance.read_all()
        
        # Position should be at end of file
        assert log_reader_instance.file_position == len(content)
    
    async def test_read_loop_integration(self, log_reader_instance):
        """Test read loop integration with event queue."""
        from app.state import system_state
        
        # Start reader
        await log_reader_instance.start()
        
        # Write to log file
        Path(log_reader_instance.log_path).write_text("GORE_EVENT\n")
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Check if event was queued
        assert system_state.event_queue.qsize() > 0
        
        # Stop reader
        await log_reader_instance.stop()
    
    async def test_read_loop_handles_missing_file(self, log_reader_instance):
        """Test read loop handles missing file gracefully."""
        from app.state import system_state
        
        # Start reader
        await log_reader_instance.start()
        
        # Remove file
        Path(log_reader_instance.log_path).unlink(missing_ok=True)
        
        # Wait for error handling
        await asyncio.sleep(0.2)
        
        # Should still be running
        assert log_reader_instance._is_running is True
        
        # Stop reader
        await log_reader_instance.stop()
    
    async def test_start_stop_lifecycle(self, log_reader_instance):
        """Test complete start/stop lifecycle."""
        # Initial state
        assert log_reader_instance._is_running is False
        assert log_reader_instance._read_task is None
        
        # Start
        await log_reader_instance.start()
        assert log_reader_instance._is_running is True
        assert log_reader_instance._read_task is not None
        
        # Stop
        await log_reader_instance.stop()
        assert log_reader_instance._is_running is False
        # Task may be cancelled but not None, check if done or cancelled
        assert log_reader_instance._read_task is None or log_reader_instance._read_task.done()
    
    async def test_read_loop_stops_on_cancel(self, log_reader_instance):
        """Test read loop stops when cancelled."""
        await log_reader_instance.start()
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Stop
        await log_reader_instance.stop()
        
        # Task should be done or cancelled
        assert log_reader_instance._read_task is None or log_reader_instance._read_task.done()
