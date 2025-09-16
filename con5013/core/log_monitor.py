"""
Con5013 Log Monitor
Real-time log monitoring and management for Flask applications.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from collections import deque

class LogMonitor:
    """
    Real-time log monitoring system for Con5013.
    
    Provides standardized log reading from multiple sources with
    filtering, searching, and real-time updates.
    """
    
    def __init__(self, app, config):
        self.app = app
        self.config = config
        self.log_sources = {}
        self.log_buffers = {}
        self.max_entries = config.get('CON5013_MAX_LOG_ENTRIES', 1000)
        # Logger name to source alias mapping (prefix-based)
        self.logger_aliases = {
            'flask.app': 'flask',
            'flask': 'flask',
            'werkzeug': 'werkzeug',
            'crawl4ai': 'crawl4ai',
            'con5013': 'CON5013',
        }
        # Alias this app's logger name to 'flask' for convenience
        try:
            app_logger_name = getattr(self.app, 'logger', None).name if hasattr(self.app, 'logger') else None
            if app_logger_name:
                self.logger_aliases[app_logger_name] = 'flask'
        except Exception:
            pass
        
        # Initialize log sources
        self._initialize_sources()
        
        # Set up logging integration (Flask app or root logger)
        self._handler = Con5013LogHandler(self)
        self._attached_targets = set()
        self._setup_flask_integration()
    
    def _initialize_sources(self):
        """Initialize log sources from configuration."""
        sources = self.config.get('CON5013_LOG_SOURCES', ['app.log'])
        
        for source in sources:
            if isinstance(source, str):
                # Simple file path
                self.add_source('app', source)
            elif isinstance(source, dict):
                # Source with name and optional path (virtual names allowed)
                name = source.get('name', 'app')
                path = source.get('path')
                if path:
                    self.add_source(name, path)
                else:
                    # Ensure buffer exists so it appears in source list
                    if name not in self.log_buffers:
                        self.log_buffers[name] = deque(maxlen=self.max_entries)
    
    def _setup_flask_integration(self):
        """Set up integration with Python logging subsystem."""
        handler = self._handler
        handler.setLevel(logging.DEBUG)
        try:
            if self.config.get('CON5013_CAPTURE_ROOT_LOGGER', True):
                root_logger = logging.getLogger()
                if 'root' not in self._attached_targets:
                    root_logger.addHandler(handler)
                    self._attached_targets.add('root')
            else:
                if 'app' not in self._attached_targets:
                    self.app.logger.addHandler(handler)
                    self._attached_targets.add('app')

            # Optionally attach to specific named loggers (e.g., werkzeug)
            extra_loggers = self.config.get('CON5013_CAPTURE_LOGGERS', []) or []
            for lname in extra_loggers:
                try:
                    lg = logging.getLogger(lname)
                    # If capturing root and this logger propagates, skip to avoid duplicates
                    if self.config.get('CON5013_CAPTURE_ROOT_LOGGER', True) and getattr(lg, 'propagate', True):
                        continue
                    key = f"logger:{lname}"
                    if key not in self._attached_targets:
                        lg.addHandler(handler)
                        self._attached_targets.add(key)
                except Exception:
                    continue
        except Exception as e:
            # Avoid breaking app on logging attach issues
            try:
                self.app.logger.error(f"Con5013 logging integration error: {e}")
            except Exception:
                pass
    
    def add_source(self, name: str, path: str):
        """Add a new log source to monitor."""
        self.log_sources[name] = {
            'path': path,
            'last_position': 0,
            'last_modified': 0
        }
        
        # Initialize buffer for this source
        if name not in self.log_buffers:
            self.log_buffers[name] = deque(maxlen=self.max_entries)
        
        # Read existing content if file exists
        if os.path.exists(path):
            self._read_file_content(name)
    
    def _read_file_content(self, source_name: str):
        """Read content from a log file."""
        source = self.log_sources.get(source_name)
        if not source:
            return
        
        path = source['path']
        if not os.path.exists(path):
            return
        
        try:
            # Check if file was modified
            current_modified = os.path.getmtime(path)
            if current_modified <= source['last_modified']:
                return
            
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                # Seek to last position
                f.seek(source['last_position'])
                
                # Read new lines
                new_lines = f.readlines()
                
                # Update position and timestamp
                source['last_position'] = f.tell()
                source['last_modified'] = current_modified
                
                # Process new lines
                for line in new_lines:
                    self._process_log_line(source_name, line.strip())
                    
        except Exception as e:
            self.app.logger.error(f"Error reading log file {path}: {e}")
    
    def _process_log_line(self, source: str, line: str):
        """Process a single log line and add to buffer."""
        if not line:
            return
        
        # Parse log line (basic parsing, can be enhanced)
        log_entry = {
            'timestamp': time.time(),
            'source': source,
            'level': self._extract_log_level(line),
            'message': line,
            'raw': line
        }
        
        # Add to buffer
        self.log_buffers[source].append(log_entry)
    
    def _extract_log_level(self, line: str) -> str:
        """Extract log level from log line."""
        line_upper = line.upper()
        
        for level in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
            if level in line_upper:
                return level
        
        return 'INFO'  # Default level
    
    def get_logs(self, source: str = 'app', limit: int = 100, level: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get logs from a specific source."""
        # Update file content first
        if source in self.log_sources:
            self._read_file_content(source)
        
        # Get logs from buffer
        buffer = self.log_buffers.get(source, deque())
        logs = list(buffer)
        
        # Filter by level if specified
        if level:
            logs = [log for log in logs if log.get('level') == level.upper()]
        
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # Apply limit
        return logs[:limit]
    
    def get_available_sources(self) -> List[str]:
        """Get list of available log sources."""
        sources = set(self.log_sources.keys())
        # Include any sources that have appeared via logger handler
        sources.update(self.log_buffers.keys())
        # Always include the in-memory 'flask' source alias for convenience
        sources.add('flask')
        # Include CON5013 if present in aliases/buffers
        if any(k.startswith('con5013') for k in self.logger_aliases.keys()) or 'CON5013' in self.log_buffers:
            sources.add('CON5013')
        return sorted(sources)
    
    def clear_logs(self, source: str):
        """Clear logs for a specific source."""
        if source in self.log_buffers:
            self.log_buffers[source].clear()
    
    def add_log_entry(self, source: str, level: str, message: str):
        """Manually add a log entry."""
        log_entry = {
            'timestamp': time.time(),
            'source': source,
            'level': level.upper(),
            'message': message,
            'raw': f"{time.strftime('%Y-%m-%d %H:%M:%S')} {level.upper()} {message}"
        }
        
        if source not in self.log_buffers:
            self.log_buffers[source] = deque(maxlen=self.max_entries)
        
        self.log_buffers[source].append(log_entry)
    
    def get_flask_handler(self):
        """Get a Flask log handler that integrates with Con5013."""
        return self._handler

    # External integration helpers
    def attach_logger(self, logger_name: str, alias: Optional[str] = None):
        """Attach Con5013 handler to a named logger (e.g., 'crawl4ai').

        If alias is provided, logs from that logger will appear under the alias
        as the source name in the UI. Avoid duplicates when root capture is on.
        """
        if alias:
            self.logger_aliases[logger_name] = alias
        try:
            lg = logging.getLogger(logger_name)
            # Skip if root capture and logger propagates to root
            if self.config.get('CON5013_CAPTURE_ROOT_LOGGER', True) and getattr(lg, 'propagate', True):
                return
            key = f"logger:{logger_name}"
            if key in getattr(self, '_attached_targets', set()):
                return
            lg.addHandler(self._handler)
            self._attached_targets.add(key)
        except Exception:
            pass

    def set_logger_alias(self, prefix: str, alias: str):
        """Define or override a logger prefix alias to a source name."""
        self.logger_aliases[prefix] = alias

    def _derive_source_from_logger(self, logger_name: str) -> str:
        """Map a logger name to a source label using aliases/prefixes."""
        for prefix, alias in self.logger_aliases.items():
            if logger_name.startswith(prefix):
                return alias
        # Fallback to the top-level logger segment
        return logger_name.split('.')[0] if logger_name else 'app'

class Con5013LogHandler(logging.Handler):
    """Custom logging handler that feeds logs into Con5013."""
    
    def __init__(self, log_monitor: LogMonitor):
        super().__init__()
        self.log_monitor = log_monitor
    
    def emit(self, record):
        """Emit a log record."""
        try:
            message = self.format(record)
            source = self.log_monitor._derive_source_from_logger(getattr(record, 'name', 'app'))
            self.log_monitor.add_log_entry(source=source, level=record.levelname, message=message)
        except Exception:
            self.handleError(record)
