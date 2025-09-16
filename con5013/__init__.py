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
import time
from flask import Flask
from .blueprint import con5013_blueprint
from .core.log_monitor import LogMonitor
from .core.terminal_engine import TerminalEngine
from .core.api_scanner import APIScanner
from .core.system_monitor import SystemMonitor

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
            'CON5013_MONITOR_CPU': True,
            'CON5013_MONITOR_MEMORY': True,
            'CON5013_MONITOR_DISK': True,
            'CON5013_MONITOR_NETWORK': True,
            'CON5013_MONITOR_GPU': True,
            
            # UI configuration
            'CON5013_ASCII_ART': True,
            'CON5013_OVERLAY_MODE': True,
            'CON5013_AUTO_INJECT': True,
            'CON5013_HOTKEY': 'Alt+C',
            
            # Integration settings
            'CON5013_CRAWL4AI_INTEGRATION': False,
            'CON5013_WEBSOCKET_SUPPORT': False,
            'CON5013_AUTHENTICATION': False,
            
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
        """Generate the console overlay HTML."""
        return '''
        <!-- Con5013 Console Overlay -->
        <div id="con5013-overlay" class="con5013-overlay">
            <div class="con5013-window">
                <div class="con5013-header">
                    <div class="con5013-title">
                        <i class="fas fa-terminal"></i>
                        <span>Con5013 Console</span>
                    </div>
                    <div class="con5013-controls">
                        <button class="con5013-btn" onclick="con5013.minimize()">
                            <i class="fas fa-minus"></i>
                        </button>
                        <button class="con5013-btn" onclick="con5013.close()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
                <div class="con5013-content">
                    <!-- Console content will be loaded here -->
                </div>
            </div>
        </div>
        '''
    
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
        if self.system_monitor:
            return self.system_monitor.get_current_stats()
        return {}
    
    def add_custom_command(self, name, handler, description=""):
        """Add a custom terminal command."""
        if self.terminal_engine:
            self.terminal_engine.add_command(name, handler, description)
    
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
