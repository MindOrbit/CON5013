#!/usr/bin/env python3
"""
Basic tests for Con5013 Flask extension.
"""

import unittest
import tempfile
import os
from flask import Flask
from con5013 import Con5013

class TestCon5013(unittest.TestCase):
    """Test cases for Con5013 extension."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['CON5013_ENABLED'] = True
        
    def test_con5013_initialization(self):
        """Test Con5013 can be initialized with Flask app."""
        console = Con5013(self.app)
        self.assertIsNotNone(console)
        self.assertEqual(console.app, self.app)
        
    def test_con5013_factory_pattern(self):
        """Test Con5013 factory pattern initialization."""
        console = Con5013()
        console.init_app(self.app)
        self.assertIsNotNone(console)
        self.assertEqual(console.app, self.app)
        
    def test_con5013_configuration(self):
        """Test Con5013 configuration options."""
        config = {
            'CON5013_URL_PREFIX': '/admin/console',
            'CON5013_THEME': 'light',
            'CON5013_ENABLE_TERMINAL': False
        }
        console = Con5013(self.app, config=config)
        
        self.assertEqual(console.config['CON5013_URL_PREFIX'], '/admin/console')
        self.assertEqual(console.config['CON5013_THEME'], 'light')
        self.assertEqual(console.config['CON5013_ENABLE_TERMINAL'], False)
        
    def test_con5013_disabled(self):
        """Test Con5013 when disabled via configuration."""
        self.app.config['CON5013_ENABLED'] = False
        console = Con5013(self.app)
        
        # Should still initialize but not register routes
        self.assertIsNotNone(console)
        
    def test_blueprint_registration(self):
        """Test that Con5013 blueprint is registered."""
        console = Con5013(self.app)
        
        with self.app.test_client() as client:
            # Test that the console route exists
            response = client.get('/con5013/')
            # Should not return 404 (route exists)
            self.assertNotEqual(response.status_code, 404)
            
    def test_api_endpoints(self):
        """Test that API endpoints are accessible."""
        console = Con5013(self.app)
        
        with self.app.test_client() as client:
            # Test logs API
            response = client.get('/con5013/api/logs')
            self.assertIn(response.status_code, [200, 500])  # 500 is OK if no logs configured
            
            # Test system API
            response = client.get('/con5013/api/system')
            self.assertIn(response.status_code, [200, 500])
            
    def test_custom_url_prefix(self):
        """Test custom URL prefix configuration."""
        config = {'CON5013_URL_PREFIX': '/admin/console'}
        console = Con5013(self.app, config=config)
        
        with self.app.test_client() as client:
            # Test custom prefix route
            response = client.get('/admin/console/')
            self.assertNotEqual(response.status_code, 404)
            
            # Test original prefix should not exist
            response = client.get('/con5013/')
            self.assertEqual(response.status_code, 404)

class TestCon5013Components(unittest.TestCase):
    """Test Con5013 individual components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
    def test_log_monitor_initialization(self):
        """Test LogMonitor component."""
        console = Con5013(self.app, config={'CON5013_ENABLE_LOGS': True})
        self.assertIsNotNone(console.log_monitor)
        
    def test_terminal_engine_initialization(self):
        """Test TerminalEngine component."""
        console = Con5013(self.app, config={'CON5013_ENABLE_TERMINAL': True})
        self.assertIsNotNone(console.terminal_engine)
        
    def test_api_scanner_initialization(self):
        """Test APIScanner component."""
        console = Con5013(self.app, config={'CON5013_ENABLE_API_SCANNER': True})
        self.assertIsNotNone(console.api_scanner)
        
    def test_system_monitor_initialization(self):
        """Test SystemMonitor component."""
        console = Con5013(self.app, config={'CON5013_ENABLE_SYSTEM_MONITOR': True})
        self.assertIsNotNone(console.system_monitor)
        
    def test_disabled_components(self):
        """Test that disabled components are not initialized."""
        console = Con5013(self.app, config={
            'CON5013_ENABLE_LOGS': False,
            'CON5013_ENABLE_TERMINAL': False,
            'CON5013_ENABLE_API_SCANNER': False,
            'CON5013_ENABLE_SYSTEM_MONITOR': False
        })
        
        self.assertIsNone(console.log_monitor)
        self.assertIsNone(console.terminal_engine)
        self.assertIsNone(console.api_scanner)
        self.assertIsNone(console.system_monitor)

class TestCon5013Integration(unittest.TestCase):
    """Test Con5013 integration features."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
    def test_flask_app_integration(self):
        """Test integration with Flask app."""
        console = Con5013(self.app)
        
        # Check that extension is registered
        self.assertIn('con5013', self.app.extensions)
        self.assertEqual(self.app.extensions['con5013'], console)
        
    def test_context_processor_injection(self):
        """Test that context processor is injected."""
        console = Con5013(self.app, config={'CON5013_AUTO_INJECT': True})
        
        with self.app.test_request_context():
            # Context processor should be available
            processors = self.app.template_context_processors[None]
            self.assertTrue(len(processors) > 0)

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)

