"""
MCP Logger for ComfyUI Integration

Provides structured logging for MCP workflow operations with:
- In-memory log buffer for ComfyUI to query
- Structured log entries with timestamps and metadata
- Log level filtering
- Thread-safe operations
"""

import logging
import threading
from collections import deque
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class LogLevel(str, Enum):
    """Log levels for MCP operations"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class MCPLogEntry:
    """Structured log entry for MCP operations"""

    def __init__(
        self,
        level: LogLevel,
        operation: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ):
        self.timestamp = datetime.utcnow().isoformat()
        self.level = level
        self.operation = operation
        self.message = message
        self.details = details or {}
        self.workflow_id = workflow_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp,
            "level": self.level.value,
            "operation": self.operation,
            "message": self.message,
            "details": self.details,
            "workflow_id": self.workflow_id
        }

    def to_log_string(self) -> str:
        """Convert to human-readable log string"""
        workflow_prefix = f"[{self.workflow_id[:8]}] " if self.workflow_id else ""
        details_str = f" | {self.details}" if self.details else ""
        return f"[MCP:{self.level.value.upper()}] {workflow_prefix}{self.operation}: {self.message}{details_str}"


class MCPLogger:
    """
    Thread-safe logger for MCP operations with in-memory buffer.

    Maintains a circular buffer of recent log entries that ComfyUI can query.
    """

    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self.entries: deque[MCPLogEntry] = deque(maxlen=max_entries)
        self.lock = threading.Lock()

        # Setup Python logger integration
        self.py_logger = logging.getLogger("mcp_workflow")
        self.py_logger.setLevel(logging.DEBUG)

        # Add console handler if not already present
        if not self.py_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.py_logger.addHandler(handler)

    def log(
        self,
        level: LogLevel,
        operation: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ) -> None:
        """Add a log entry"""
        entry = MCPLogEntry(level, operation, message, details, workflow_id)

        with self.lock:
            self.entries.append(entry)

        # Also log to Python logger
        log_str = entry.to_log_string()
        if level == LogLevel.DEBUG:
            self.py_logger.debug(log_str)
        elif level == LogLevel.INFO:
            self.py_logger.info(log_str)
        elif level == LogLevel.WARNING:
            self.py_logger.warning(log_str)
        elif level == LogLevel.ERROR:
            self.py_logger.error(log_str)

    def debug(self, operation: str, message: str, **kwargs) -> None:
        """Log debug message"""
        self.log(LogLevel.DEBUG, operation, message, **kwargs)

    def info(self, operation: str, message: str, **kwargs) -> None:
        """Log info message"""
        self.log(LogLevel.INFO, operation, message, **kwargs)

    def warning(self, operation: str, message: str, **kwargs) -> None:
        """Log warning message"""
        self.log(LogLevel.WARNING, operation, message, **kwargs)

    def error(self, operation: str, message: str, **kwargs) -> None:
        """Log error message"""
        self.log(LogLevel.ERROR, operation, message, **kwargs)

    def get_recent(
        self,
        count: int = 100,
        level: Optional[LogLevel] = None,
        workflow_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent log entries.

        Args:
            count: Maximum number of entries to return
            level: Filter by log level (None = all levels)
            workflow_id: Filter by workflow ID (None = all workflows)

        Returns:
            List of log entry dictionaries
        """
        with self.lock:
            entries = list(self.entries)

        # Filter by level
        if level:
            entries = [e for e in entries if e.level == level]

        # Filter by workflow_id
        if workflow_id:
            entries = [e for e in entries if e.workflow_id == workflow_id]

        # Return most recent entries
        return [e.to_dict() for e in entries[-count:]]

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all log entries in buffer"""
        with self.lock:
            return [e.to_dict() for e in self.entries]

    def clear(self) -> None:
        """Clear all log entries"""
        with self.lock:
            self.entries.clear()
        self.info("system", "Log buffer cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        with self.lock:
            entries = list(self.entries)

        total = len(entries)
        by_level = {
            "debug": len([e for e in entries if e.level == LogLevel.DEBUG]),
            "info": len([e for e in entries if e.level == LogLevel.INFO]),
            "warning": len([e for e in entries if e.level == LogLevel.WARNING]),
            "error": len([e for e in entries if e.level == LogLevel.ERROR])
        }

        by_operation = {}
        for entry in entries:
            by_operation[entry.operation] = by_operation.get(entry.operation, 0) + 1

        return {
            "total_entries": total,
            "max_entries": self.max_entries,
            "by_level": by_level,
            "by_operation": by_operation,
            "oldest_timestamp": entries[0].timestamp if entries else None,
            "newest_timestamp": entries[-1].timestamp if entries else None
        }


# Global logger instance
_logger = MCPLogger()


def get_logger() -> MCPLogger:
    """Get the global MCP logger instance"""
    return _logger
