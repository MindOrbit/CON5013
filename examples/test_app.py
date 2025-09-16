#!/usr/bin/env python3
"""
Test Flask Application for Con5013
This demonstrates how to integrate Con5013 with a Flask application.
"""

import os
import sys
import time
import logging
from flask import Flask, jsonify, request, render_template_string

# Add the parent directory to the path so we can import con5013
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from con5013 import Con5013

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-secret-key-for-con5013'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Con5013 with custom configuration
con5013 = Con5013(app, config={
    'CON5013_URL_PREFIX': '/console',
    'CON5013_THEME': 'dark',
    'CON5013_ENABLE_LOGS': True,
    'CON5013_ENABLE_TERMINAL': True,
    'CON5013_ENABLE_API_SCANNER': True,
    'CON5013_ENABLE_SYSTEM_MONITOR': True,
    'CON5013_CRAWL4AI_INTEGRATION': False,  # Set to True if testing with Crawl4AI
    'CON5013_LOG_SOURCES': ['app', 'test', 'demo']
})

# Test routes to generate some activity
@app.route('/')
def home():
    """Home page with Con5013 integration demo."""
    logger.info("Home page accessed")
    
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Con5013 Test Application</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .header {
                background: #1a1a1a;
                color: #00ff00;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                text-align: center;
            }
            .section {
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .button {
                background: #007bff;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                margin: 5px;
                text-decoration: none;
                display: inline-block;
            }
            .button:hover {
                background: #0056b3;
            }
            .console-button {
                background: #00ff00;
                color: #000;
                font-weight: bold;
            }
            .console-button:hover {
                background: #00cc00;
            }
            .code {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 4px;
                border-left: 4px solid #007bff;
                font-family: 'Courier New', monospace;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 Con5013 Test Application</h1>
            <p>The Ultimate Flask Console Extension</p>
        </div>
        
        <div class="section">
            <h2>🎯 Quick Access</h2>
            <p>Access the Con5013 console using any of these methods:</p>
            <a href="/console" class="button console-button">Open Full Console</a>
            <a href="/console/overlay" class="button console-button">Open Overlay Console</a>
            <p><strong>Or use the floating console button in the bottom-right corner!</strong></p>
        </div>
        
        <div class="section">
            <h2>🧪 Test Features</h2>
            <p>Try these endpoints to generate activity for monitoring:</p>
            <a href="/api/test/info" class="button">Test Info Endpoint</a>
            <a href="/api/test/error" class="button">Test Error Endpoint</a>
            <a href="/api/test/slow" class="button">Test Slow Endpoint</a>
            <button onclick="generateLogs()" class="button">Generate Random Logs</button>
        </div>
        
        <div class="section">
            <h2>📊 Integration Code</h2>
            <p>Here's how Con5013 was integrated into this application:</p>
            <div class="code">
from con5013 import Con5013

app = Flask(__name__)
con5013 = Con5013(app, config={
    'CON5013_URL_PREFIX': '/console',
    'CON5013_THEME': 'dark',
    'CON5013_ENABLE_LOGS': True,
    'CON5013_ENABLE_TERMINAL': True,
    'CON5013_ENABLE_API_SCANNER': True,
    'CON5013_ENABLE_SYSTEM_MONITOR': True
})
            </div>
        </div>
        
        <div class="section">
            <h2>🔧 Available Features</h2>
            <ul>
                <li><strong>Real-time Logs:</strong> Monitor application logs in real-time</li>
                <li><strong>Interactive Terminal:</strong> Execute commands directly from the console</li>
                <li><strong>API Scanner:</strong> Discover and test all application endpoints</li>
                <li><strong>System Monitor:</strong> View CPU, memory, and performance metrics</li>
                <li><strong>Overlay Mode:</strong> Non-intrusive floating console</li>
                <li><strong>Dark Theme:</strong> Professional developer-friendly interface</li>
            </ul>
        </div>
        
        <script>
            function generateLogs() {
                fetch('/api/test/logs', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        alert('Generated ' + data.count + ' log entries!');
                    })
                    .catch(error => {
                        alert('Error generating logs: ' + error.message);
                    });
            }
        </script>
        
        <!-- Con5013 Overlay Integration -->
        <iframe src="/console/overlay" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; border: none; pointer-events: none; z-index: 999999;" id="con5013-overlay"></iframe>
        <script>
            // Make overlay interactive
            document.getElementById('con5013-overlay').style.pointerEvents = 'auto';
        </script>
    </body>
    </html>
    """
    
    return render_template_string(html_template)

@app.route('/api/test/info')
def api_test_info():
    """Test endpoint that returns information."""
    logger.info("Test info endpoint called")
    return jsonify({
        'status': 'success',
        'message': 'This is a test info endpoint',
        'timestamp': time.time(),
        'data': {
            'version': '1.0.0',
            'environment': 'test',
            'features': ['logs', 'terminal', 'api_scanner', 'system_monitor']
        }
    })

@app.route('/api/test/error')
def api_test_error():
    """Test endpoint that generates an error."""
    logger.error("Test error endpoint called - simulating error")
    return jsonify({
        'status': 'error',
        'message': 'This is a simulated error for testing purposes',
        'timestamp': time.time()
    }), 500

@app.route('/api/test/slow')
def api_test_slow():
    """Test endpoint that takes time to respond."""
    logger.info("Test slow endpoint called - simulating slow response")
    time.sleep(2)  # Simulate slow processing
    logger.info("Test slow endpoint completed")
    return jsonify({
        'status': 'success',
        'message': 'This endpoint took 2 seconds to respond',
        'timestamp': time.time()
    })

@app.route('/api/test/logs', methods=['POST'])
def api_test_logs():
    """Generate random log entries for testing."""
    import random
    
    log_messages = [
        "User authentication successful",
        "Database connection established",
        "Cache miss for key: user_123",
        "Processing background task",
        "Email notification sent",
        "File upload completed",
        "Session expired for user",
        "API rate limit check passed",
        "Backup process started",
        "Configuration reloaded"
    ]
    
    log_levels = [
        (logging.INFO, 'info'),
        (logging.WARNING, 'warning'),
        (logging.ERROR, 'error'),
        (logging.DEBUG, 'debug')
    ]
    
    count = random.randint(5, 15)
    for i in range(count):
        level, level_name = random.choice(log_levels)
        message = random.choice(log_messages)
        logger.log(level, f"{message} (test #{i+1})")
    
    return jsonify({
        'status': 'success',
        'message': f'Generated {count} log entries',
        'count': count,
        'timestamp': time.time()
    })

@app.route('/api/users/<int:user_id>')
def get_user(user_id):
    """Test endpoint with parameters."""
    logger.info(f"User {user_id} data requested")
    return jsonify({
        'user_id': user_id,
        'username': f'user_{user_id}',
        'email': f'user_{user_id}@example.com',
        'status': 'active'
    })

@app.route('/api/users', methods=['POST'])
def create_user():
    """Test endpoint for creating users."""
    data = request.get_json() or {}
    logger.info(f"Creating new user: {data.get('username', 'unknown')}")
    return jsonify({
        'status': 'created',
        'user_id': 12345,
        'message': 'User created successfully'
    }), 201

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'uptime': time.time() - app.start_time if hasattr(app, 'start_time') else 0
    })

if __name__ == '__main__':
    # Record start time for uptime calculation
    app.start_time = time.time()
    
    print("🚀 Starting Con5013 Test Application")
    print("📊 Console available at: http://localhost:5001/console")
    print("🎯 Overlay available at: http://localhost:5001/console/overlay")
    print("🏠 Home page: http://localhost:5001/")
    print("=" * 60)
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True,
        use_reloader=False  # Disable reloader to prevent Con5013 double initialization
    )

