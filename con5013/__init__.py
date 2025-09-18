"""
Con5013 - The Ultimate Flask Console Extension
Monitor, Debug, and Control Your Flask Applications

A powerful, beautiful web console that provides:
- Real-time application monitoring and logging
- Interactive terminal interface for live application control
- Comprehensive API discovery and testing
- System metrics and performance monitoring
- Beautiful overlay interface that works with any Flask app
"""

__version__ = "1.0.0"
__author__ = "Con5013 Team"
__license__ = "MIT"

import logging
import re
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

from flask import Flask, render_template_string, url_for

from .blueprint import con5013_blueprint
from .core.api_scanner import APIScanner
from .core.log_monitor import LogMonitor
from .core.system_monitor import SystemMonitor
from .core.terminal_engine import TerminalEngine

# Set up logging
logger = logging.getLogger(__name__)

class Con5013:
    """
    The Ultimate Flask Console Extension
    
    Provides comprehensive monitoring, debugging, and control capabilities
    for Flask applications through a beautiful web interface.
    
    Usage:
        # Simple integration
        app = Flask(__name__)
        console = Con5013(app)
        
        # Factory pattern
        console = Con5013()
        console.init_app(app)
        
        # With configuration
        console = Con5013(app, config={
            'CON5013_URL_PREFIX': '/admin/console',
            'CON5013_THEME': 'dark',
            'CON5013_ENABLE_TERMINAL': True,
            'CON5013_ENABLE_API_SCANNER': True,
            'CON5013_LOG_SOURCES': ['app.log', 'system.log'],
            'CON5013_CRAWL4AI_INTEGRATION': True
        })
    """
    
    def __init__(self, app=None, **kwargs):
        self.app = app
        self.config = self._get_default_config()
        self.config.update(kwargs.get('config', {}))
        
        # Core components
        self.log_monitor = None
        self.terminal_engine = None
        self.api_scanner = None
        self.system_monitor = None
        
        # Registry for custom system monitor boxes
        self._system_boxes: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

        if app is not None:
            self.init_app(app)
    
    def _get_default_config(self):
        """Get default configuration for Con5013."""
        return {
            # Core settings
            'CON5013_URL_PREFIX': '/con5013',
            'CON5013_THEME': 'dark',
            'CON5013_ENABLED': True,
            'CON5013_CAPTURE_ROOT_LOGGER': True,
            'CON5013_CAPTURE_LOGGERS': ['werkzeug', 'flask.app'],
            
            # Feature toggles
            'CON5013_ENABLE_LOGS': True,
            'CON5013_ENABLE_TERMINAL': True,
            'CON5013_ENABLE_API_SCANNER': True,
            'CON5013_ENABLE_SYSTEM_MONITOR': True,
            
            # Logging configuration
            'CON5013_LOG_SOURCES': ['app.log'],
            'CON5013_LOG_LEVELS': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            'CON5013_MAX_LOG_ENTRIES': 1000,
            'CON5013_REAL_TIME_LOGS': True,
            
            # Terminal configuration
            'CON5013_TERMINAL_HISTORY_SIZE': 100,
            'CON5013_TERMINAL_TIMEOUT': 30,
            'CON5013_CUSTOM_COMMANDS': {},
            
            # API Scanner configuration
            'CON5013_API_TEST_TIMEOUT': 10,
            'CON5013_API_INCLUDE_METHODS': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
            'CON5013_API_EXCLUDE_ENDPOINTS': ['/static', '/con5013'],
            
            # System monitoring
            'CON5013_SYSTEM_UPDATE_INTERVAL': 5,
            'CON5013_MONITOR_SYSTEM_INFO': True,
            'CON5013_MONITOR_APPLICATION': True,
            'CON5013_MONITOR_CPU': True,
            'CON5013_MONITOR_MEMORY': True,
            'CON5013_MONITOR_DISK': True,
            'CON5013_MONITOR_NETWORK': True,
            'CON5013_MONITOR_GPU': True,
            'CON5013_SYSTEM_CUSTOM_BOXES': [],
            
            # UI configuration
            'CON5013_ASCII_ART': True,
            'CON5013_OVERLAY_MODE': True,
            'CON5013_AUTO_INJECT': True,
            'CON5013_HOTKEY': 'Alt+C',
            
            # Integration settings
            'CON5013_CRAWL4AI_INTEGRATION': False,
            'CON5013_WEBSOCKET_SUPPORT': False,
            'CON5013_AUTHENTICATION': False,
            'CON5013_AUTH_USER': None,
            'CON5013_AUTH_PASSWORD': None,
            'CON5013_AUTH_TOKEN': None,
            'CON5013_AUTH_CALLBACK': None,
            
            # API scanner safety
            'CON5013_API_PROTECTED_ENDPOINTS': [
                '/con5013/api/scanner/test',
                '/con5013/api/scanner/test-all',
                '/con5013/api/logs/clear',
                '/con5013/api/system/stats'
            ],
        }
    
    def init_app(self, app: Flask):
        """Initialize Con5013 with a Flask application."""
        self.app = app
        
        # Update config from Flask app config
        for key, default_value in self.config.items():
            self.config[key] = app.config.get(key, default_value)
        
        # Skip initialization if disabled
        if not self.config['CON5013_ENABLED']:
            logger.info("Con5013 is disabled via configuration")
            return
        
        # Store extension instance in app
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['con5013'] = self

        # Ensure app start_time exists for uptime metrics
        if not hasattr(app, 'start_time'):
            app.start_time = time.time()
        
        # Initialize core components
        self._initialize_components()

        # Load system boxes defined via configuration after core components
        self._load_configured_system_boxes()

        # Register blueprint
        app.register_blueprint(
            con5013_blueprint,
            url_prefix=self.config['CON5013_URL_PREFIX']
        )
        
        # Auto-inject console HTML if enabled
        if self.config['CON5013_AUTO_INJECT']:
            self._inject_console_assets()
        
        # Set up logging integration
        self._setup_logging_integration()
        
        # Detect Crawl4AI integration
        if self.config['CON5013_CRAWL4AI_INTEGRATION']:
            self._setup_crawl4ai_integration()
        
        logger.info(f"Con5013 initialized successfully on {self.config['CON5013_URL_PREFIX']}")
    
    def _initialize_components(self):
        """Initialize all core components."""
        if self.config['CON5013_ENABLE_LOGS']:
            self.log_monitor = LogMonitor(self.app, self.config)
        
        if self.config['CON5013_ENABLE_TERMINAL']:
            self.terminal_engine = TerminalEngine(self.app, self.config)
        
        if self.config['CON5013_ENABLE_API_SCANNER']:
            self.api_scanner = APIScanner(self.app, self.config)
        
        if self.config['CON5013_ENABLE_SYSTEM_MONITOR']:
            self.system_monitor = SystemMonitor(self.app, self.config)
    
    def _inject_console_assets(self):
        """Inject console HTML and assets into the application."""
        @self.app.context_processor
        def inject_con5013():
            return {
                'con5013_enabled': True,
                'con5013_config': {
                    'url_prefix': self.config['CON5013_URL_PREFIX'],
                    'theme': self.config['CON5013_THEME'],
                    'hotkey': self.config['CON5013_HOTKEY'],
                    'overlay_mode': self.config['CON5013_OVERLAY_MODE']
                }
            }
        
        # Add template globals
        @self.app.template_global()
        def con5013_console_html():
            """Generate console HTML for injection."""
            return self._generate_console_html()
    
    def _setup_logging_integration(self):
        """Set up logging integration with Flask app."""
        if not self.log_monitor:
            return
        # If capturing root logger, the log monitor already attached to root.
        if self.config.get('CON5013_CAPTURE_ROOT_LOGGER', True):
            return
        # Otherwise, attach handler to app logger for app-specific logs.
        handler = self.log_monitor.get_flask_handler()
        self.app.logger.addHandler(handler)
    
    def _setup_crawl4ai_integration(self):
        """Set up special integration with Crawl4AI."""
        try:
            import crawl4ai
            logger.info("Crawl4AI detected - enabling enhanced integration")
            
            # Add Crawl4AI specific terminal commands
            if self.terminal_engine:
                self.terminal_engine.add_crawl4ai_commands()
            
            # Add Crawl4AI specific monitoring
            if self.system_monitor:
                self.system_monitor.add_crawl4ai_metrics()
                
            # Attach logging from Crawl4AI to our logs (as 'crawl4ai')
            if self.log_monitor:
                self.log_monitor.attach_logger('crawl4ai', alias='crawl4ai')
                # Also alias common sub-loggers if used
                self.log_monitor.set_logger_alias('crawl4ai.', 'crawl4ai')
                self.log_monitor.set_logger_alias('Crawl4AI', 'crawl4ai')
                self.log_monitor.set_logger_alias('Crawl4AI.', 'crawl4ai')

        except ImportError:
            logger.debug("Crawl4AI not found - skipping enhanced integration")
    
    def _generate_console_html(self):
        """Generate the auto-injected console assets."""

        url_prefix = self.config.get('CON5013_URL_PREFIX', '/con5013') or '/con5013'
        if not isinstance(url_prefix, str):
            url_prefix = str(url_prefix)
        if not url_prefix.startswith('/'):
            url_prefix = f'/{url_prefix}'
        if url_prefix != '/' and url_prefix.endswith('/'):
            url_prefix = url_prefix.rstrip('/')

        try:
            script_src = url_for('con5013.static', filename='js/con5013.js')
        except RuntimeError:
            prefix = '' if url_prefix == '/' else url_prefix
            script_src = f"{prefix}/static/js/con5013.js"

        hotkey = self.config.get('CON5013_HOTKEY', 'Alt+C') or 'Alt+C'
        update_interval = self.config.get('CON5013_SYSTEM_UPDATE_INTERVAL', 5)
        payload = {
            'baseUrl': url_prefix,
            'url_prefix': url_prefix,
            'hotkey': hotkey,
            'updateInterval': update_interval,
            'CON5013_URL_PREFIX': url_prefix,
            'CON5013_HOTKEY': hotkey,
            'CON5013_SYSTEM_UPDATE_INTERVAL': update_interval,
        }

        return render_template_string(
            """<!-- Con5013 Console Assets -->
<script>
    (function () {
        const defaults = {{ payload | tojson }};
        const existing = window.CON5013_BOOTSTRAP || window.CON5013_CONFIG || window.con5013_bootstrap || null;
        if (existing && typeof existing === 'object') {
            window.CON5013_BOOTSTRAP = Object.assign({}, defaults, existing);
        } else {
            window.CON5013_BOOTSTRAP = defaults;
        }
    })();
</script>
<script src="{{ script_src }}" data-con5013-base="{{ base_url }}" data-con5013-hotkey="{{ hotkey }}" defer></script>
""",
            payload=payload,
            script_src=script_src,
            base_url=url_prefix,
            hotkey=hotkey,
        )
    
    # Public API methods
    def get_logs(self, source='app', limit=100, level=None):
        """Get application logs."""
        if self.log_monitor:
            return self.log_monitor.get_logs(source, limit, level)
        return []
    
    def execute_command(self, command, context=None):
        """Execute a terminal command."""
        if self.terminal_engine:
            return self.terminal_engine.execute(command, context)
        return {'error': 'Terminal engine not available'}
    
    def scan_apis(self):
        """Scan and discover all API endpoints."""
        if self.api_scanner:
            return self.api_scanner.discover_endpoints()
        return []
    
    def get_system_stats(self):
        """Get current system statistics."""
        stats = self.system_monitor.get_current_stats() if self.system_monitor else {}
        custom_boxes = self._collect_system_boxes()
        if custom_boxes:
            stats['custom_boxes'] = custom_boxes
        return stats

    def add_custom_command(self, name, handler, description=""):
        """Add a custom terminal command."""
        if self.terminal_engine:
            self.terminal_engine.add_command(name, handler, description)

    # ------------------------------------------------------------------
    # Custom system monitor boxes
    # ------------------------------------------------------------------
    def add_system_box(self, box_id: Optional[str] = None, *, title: Optional[str] = None,
                       rows: Optional[Iterable[Any]] = None, provider: Optional[Callable[[], Dict[str, Any]]] = None,
                       enabled: Union[Callable[[], bool], bool, None] = True, order: Optional[int] = None,
                       description: Optional[str] = None) -> str:
        """Register a custom system monitor box.

        Parameters
        ----------
        box_id:
            Optional unique identifier for the box. If omitted, an ID is generated from the title.
        title:
            Title displayed on the card. Required when ``box_id`` is not provided.
        rows:
            Iterable of row definitions describing the metrics to render. Each row can be a dict or callable.
        provider:
            Optional callable returning a dictionary with dynamic box data. When provided, the callable can
            override fields such as ``title`` or ``rows`` on every refresh.
        enabled:
            Boolean or callable evaluated on each refresh to determine whether the box should be visible.
        order:
            Optional integer used to control ordering amongst custom boxes. Lower numbers render first.
        description:
            Optional descriptive text surfaced through the API for consumers that need metadata.

        Returns
        -------
        str
            The identifier of the registered box.
        """

        if box_id is None and not title:
            raise ValueError("A system box requires a title or explicit box_id")

        box_key = self._slugify(box_id or title)

        self._system_boxes[box_key] = {
            'id': box_key,
            'title': title,
            'rows': rows,
            'provider': provider,
            'enabled': enabled,
            'order': order,
            'description': description,
        }
        return box_key

    def remove_system_box(self, box_id: str) -> None:
        """Remove a previously registered system box."""
        if not box_id:
            return
        self._system_boxes.pop(box_id, None)

    def set_system_box_enabled(self, box_id: str, enabled: bool) -> None:
        """Enable or disable a registered system box."""
        if not box_id or box_id not in self._system_boxes:
            return
        self._system_boxes[box_id]['enabled'] = bool(enabled)

    # Internal helpers -------------------------------------------------
    def _load_configured_system_boxes(self) -> None:
        """Register system boxes defined through configuration."""
        config_boxes = self.config.get('CON5013_SYSTEM_CUSTOM_BOXES') or []
        for index, raw in enumerate(config_boxes):
            if isinstance(raw, dict):
                data = dict(raw)
            else:
                # Allow simple tuples/lists such as (title, rows)
                data = {}
                if isinstance(raw, (list, tuple)) and raw:
                    data['title'] = raw[0]
                    if len(raw) > 1:
                        data['rows'] = raw[1]
            if not data:
                continue
            box_id = data.pop('id', None) or data.pop('box_id', None)
            title = data.pop('title', None)
            self.add_system_box(box_id, title=title, **data)

    def _collect_system_boxes(self) -> List[Dict[str, Any]]:
        """Build serializable payload for registered system boxes."""
        boxes: List[Dict[str, Any]] = []
        for _, entry in self._system_boxes.items():
            normalized = self._normalize_system_box(entry)
            if normalized:
                boxes.append(normalized)
        boxes.sort(key=lambda b: (b.get('order') if b.get('order') is not None else 1_000_000, b.get('title', '')))
        return boxes

    def _normalize_system_box(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize a single system box definition."""
        if not entry:
            return None

        enabled = entry.get('enabled', True)
        try:
            if callable(enabled):
                enabled = bool(enabled())
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Error evaluating system box enabled state: %s", exc)
            enabled = False
        if not enabled:
            return None

        provider = entry.get('provider')
        dynamic_data: Dict[str, Any] = {}
        if callable(provider):
            try:
                provided = provider() or {}
                if isinstance(provided, dict):
                    dynamic_data = provided
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Error evaluating system box provider: %s", exc)
                dynamic_data = {'error': str(exc)}
        elif isinstance(provider, dict):
            dynamic_data = dict(provider)

        # Merge static and dynamic data (dynamic data takes precedence)
        title = dynamic_data.get('title') or entry.get('title') or entry.get('id')
        order = dynamic_data.get('order') if dynamic_data.get('order') is not None else entry.get('order')
        description = dynamic_data.get('description') or entry.get('description')

        rows_source = dynamic_data.get('rows', entry.get('rows'))
        normalized_rows = self._normalize_system_rows(rows_source)

        # If provider returned an explicit enabled flag, respect it
        provided_enabled = dynamic_data.get('enabled')
        if provided_enabled is not None and not provided_enabled:
            return None

        payload = {
            'id': entry.get('id'),
            'title': title,
            'rows': normalized_rows,
        }
        if order is not None:
            payload['order'] = order
        if description:
            payload['description'] = description
        if dynamic_data.get('meta'):
            payload['meta'] = dynamic_data['meta']
        if dynamic_data.get('error'):
            payload['error'] = str(dynamic_data['error'])
        return payload

    def _normalize_system_rows(self, rows: Optional[Iterable[Any]]) -> List[Dict[str, Any]]:
        """Normalize a collection of row specifications."""
        normalized: List[Dict[str, Any]] = []
        if rows is None:
            return normalized

        for index, raw in enumerate(rows):
            row = raw
            if callable(row):
                try:
                    row = row()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.exception("Error evaluating system box row callable: %s", exc)
                    continue
            if not isinstance(row, dict):
                if row is None:
                    continue
                row = {'name': str(row), 'value': ''}

            name = row.get('name') or row.get('label')
            if not name:
                continue

            row_id = row.get('id') or f"{self._slugify(name)}-{index}"

            value = row.get('value')
            if callable(value):
                try:
                    value = value()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.exception("Error evaluating system row value: %s", exc)
                    value = None
            display_value = row.get('display_value')
            if callable(display_value):
                try:
                    display_value = display_value()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.exception("Error evaluating system row display value: %s", exc)
                    display_value = None

            normalized_row: Dict[str, Any] = {
                'id': row_id,
                'name': str(name),
                'value': '' if value is None else str(value),
            }
            if display_value is not None:
                normalized_row['display_value'] = str(display_value)

            progress_spec = self._normalize_progress_spec(row.get('progress'))
            if progress_spec:
                normalized_row['progress'] = progress_spec

            if 'divider' in row:
                normalized_row['divider'] = bool(row['divider'])

            if row.get('meta') is not None:
                normalized_row['meta'] = row['meta']

            normalized.append(normalized_row)

        return normalized

    def _normalize_progress_spec(self, spec: Any) -> Optional[Dict[str, Any]]:
        """Normalize progress bar configuration for a row."""
        if spec is None:
            return None
        progress = spec
        if callable(progress):
            try:
                progress = progress()
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Error evaluating progress spec: %s", exc)
                return None
        if not isinstance(progress, dict):
            return None

        value = progress.get('value')
        if callable(value):
            try:
                value = value()
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Error evaluating progress value: %s", exc)
                value = None
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return None

        min_value = progress.get('min', 0)
        max_value = progress.get('max', 100)
        try:
            min_value = float(min_value)
        except (TypeError, ValueError):
            min_value = 0.0
        try:
            max_value = float(max_value)
        except (TypeError, ValueError):
            max_value = max(min_value + 1.0, 100.0)
        if max_value == min_value:
            max_value = min_value + 1.0

        payload: Dict[str, Any] = {
            'value': numeric_value,
            'min': min_value,
            'max': max_value,
        }

        if 'display_value' in progress and progress['display_value'] is not None:
            payload['display_value'] = str(progress['display_value'])

        color = progress.get('color')
        if color:
            payload['color'] = str(color)

        color_rules: List[Dict[str, Any]] = []
        for rule in progress.get('color_rules', []) or []:
            entry = rule
            if callable(entry):
                try:
                    entry = entry()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.exception("Error evaluating progress color rule: %s", exc)
                    continue
            if not isinstance(entry, dict):
                continue
            threshold = entry.get('threshold')
            try:
                threshold_value = float(threshold)
            except (TypeError, ValueError):
                continue
            color_class = entry.get('class') or entry.get('color')
            operator = (entry.get('operator') or 'gte').lower()
            color_rules.append({
                'threshold': threshold_value,
                'class': str(color_class) if color_class else None,
                'operator': operator,
            })
        if color_rules:
            payload['color_rules'] = color_rules

        if 'divider' in progress:
            payload['divider'] = bool(progress['divider'])
        if 'tooltip' in progress and progress['tooltip'] is not None:
            payload['tooltip'] = str(progress['tooltip'])

        if 'precision' in progress and progress['precision'] is not None:
            try:
                payload['precision'] = int(progress['precision'])
            except (TypeError, ValueError):
                pass

        return payload

    def _slugify(self, value: Optional[str]) -> str:
        """Generate a safe identifier for dynamic system boxes."""
        if not value:
            return f"box-{len(self._system_boxes) + 1}"
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', str(value)).strip('-').lower()
        return slug or f"box-{len(self._system_boxes) + 1}"
    
    def add_log_source(self, source_name, source_path):
        """Add a new log source to monitor."""
        if self.log_monitor:
            self.log_monitor.add_source(source_name, source_path)

# Convenience functions for easy integration
def create_con5013(app, **config):
    """Factory function to create and configure Con5013."""
    return Con5013(app, config=config)

def init_con5013(app, **config):
    """Initialize Con5013 with an existing Flask app."""
    console = Con5013(**config)
    console.init_app(app)
    return console

# Export main classes and functions
__all__ = [
    'Con5013',
    'con5013_blueprint',
    'create_con5013',
    'init_con5013',
    'LogMonitor',
    'TerminalEngine',
    'APIScanner',
    'SystemMonitor'
]
