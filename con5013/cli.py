#!/usr/bin/env python3
"""
Con5013 Command Line Interface
Provides command-line tools for Con5013 management and utilities.
"""

import argparse
import sys
import os
import time
from . import __version__

def print_banner():
    """Print Con5013 banner."""
    banner = f"""
╔═══════════════════════════════════════════════════════════════╗
║                         CON5013 v{__version__}                         ║
║              The Ultimate Flask Console Extension             ║
║                                                               ║
║  Monitor • Debug • Control Your Flask Applications           ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(banner)

def cmd_version(args):
    """Show version information."""
    print(f"Con5013 version {__version__}")

def cmd_init(args):
    """Initialize Con5013 in a Flask project."""
    print("Initializing Con5013 in your Flask project...")
    
    # Create example integration file
    example_code = '''from flask import Flask
from con5013 import Con5013

app = Flask(__name__)

# Initialize Con5013 with your Flask app
console = Con5013(app)

# Optional: Configure Con5013
# console = Con5013(app, config={
#     'CON5013_URL_PREFIX': '/admin/console',
#     'CON5013_THEME': 'dark',
#     'CON5013_ENABLE_TERMINAL': True,
#     'CON5013_CRAWL4AI_INTEGRATION': True
# })

@app.route('/')
def home():
    return """
    <h1>Your Flask App with Con5013</h1>
    <p>Con5013 console is available at: <a href="/con5013">/con5013</a></p>
    <p>Press Alt+C to open the overlay console</p>
    """

if __name__ == '__main__':
    app.run(debug=True)
'''
    
    filename = args.filename or 'app_with_con5013.py'
    with open(filename, 'w') as f:
        f.write(example_code)
    
    print(f"✓ Created example Flask app with Con5013: {filename}")
    print(f"✓ Run with: python {filename}")
    print("✓ Access console at: http://localhost:5000/con5013")

def cmd_demo(args):
    """Run a Con5013 demo application."""
    print("Starting Con5013 demo application...")
    
    from flask import Flask
    from . import Con5013
    
    app = Flask(__name__)
    app.config['DEBUG'] = True
    
    # Initialize Con5013
    console = Con5013(app, config={
        'CON5013_CRAWL4AI_INTEGRATION': args.crawl4ai,
        'CON5013_ENABLE_TERMINAL': True,
        'CON5013_ENABLE_API_SCANNER': True,
        'CON5013_ENABLE_SYSTEM_MONITOR': True
    })
    
    @app.route('/')
    def home():
        return '''
        <html>
        <head><title>Con5013 Demo</title></head>
        <body style="font-family: Arial, sans-serif; margin: 40px;">
            <h1>🚀 Con5013 Demo Application</h1>
            <p>Welcome to the Con5013 demonstration!</p>
            <h2>Available Features:</h2>
            <ul>
                <li><a href="/con5013">📊 Full Console Interface</a></li>
                <li><strong>Hotkey:</strong> Press <code>Alt+C</code> for overlay console</li>
                <li><strong>Real-time Monitoring:</strong> System stats, logs, and API discovery</li>
                <li><strong>Interactive Terminal:</strong> Execute commands directly</li>
            </ul>
            <h2>Test Endpoints:</h2>
            <ul>
                <li><a href="/api/test">GET /api/test</a></li>
                <li><a href="/api/users">GET /api/users</a></li>
            </ul>
        </body>
        </html>
        '''
    
    @app.route('/api/test')
    def api_test():
        return {'message': 'Con5013 API test successful', 'timestamp': time.time()}
    
    @app.route('/api/users')
    def api_users():
        return {'users': [{'id': 1, 'name': 'Demo User'}]}
    
    print("Demo application starting...")
    print("Access at: http://localhost:5000")
    print("Console at: http://localhost:5000/con5013")
    print("Press Ctrl+C to stop")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        print("\nDemo stopped.")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Con5013 - The Ultimate Flask Console Extension',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--version', action='version', version=f'Con5013 {__version__}')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Version command
    version_parser = subparsers.add_parser('version', help='Show version information')
    version_parser.set_defaults(func=cmd_version)
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize Con5013 in a Flask project')
    init_parser.add_argument('--filename', '-f', help='Output filename (default: app_with_con5013.py)')
    init_parser.set_defaults(func=cmd_init)
    
    # Demo command
    demo_parser = subparsers.add_parser('demo', help='Run Con5013 demo application')
    demo_parser.add_argument('--crawl4ai', action='store_true', help='Enable Crawl4AI integration')
    demo_parser.set_defaults(func=cmd_demo)
    
    args = parser.parse_args()
    
    if not args.command:
        print_banner()
        parser.print_help()
        return
    
    # Execute the command
    args.func(args)

if __name__ == '__main__':
    main()

