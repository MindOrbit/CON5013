#!/usr/bin/env python3
"""
Minimal Flask app demonstrating Con5013 with a Matrix-themed page.
Runs on port 5002 by default.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template_string

# Try importing installed package; fallback to local source for dev
try:
    from con5013 import Con5013
except ImportError:
    REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
    LOCAL_PKG_ROOT = os.path.join(REPO_ROOT, 'CON5013')
    if LOCAL_PKG_ROOT not in sys.path:
        sys.path.insert(0, LOCAL_PKG_ROOT)
    from con5013 import Con5013  # type: ignore


def create_app() -> Flask:
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'matrix-demo-secret'

    # Demo custom command: `matrix`
    def matrix_command(args):
        """Matrix demo: matrix [hello|status|time]

        - hello:  prints a greeting
        - status: shows a tiny app status
        - time:   shows current server time
        """
        sub = (args[0] if args else '').lower()
        if sub == 'hello':
            return {'output': 'Hello from the Matrix custom command.', 'type': 'text'}
        elif sub == 'status':
            up = 'unknown'
            try:
                import time as _t
                if hasattr(app, 'start_time'):
                    up = f"{int(_t.time() - app.start_time)}s"
            except Exception:
                pass
            return {'output': f"App: {app.name}\nUptime: {up}\nDebug: {app.debug}", 'type': 'text'}
        elif sub == 'time':
            import time as _t
            return {'output': _t.strftime('%Y-%m-%d %H:%M:%S'), 'type': 'text'}
        else:
            return {'output': 'Usage: matrix [hello|status|time]', 'type': 'text'}
        

    # Basic logging + file handler
    logging.basicConfig(level=logging.INFO)
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, 'matrix_app.log')
    file_handler = RotatingFileHandler(log_path, maxBytes=512_000, backupCount=3)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s in %(name)s: %(message)s'))
    app.logger.addHandler(file_handler)
    app.logger.info('Matrix app starting...')

    # Initialize Con5013
    console = Con5013(app, config={
        'CON5013_URL_PREFIX': '/con5013',
        'CON5013_THEME': 'dark',
        'CON5013_ENABLE_LOGS': True,
        'CON5013_ENABLE_TERMINAL': True,
        'CON5013_ENABLE_API_SCANNER': True,
        'CON5013_ENABLE_SYSTEM_MONITOR': True,
        'CON5013_TERMINAL_ALLOW_PY': True,
        # Expose file-backed log source under a friendly name
        'CON5013_LOG_SOURCES': [
            {'name': 'CON5013'},
            {'name': 'flask'},
            {'name': 'werkzeug'},
            {'name': 'matrix', 'path': log_path}
        ],
        'CON5013_DEFAULT_LOG_SOURCE': 'CON5013',
    })

    # Register the demo custom command with help text from docstring
    console.add_custom_command('matrix', matrix_command, description=matrix_command.__doc__.split('\n')[0])

    # Simple Matrix-themed page
    @app.route('/')
    def matrix_home():
        html = """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>The Matrix — Demo</title>
            <style>
                body { background:#000; color:#0f0; font-family: Consolas, monospace; }
                .container { max-width: 900px; margin: 40px auto; padding: 24px; }
                h1 { letter-spacing: 2px; }
                .card { background: rgba(0, 0, 0, 0.6); border:1px solid #0f0; padding:16px; border-radius:8px; }
                a { color:#0f0; }
                .muted { color:#7f7; }
                .row { display:flex; gap:16px; flex-wrap:wrap; }
                .col { flex:1 1 280px; }
                code { color:#9f9; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Welcome to The Matrix</h1>
                <p class="muted">A tiny Flask demo wired to <code>Con5013</code>.</p>
                <div class="row">
                    <div class="col card">
                        <h3>Lore</h3>
                        <p>There is no spoon. Follow the white rabbit. Choice is an illusion created between those with power and those without.</p>
                    </div>
                    <div class="col card">
                        <h3>Specs</h3>
                        <ul>
                            <li>Reality Layer: Construct v3.1</li>
                            <li>Operator: Tank (on-call)</li>
                            <li>Ship: Nebuchadnezzar</li>
                        </ul>
                    </div>
                    <div class="col card">
                        <h3>Quick Links</h3>
                        <ul>
                            <li><a href="/con5013/">Open Con5013 Console</a></li>
                            <li><a href="/con5013/api/info">Console Info API</a></li>
                            <li><a href="/con5013/api/system/health">System Health</a></li>
                            <li><a href="/con5013/api/logs?source=matrix">Logs: matrix file</a></li>
                            <li><a href="/con5013/api/logs?source=flask">Logs: flask stream</a></li>
                        </ul>
                    </div>
                </div>
                <p class="muted">Press <strong>Alt + C</strong> to toggle the overlay (if enabled).</p>
            </div>
            <!-- Con5013 overlay launcher: include once to enable the floating button on this page -->
            <script src="/con5013/static/js/con5013.js"></script>
        </body>
        </html>
        """
        return render_template_string(html)

    @app.route('/generate-logs')
    def generate_logs():
        app.logger.info('Matrix demo info log')
        app.logger.warning('Matrix demo warning log')
        app.logger.error('Matrix demo error log')
        import logging as _logging
        _logging.getLogger('crawl4ai').info('Crawl4AI demo info log')
        return {'status': 'ok', 'generated': 3}

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=5002, debug=True)
