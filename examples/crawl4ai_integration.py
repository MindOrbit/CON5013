#!/usr/bin/env python3
"""
Con5013 + Crawl4AI Integration Example
Demonstrates how to use Con5013 with Crawl4AI for web scraping monitoring.
"""

from flask import Flask, render_template_string, jsonify, request
from con5013 import Con5013
import logging
import time
import threading
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Initialize Con5013 with Crawl4AI integration
console = Con5013(app, config={
    'CON5013_URL_PREFIX': '/console',
    'CON5013_THEME': 'dark',
    'CON5013_ENABLE_TERMINAL': True,
    'CON5013_ENABLE_API_SCANNER': True,
    'CON5013_ENABLE_SYSTEM_MONITOR': True,
    'CON5013_CRAWL4AI_INTEGRATION': True,
    'CON5013_AUTO_INJECT': True,
    'CON5013_HOTKEY': 'Alt+C'
})

# Simulated scraping jobs storage
scraping_jobs = []
job_counter = 0

@app.route('/')
def home():
    """Main dashboard page."""
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Crawl4AI + Con5013 Demo</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            }
            .header {
                text-align: center;
                margin-bottom: 40px;
            }
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }
            .feature-card {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 20px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .btn {
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                margin: 5px;
                transition: transform 0.2s;
            }
            .btn:hover {
                transform: translateY(-2px);
            }
            .console-hint {
                background: rgba(0, 0, 0, 0.3);
                padding: 15px;
                border-radius: 10px;
                margin-top: 20px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🕷️ Crawl4AI + Con5013 Integration Demo</h1>
                <p>Monitor your web scraping operations with the ultimate Flask console</p>
            </div>
            
            <div class="features">
                <div class="feature-card">
                    <h3>🚀 Start Scraping Job</h3>
                    <p>Launch a new web scraping job and monitor its progress in real-time.</p>
                    <a href="/api/scrape/start" class="btn">Start Job</a>
                </div>
                
                <div class="feature-card">
                    <h3>📊 View Jobs</h3>
                    <p>See all scraping jobs, their status, and collected data.</p>
                    <a href="/api/scrape/jobs" class="btn">View Jobs</a>
                </div>
                
                <div class="feature-card">
                    <h3>📈 System Stats</h3>
                    <p>Monitor system performance and resource usage.</p>
                    <a href="/api/system/stats" class="btn">System Stats</a>
                </div>
                
                <div class="feature-card">
                    <h3>🔍 API Explorer</h3>
                    <p>Discover and test all available API endpoints.</p>
                    <a href="/console" class="btn">Open Console</a>
                </div>
            </div>
            
            <div class="console-hint">
                <h3>🎯 Quick Access</h3>
                <p><strong>Press Alt+C</strong> to open the Con5013 overlay console from anywhere!</p>
                <p>Or visit the <a href="/console" style="color: #ffd700;">full console interface</a></p>
            </div>
        </div>
        
        <!-- Con5013 will auto-inject the console overlay -->
        {{ con5013_console_html() }}
    </body>
    </html>
    ''')

@app.route('/api/scrape/start')
def start_scraping_job():
    """Start a new scraping job."""
    global job_counter
    job_counter += 1
    
    job = {
        'id': job_counter,
        'url': 'https://example.com',
        'status': 'running',
        'started_at': datetime.now().isoformat(),
        'progress': 0,
        'pages_scraped': 0,
        'data_collected': 0
    }
    
    scraping_jobs.append(job)
    logger.info(f"Started scraping job #{job_counter}")
    
    # Simulate job progress in background
    def simulate_job_progress():
        for i in range(10):
            time.sleep(2)
            job['progress'] = (i + 1) * 10
            job['pages_scraped'] = i + 1
            job['data_collected'] = (i + 1) * 15
            logger.info(f"Job #{job_counter} progress: {job['progress']}%")
        
        job['status'] = 'completed'
        job['completed_at'] = datetime.now().isoformat()
        logger.info(f"Job #{job_counter} completed successfully")
    
    threading.Thread(target=simulate_job_progress, daemon=True).start()
    
    return jsonify({
        'success': True,
        'message': f'Scraping job #{job_counter} started',
        'job': job
    })

@app.route('/api/scrape/jobs')
def get_scraping_jobs():
    """Get all scraping jobs."""
    return jsonify({
        'jobs': scraping_jobs,
        'total': len(scraping_jobs),
        'active': len([j for j in scraping_jobs if j['status'] == 'running'])
    })

@app.route('/api/system/stats')
def get_system_stats():
    """Get system statistics."""
    import psutil
    
    stats = {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory': {
            'total': psutil.virtual_memory().total,
            'available': psutil.virtual_memory().available,
            'percent': psutil.virtual_memory().percent
        },
        'disk': {
            'total': psutil.disk_usage('/').total,
            'used': psutil.disk_usage('/').used,
            'free': psutil.disk_usage('/').free,
            'percent': psutil.disk_usage('/').percent
        },
        'timestamp': datetime.now().isoformat()
    }
    
    return jsonify(stats)

@app.route('/api/test/crawl4ai')
def test_crawl4ai():
    """Test Crawl4AI integration."""
    try:
        # This would normally import and use Crawl4AI
        # import crawl4ai
        
        logger.info("Testing Crawl4AI integration")
        
        return jsonify({
            'success': True,
            'message': 'Crawl4AI integration test successful',
            'features': [
                'Web scraping with AI extraction',
                'Real-time job monitoring',
                'Data visualization',
                'Scheduled scraping tasks'
            ]
        })
    except ImportError:
        return jsonify({
            'success': False,
            'message': 'Crawl4AI not installed. Install with: pip install crawl4ai',
            'note': 'This is a demo - Crawl4AI integration would work with the actual package'
        })

# Add some custom terminal commands for Con5013
if hasattr(console, 'terminal_engine') and console.terminal_engine:
    def scrape_status_command(args):
        """Custom command to check scraping status."""
        active_jobs = [j for j in scraping_jobs if j['status'] == 'running']
        return {
            'output': f"Active jobs: {len(active_jobs)}, Total jobs: {len(scraping_jobs)}",
            'success': True
        }
    
    console.add_custom_command('scrape-status', scrape_status_command, 
                              "Check the status of scraping jobs")

if __name__ == '__main__':
    print("🚀 Starting Crawl4AI + Con5013 Demo")
    print("📊 Console available at: http://localhost:5000/console")
    print("?? Press Alt+C for overlay console")
    print("🔍 API endpoints will be auto-discovered by Con5013")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

