"""
Con5013 Flask Blueprint
Provides all the web routes and API endpoints for the Con5013 console.
"""

import json
import time
from flask import Blueprint, render_template, jsonify, request, current_app, abort

from .core.security import enforce_con5013_security
from .core.utils import get_con5013_instance

# Create the blueprint
con5013_blueprint = Blueprint(
    'con5013',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)


@con5013_blueprint.before_request
def _enforce_security():
    """Gate all Con5013 routes according to the configured auth policy."""
    response = enforce_con5013_security()
    if response is not None:
        return response

@con5013_blueprint.route('/')
def console_home():
    """Main console interface."""
    con5013 = get_con5013_instance()
    return render_template('console.html', config=con5013.config)

@con5013_blueprint.route('/overlay')
def console_overlay():
    """Console overlay for injection into other pages."""
    con5013 = get_con5013_instance()
    return render_template('overlay.html', config=con5013.config)

# ============================================================================
# LOGS API ENDPOINTS
# ============================================================================

@con5013_blueprint.route('/api/logs')
def api_logs():
    """Get application logs."""
    con5013 = get_con5013_instance()
    if not con5013.config.get('CON5013_ENABLE_LOGS', True):
        abort(404)
    
    # Get query parameters (default to 'flask' which always exists via handler)
    source = request.args.get('source', 'flask')
    limit = int(request.args.get('limit', 100))
    level = request.args.get('level')
    since = request.args.get('since')  # timestamp
    
    try:
        logs = con5013.get_logs(source=source, limit=limit, level=level)
        
        # Filter by timestamp if provided
        if since:
            since_timestamp = float(since)
            logs = [log for log in logs if log.get('timestamp', 0) > since_timestamp]
        
        return jsonify({
            'status': 'success',
            'logs': logs,
            'total': len(logs),
            'source': source,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': time.time()
        }), 500

@con5013_blueprint.route('/api/logs/sources')
def api_log_sources():
    """Get available log sources."""
    con5013 = get_con5013_instance()
    if not con5013.config.get('CON5013_ENABLE_LOGS', True):
        abort(404)
    
    try:
        sources = []
        cfg_sources = con5013.config.get('CON5013_LOG_SOURCES')
        if cfg_sources:
            names = []
            for s in cfg_sources:
                if isinstance(s, dict) and s.get('name'):
                    names.append(s['name'])
            if names:
                sources = names
        if not sources and con5013.log_monitor:
            sources = con5013.log_monitor.get_available_sources()
        if not sources:
            sources = ['CON5013']
        
        return jsonify({
            'status': 'success',
            'sources': sources,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': time.time()
        }), 500

@con5013_blueprint.route('/api/logs/clear', methods=['POST'])
def api_clear_logs():
    """Clear logs for a specific source."""
    con5013 = get_con5013_instance()
    if not con5013.config.get('CON5013_ENABLE_LOGS', True) \
            or not con5013.config.get('CON5013_ALLOW_LOG_CLEAR', True):
        abort(404)
    data = request.get_json() or {}
    source = data.get('source', 'app')

    try:
        if con5013.log_monitor:
            con5013.log_monitor.clear_logs(source)
        
        return jsonify({
            'status': 'success',
            'message': f'Logs cleared for source: {source}',
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': time.time()
        }), 500

# ============================================================================
# TERMINAL API ENDPOINTS
# ============================================================================

@con5013_blueprint.route('/api/terminal/execute', methods=['POST'])
def api_terminal_execute():
    """Execute a terminal command."""
    con5013 = get_con5013_instance()
    if not con5013.config.get('CON5013_ENABLE_TERMINAL', True):
        abort(404)
    data = request.get_json() or {}
    command = data.get('command', '').strip()
    
    if not command:
        return jsonify({
            'status': 'error',
            'message': 'No command provided',
            'timestamp': time.time()
        }), 400
    
    try:
        result = con5013.execute_command(command, context={
            'user_ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'timestamp': time.time()
        })
        
        return jsonify({
            'status': 'success',
            'command': command,
            'result': result,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'command': command,
            'message': str(e),
            'timestamp': time.time()
        }), 500

@con5013_blueprint.route('/api/terminal/commands')
def api_terminal_commands():
    """Get available terminal commands."""
    con5013 = get_con5013_instance()
    if not con5013.config.get('CON5013_ENABLE_TERMINAL', True):
        abort(404)
    
    try:
        if con5013.terminal_engine:
            commands = con5013.terminal_engine.get_available_commands()
        else:
            commands = {
                'help': 'Show available commands',
                'status': 'Show application status',
                'clear': 'Clear terminal'
            }
        
        return jsonify({
            'status': 'success',
            'commands': commands,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': time.time()
        }), 500

@con5013_blueprint.route('/api/terminal/history')
def api_terminal_history():
    """Get terminal command history."""
    con5013 = get_con5013_instance()
    if not con5013.config.get('CON5013_ENABLE_TERMINAL', True):
        abort(404)
    limit = int(request.args.get('limit', 50))
    
    try:
        if con5013.terminal_engine:
            history = con5013.terminal_engine.get_history(limit=limit)
        else:
            history = []
        
        return jsonify({
            'status': 'success',
            'history': history,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': time.time()
        }), 500

# ============================================================================
# API SCANNER ENDPOINTS
# ============================================================================

@con5013_blueprint.route('/api/scanner/discover')
def api_scanner_discover():
    """Discover all API endpoints in the application."""
    con5013 = get_con5013_instance()
    if not con5013.config.get('CON5013_ENABLE_API_SCANNER', True):
        abort(404)
    
    try:
        include_param = request.args.get('include_con5013')
        include_con5013 = True if include_param is None else (include_param.lower() in ['1', 'true', 'yes', 'on'])
        # Prefer calling scanner directly to pass options
        if con5013.api_scanner:
            endpoints = con5013.api_scanner.discover_endpoints(include_con5013=include_con5013)
        else:
            endpoints = []
        
        return jsonify({
            'status': 'success',
            'endpoints': endpoints,
            'total': len(endpoints),
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': time.time()
        }), 500

@con5013_blueprint.route('/api/scanner/test', methods=['POST'])
def api_scanner_test():
    """Test a specific API endpoint."""
    con5013 = get_con5013_instance()
    if not con5013.config.get('CON5013_ENABLE_API_SCANNER', True):
        abort(404)
    data = request.get_json() or {}
    endpoint = data.get('endpoint')
    method = data.get('method', 'GET')
    
    if not endpoint:
        return jsonify({
            'status': 'error',
            'message': 'No endpoint provided',
            'timestamp': time.time()
        }), 400
    
    try:
        if con5013.api_scanner:
            result = con5013.api_scanner.test_endpoint(endpoint, method)
        else:
            result = {'error': 'API scanner not available'}
        
        return jsonify({
            'status': 'success',
            'endpoint': endpoint,
            'method': method,
            'result': result,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'endpoint': endpoint,
            'method': method,
            'message': str(e),
            'timestamp': time.time()
        }), 500

@con5013_blueprint.route('/api/scanner/test-all', methods=['POST'])
def api_scanner_test_all():
    """Test all discovered API endpoints."""
    con5013 = get_con5013_instance()
    if not con5013.config.get('CON5013_ENABLE_API_SCANNER', True):
        abort(404)
    
    try:
        include_param = request.args.get('include_con5013')
        include_con5013 = True if include_param is None else (include_param.lower() in ['1', 'true', 'yes', 'on'])
        if con5013.api_scanner:
            results = con5013.api_scanner.test_all_endpoints(include_con5013=include_con5013)
        else:
            results = {'error': 'API scanner not available'}
        
        return jsonify({
            'status': 'success',
            'results': results,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': time.time()
        }), 500

# ============================================================================
# SYSTEM MONITOR ENDPOINTS
# ============================================================================

@con5013_blueprint.route('/api/system/stats')
def api_system_stats():
    """Get current system statistics."""
    con5013 = get_con5013_instance()
    if not con5013.config.get('CON5013_ENABLE_SYSTEM_MONITOR', True):
        abort(404)
    
    try:
        stats = con5013.get_system_stats()
        
        return jsonify({
            'status': 'success',
            'stats': stats,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': time.time()
        }), 500

@con5013_blueprint.route('/api/system/health')
def api_system_health():
    """Get application health status."""
    con5013 = get_con5013_instance()
    if not con5013.config.get('CON5013_ENABLE_SYSTEM_MONITOR', True):
        abort(404)
    
    try:
        health = {
            'status': 'healthy',
            'uptime': time.time() - getattr(current_app, 'start_time', time.time()),
            'con5013_version': con5013.__class__.__module__.split('.')[0],
            'flask_version': current_app.__class__.__module__.split('.')[0],
            'components': {
                'log_monitor': con5013.log_monitor is not None,
                'terminal_engine': con5013.terminal_engine is not None,
                'api_scanner': con5013.api_scanner is not None,
                'system_monitor': con5013.system_monitor is not None,
            }
        }
        
        return jsonify({
            'status': 'success',
            'health': health,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': time.time()
        }), 500

# Processes endpoint
@con5013_blueprint.route('/api/system/processes')
def api_system_processes():
    """Get paginated list of system processes."""
    con5013 = get_con5013_instance()
    if not con5013.config.get('CON5013_ENABLE_SYSTEM_MONITOR', True):
        abort(404)
    sort_by = request.args.get('sort_by', 'cpu').lower()
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))

    try:
        if con5013.system_monitor:
            data = con5013.system_monitor.get_processes(sort_by=sort_by, page=page, page_size=page_size)
        else:
            data = {'available': False, 'processes': [], 'total': 0, 'page': page, 'page_size': page_size, 'sort_by': sort_by}
        return jsonify({'status': 'success', 'data': data, 'timestamp': time.time()})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'timestamp': time.time()}), 500

# ============================================================================
# CONFIGURATION ENDPOINTS
# ============================================================================

@con5013_blueprint.route('/api/config')
def api_config():
    """Get Con5013 configuration."""
    con5013 = get_con5013_instance()
    
    # Filter sensitive configuration
    safe_config = {k: v for k, v in con5013.config.items() 
                   if not any(sensitive in k.lower() 
                             for sensitive in ['password', 'secret', 'key', 'token'])}
    
    return jsonify({
        'status': 'success',
        'config': safe_config,
        'timestamp': time.time()
    })

@con5013_blueprint.route('/api/info')
def api_info():
    """Get Con5013 information and status."""
    con5013 = get_con5013_instance()
    
    info = {
        'name': 'Con5013',
        'version': '1.0.0',
        'description': 'The Ultimate Flask Console Extension',
        'url_prefix': con5013.config['CON5013_URL_PREFIX'],
        'theme': con5013.config['CON5013_THEME'],
        'default_log_source': con5013.config.get('CON5013_DEFAULT_LOG_SOURCE'),
        'features': {
            'logs': con5013.config['CON5013_ENABLE_LOGS'],
            'terminal': con5013.config['CON5013_ENABLE_TERMINAL'],
            'api_scanner': con5013.config['CON5013_ENABLE_API_SCANNER'],
            'system_monitor': con5013.config['CON5013_ENABLE_SYSTEM_MONITOR'],
            'allow_log_clear': con5013.config.get('CON5013_ALLOW_LOG_CLEAR', True),
            'system_monitor_metrics': {
                'system_info': con5013.config.get('CON5013_MONITOR_SYSTEM_INFO', True),
                'application': con5013.config.get('CON5013_MONITOR_APPLICATION', True),
                'cpu': con5013.config.get('CON5013_MONITOR_CPU', True),
                'memory': con5013.config.get('CON5013_MONITOR_MEMORY', True),
                'disk': con5013.config.get('CON5013_MONITOR_DISK', True),
                'network': con5013.config.get('CON5013_MONITOR_NETWORK', True),
                'gpu': con5013.config.get('CON5013_MONITOR_GPU', True),
            },
        },
        'crawl4ai_integration': con5013.config['CON5013_CRAWL4AI_INTEGRATION'],
        'security_profile': con5013.config.get('CON5013_SECURITY_PROFILE', 'open'),
        'endpoints': {
            'console': con5013.config['CON5013_URL_PREFIX'] + '/',
            'overlay': con5013.config['CON5013_URL_PREFIX'] + '/overlay',
            'api_base': con5013.config['CON5013_URL_PREFIX'] + '/api',
        }
    }
    
    return jsonify({
        'status': 'success',
        'info': info,
        'timestamp': time.time()
    })

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@con5013_blueprint.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found',
        'code': 404,
        'timestamp': time.time()
    }), 404

@con5013_blueprint.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        'status': 'error',
        'message': 'Internal server error',
        'code': 500,
        'timestamp': time.time()
    }), 500
