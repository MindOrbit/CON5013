"""
Con5013 Terminal Engine
Interactive terminal interface for Flask applications.
"""

import time
import io
import contextlib
import subprocess
import shlex
from typing import Dict, List, Any, Callable, Optional
from collections import deque

class TerminalEngine:
    """
    Interactive terminal engine for Con5013.
    
    Provides safe command execution, command history, and
    extensible command system for Flask applications.
    """
    
    def __init__(self, app, config):
        self.app = app
        self.config = config
        self.commands = {}
        self.history = deque(maxlen=config.get('CON5013_TERMINAL_HISTORY_SIZE', 100))
        self.timeout = config.get('CON5013_TERMINAL_TIMEOUT', 30)
        # Persistent Python evaluation context
        self._py_context: Dict[str, Any] = {}
        
        # Initialize built-in commands
        self._initialize_builtin_commands()
        
        # Add custom commands from config
        custom_commands = config.get('CON5013_CUSTOM_COMMANDS', {})
        for name, handler in custom_commands.items():
            self.add_command(name, handler)

        # Mark built-in commands for grouping in help
        try:
            builtin_names = ['help','clear','status','routes','config','logs','history','http','httpfull','system','py']
            for n in builtin_names:
                if n in self.commands:
                    self.commands[n]['builtin'] = True
        except Exception:
            pass

        # Override help handler to include custom section when available
        if 'help' in self.commands:
            self.commands['help']['handler'] = self._help_handler
    
    def _initialize_builtin_commands(self):
        """Initialize built-in terminal commands."""
        
        @self.command('help')
        def help_command(args):
            """Show available commands."""
            lines = [
                "Con5013 Terminal – Available Commands",
                "",
                "Core:",
                f"  {'help':<12} Show available commands",
                f"  {'clear':<12} Clear terminal screen",
                f"  {'status':<12} Show application status",
                f"  {'routes':<12} List all application routes",
                f"  {'config':<12} Show safe application configuration",
                f"  {'logs [N]':<12} Show recent logs (default 10)",
                f"  {'history [N]':<12} Show recent terminal commands",
                "",
                "Requests:",
                f"  {'http':<12} HTTP test: http [--full|-f] GET /path [JSON]",
                f"  {'httpfull':<12} HTTP test (full body alias)",
                "  Examples:",
                "    http GET /",
                "    http --full GET /con5013/api/info",
                "    http POST /api/users {\"name\":\"neo\"}",
                "",
                "Python:",
                f"  {'py':<12} Evaluate Python in app context (enable CON5013_TERMINAL_ALLOW_PY)",
                "  Examples:",
                "    py 1+2",
                "    py for i in range(3): print(i)",
                "    py x=2; y=5; result=x*y",
                "",
                "Tips:",
                "  • Enter: run    • Shift+Enter: newline",
            ]
            return {'output': "\n".join(lines), 'type': 'text'}
        
        @self.command('clear')
        def clear_command(args):
            """Clear terminal screen."""
            return {
                'output': '',
                'type': 'clear'
            }
        
        @self.command('status')
        def status_command(args):
            """Show application status."""
            uptime = time.time() - getattr(self.app, 'start_time', time.time())
            
            status = {
                'Application': self.app.name,
                'Uptime': f"{uptime:.2f} seconds",
                'Routes': len(self.app.url_map._rules),
                'Con5013 Version': '1.0.0',
                'Debug Mode': self.app.debug,
                'Extensions': list(getattr(self.app, 'extensions', {}).keys())
            }
            
            output = "Application Status:\n"
            for key, value in status.items():
                output += f"  {key:<20}: {value}\n"
            
            return {
                'output': output,
                'type': 'text'
            }
        
        @self.command('routes')
        def routes_command(args):
            """List all application routes."""
            routes = []
            for rule in self.app.url_map.iter_rules():
                methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
                routes.append(f"  {methods:<10} {rule.rule}")
            
            return {'output': "Application Routes:\n" + "\n".join(routes), 'type': 'text'}
        
        @self.command('config')
        def config_command(args):
            """Show application configuration (safe keys only)."""
            safe_keys = [
                'DEBUG', 'TESTING', 'SECRET_KEY', 'SERVER_NAME',
                'APPLICATION_ROOT', 'PREFERRED_URL_SCHEME'
            ]
            
            config_info = []
            for key in safe_keys:
                if key in self.app.config:
                    value = self.app.config[key]
                    # Hide sensitive values
                    if 'SECRET' in key or 'PASSWORD' in key:
                        value = '*' * len(str(value)) if value else 'Not set'
                    config_info.append(f"  {key:<20}: {value}")
            
            return {'output': "Application Configuration:\n" + "\n".join(config_info), 'type': 'text'}
        
        @self.command('logs')
        def logs_command(args):
            """Show recent logs."""
            try:
                con5013 = self.app.extensions.get('con5013')
                if con5013 and con5013.log_monitor:
                    limit = int(args[0]) if args and args[0].isdigit() else 10
                    logs = con5013.log_monitor.get_logs(limit=limit)
                    
                    output = f"Recent {len(logs)} log entries:\n"
                    for log in logs:
                        timestamp = time.strftime('%H:%M:%S', time.localtime(log.get('timestamp', 0)))
                        level = log.get('level', 'INFO')
                        message = log.get('message', '')[:100]  # Truncate long messages
                        output += f"  {timestamp} [{level}] {message}\n"
                    
                    return {
                        'output': output,
                        'type': 'text'
                    }
                else:
                    return {
                        'output': "Log monitor not available",
                        'type': 'error'
                    }
            except Exception as e:
                return {
                    'output': f"Error retrieving logs: {e}",
                    'type': 'error'
                }
        
        @self.command('system')
        def system_command(args):
            """Show system information."""
            try:
                import psutil
                
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                output = f"""System Information:
  CPU Usage        : {cpu_percent:.1f}%
  Memory Usage     : {memory.percent:.1f}% ({memory.used // (1024**2)} MB / {memory.total // (1024**2)} MB)
  Disk Usage       : {disk.percent:.1f}% ({disk.used // (1024**3)} GB / {disk.total // (1024**3)} GB)
  Boot Time        : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(psutil.boot_time()))}"""
                
                return {
                    'output': output,
                    'type': 'text'
                }
            except ImportError:
                return {
                    'output': "psutil not available - install with: pip install psutil",
                    'type': 'warning'
                }
            except Exception as e:
                return {
                    'output': f"Error getting system info: {e}",
                    'type': 'error'
                }

        @self.command('history')
        def history_command(args):
            """Show recent terminal commands."""
            limit = int(args[0]) if args and args[0].isdigit() else 20
            items = list(self.history)[-limit:]
            output = "Recent Commands:\n" + "\n".join(
                f"  {time.strftime('%H:%M:%S', time.localtime(i['timestamp']))} > {i['command']}" for i in items
            )
            return {'output': output, 'type': 'text'}

        # shared http executor
        def _exec_http(method: str, path: str, data, full: bool = False):
            with self.app.test_client() as client:
                func = getattr(client, method.lower())
                if data is None:
                    resp = func(path)
                else:
                    resp = func(path, json=data)
            preview = resp.get_json(silent=True)
            if preview is None:
                body = (resp.data or b'').decode('utf-8', 'ignore')
                if not full and len(body) > 2000:
                    body = body[:2000] + '...'
            else:
                import json as _json
                s = _json.dumps(preview, indent=2)
                body = s if full else s[:2000]
            out = f"HTTP {method} {path}\nStatus: {resp.status}\nHeaders: content-type={resp.headers.get('Content-Type')}\n\n{body}"
            return out

        @self.command('http')
        def http_command(args):
            """HTTP test: http [--full|-f] METHOD /path [JSON]"""
            if not args:
                return {'output': "Usage: http [--full|-f] <METHOD> <PATH> [JSON]", 'type': 'warning'}

            # Flags
            full = False
            cleaned = []
            for a in args:
                if a in ('--full', '-f'):
                    full = True
                else:
                    cleaned.append(a)

            if not cleaned:
                return {'output': "Usage: http [--full|-f] <METHOD> <PATH> [JSON]", 'type': 'warning'}
            method = cleaned[0].upper()
            if method not in {'GET','POST','PUT','DELETE','PATCH'}:
                return {'output': f"Unsupported method: {method}", 'type': 'error'}
            if len(cleaned) < 2:
                return {'output': "Usage: http [--full|-f] <METHOD> <PATH> [JSON]", 'type': 'warning'}
            path = cleaned[1]
            data = None
            if len(cleaned) > 2:
                try:
                    import json
                    data = json.loads(" ".join(cleaned[2:]))
                except Exception as e:
                    return {'output': f"Invalid JSON: {e}", 'type': 'error'}

            try:
                out = _exec_http(method, path, data, full=full)
                return {'output': out, 'type': 'text'}
            except Exception as e:
                return {'output': f"HTTP error: {e}", 'type': 'error'}

        @self.command('httpfull')
        def httpfull_command(args):
            """HTTP test (full body): httpfull METHOD /path [JSON]"""
            if not args:
                return {'output': "Usage: httpfull <METHOD> <PATH> [JSON]", 'type': 'warning'}
            method = args[0].upper()
            if method not in {'GET','POST','PUT','DELETE','PATCH'}:
                return {'output': f"Unsupported method: {method}", 'type': 'error'}
            if len(args) < 2:
                return {'output': "Usage: httpfull <METHOD> <PATH> [JSON]", 'type': 'warning'}
            path = args[1]
            data = None
            if len(args) > 2:
                try:
                    import json
                    data = json.loads(" ".join(args[2:]))
                except Exception as e:
                    return {'output': f"Invalid JSON: {e}", 'type': 'error'}
            try:
                out = _exec_http(method, path, data, full=True)
                return {'output': out, 'type': 'text'}
            except Exception as e:
                return {'output': f"HTTP error: {e}", 'type': 'error'}

        @self.command('py')
        def py_command(args):
            """Evaluate a Python expression in app context (dev only).

            Usage: py <expression>
            Example: py 1+2
                     py current_app.name
            """
            if not self.config.get('CON5013_TERMINAL_ALLOW_PY', False):
                return {'output': "Python eval disabled. Enable CON5013_TERMINAL_ALLOW_PY to use.", 'type': 'warning'}
            expr = " ".join(args).strip()
            if not expr:
                return {'output': "Usage: py <expression>", 'type': 'warning'}
            try:
                from flask import current_app
                # Safe builtins for evaluation
                SAFE_BUILTINS = {
                    'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
                    'min': min, 'max': max, 'sum': sum, 'sorted': sorted, 'any': any, 'all': all,
                    'abs': abs, 'round': round, 'range': range, 'enumerate': enumerate,
                    'list': list, 'dict': dict, 'set': set, 'tuple': tuple, 'print': print,
                    'zip': zip, 'repr': repr
                }
                # Prepare namespace with persistent context
                ns: Dict[str, Any] = {'__builtins__': SAFE_BUILTINS}
                ns.update(self._py_context)
                ns['app'] = self.app
                ns['current_app'] = current_app

                buf = io.StringIO()
                with self.app.app_context(), contextlib.redirect_stdout(buf):
                    try:
                        # Prefer exec for multi-line or statements; otherwise try eval first
                        use_exec = ("\n" in expr) or (';' in expr)
                        if not use_exec:
                            try:
                                result = eval(expr, ns, ns)
                                out_text = buf.getvalue()
                                if result is None and not out_text:
                                    return {'output': 'None', 'type': 'text'}
                                joined = out_text + (str(result) if result is not None else '')
                                # Persist context variables
                                self._py_context = {k: v for k, v in ns.items() if k not in {'__builtins__', 'app', 'current_app'}}
                                return {'output': joined, 'type': 'text'}
                            except SyntaxError:
                                use_exec = True
                        if use_exec:
                            exec(expr, ns, ns)
                            out_text = buf.getvalue()
                            # Persist context after exec
                            self._py_context = {k: v for k, v in ns.items() if k not in {'__builtins__', 'app', 'current_app'}}
                            # If user defined 'result', print it after stdout
                            if 'result' in ns and ns['result'] is not None:
                                out_text = out_text + ('' if out_text.endswith('\n') or out_text == '' else '\n') + str(ns['result'])
                            return {'output': out_text or 'Code executed.', 'type': 'text'}
                    finally:
                        buf.close()
            except Exception as e:
                return {'output': f"Eval error: {e}", 'type': 'error'}
    
    def command(self, name: str, description: str = ""):
        """Decorator to register a command."""
        def decorator(func: Callable):
            self.add_command(name, func, description)
            return func
        return decorator
    
    def add_command(self, name: str, handler: Callable, description: str = ""):
        """Add a custom command to the terminal."""
        self.commands[name] = {
            'handler': handler,
            'description': description or getattr(handler, '__doc__', 'No description')
        }

    def _help_handler(self, args):
        """Dynamic help that lists custom commands when available."""
        # Collect custom commands (not marked builtin)
        try:
            custom = sorted((k, v.get('description', '')) for k, v in self.commands.items() if not v.get('builtin'))
        except Exception:
            custom = []
        lines = [
            "Con5013 Terminal – Available Commands",
            "",
        ]
        if custom:
            lines += [
                "Custom:",
            ] + [f"  {name:<12} {desc}" for name, desc in custom] + ["",]
        lines += [
            "Core:",
            f"  {'help':<12} Show available commands",
            f"  {'clear':<12} Clear terminal screen",
            f"  {'status':<12} Show application status",
            f"  {'routes':<12} List all application routes",
            f"  {'config':<12} Show safe application configuration",
            f"  {'logs [N]':<12} Show recent logs (default 10)",
            f"  {'history [N]':<12} Show recent terminal commands",
            "",
            "Requests:",
            f"  {'http':<12} HTTP test: http [--full|-f] GET /path [JSON]",
            f"  {'httpfull':<12} HTTP test (full body alias)",
            "  Examples:",
            "    http GET /",
            "    http --full GET /con5013/api/info",
            "    http POST /api/users {\"name\":\"neo\"}",
            "",
            "Python:",
            f"  {'py':<12} Evaluate Python in app context (enable CON5013_TERMINAL_ALLOW_PY)",
            "  Examples:",
            "    py 1+2",
            "    py for i in range(3): print(i)",
            "    py x=2; y=5; result=x*y",
            "",
            "Tips:",
            "  • Enter: run    • Shift+Enter: newline",
        ]
        # Conditionally remove Python section when eval is disabled
        if not self.config.get('CON5013_TERMINAL_ALLOW_PY', False):
            try:
                idx = lines.index("Python:")
                # Remove header + examples block + trailing blank line
                del lines[idx:idx+7]
            except ValueError:
                pass
        return {'output': "\n".join(lines), 'type': 'text'}
    
    def execute(self, command: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a terminal command."""
        if not command.strip():
            return {
                'output': '',
                'type': 'empty'
            }
        
        # Add to history
        self.history.append({
            'command': command,
            'timestamp': time.time(),
            'context': context or {}
        })
        
        # Parse command
        try:
            parts = shlex.split(command)
        except ValueError as e:
            return {
                'output': f"Command parsing error: {e}",
                'type': 'error'
            }
        
        if not parts:
            return {
                'output': '',
                'type': 'empty'
            }
        
        cmd_name = parts[0]
        args = parts[1:]
        
        # Check if command exists
        if cmd_name not in self.commands:
            return {
                'output': f"Command '{cmd_name}' not found. Type 'help' for available commands.",
                'type': 'error'
            }
        
        # Execute command
        try:
            handler = self.commands[cmd_name]['handler']
            result = handler(args)
            
            # Ensure result is in correct format
            if isinstance(result, str):
                result = {
                    'output': result,
                    'type': 'text'
                }
            elif not isinstance(result, dict):
                result = {
                    'output': str(result),
                    'type': 'text'
                }
            
            # Add metadata
            result['command'] = command
            result['timestamp'] = time.time()
            
            return result
            
        except Exception as e:
            return {
                'output': f"Command execution error: {e}",
                'type': 'error',
                'command': command,
                'timestamp': time.time()
            }
    
    def get_available_commands(self) -> Dict[str, str]:
        """Get list of available commands with descriptions."""
        return {
            name: info.get('description', 'No description')
            for name, info in self.commands.items()
        }
    
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get command history."""
        history_list = list(self.history)
        history_list.reverse()  # Most recent first
        return history_list[:limit]
    
    def clear_history(self):
        """Clear command history."""
        self.history.clear()
    
    def add_crawl4ai_commands(self):
        """Add Crawl4AI-specific commands."""
        
        @self.command('crawl4ai-status')
        def crawl4ai_status_command(args):
            """Show Crawl4AI integration status."""
            try:
                import crawl4ai
                return {
                    'output': f"Crawl4AI version: {crawl4ai.__version__}\\nIntegration: Active",
                    'type': 'text'
                }
            except ImportError:
                return {
                    'output': "Crawl4AI not installed",
                    'type': 'warning'
                }
        
        @self.command('crawl4ai-test')
        def crawl4ai_test_command(args):
            """Test Crawl4AI functionality."""
            try:
                from crawl4ai import WebCrawler
                
                url = args[0] if args else "https://example.com"
                
                # This would be a simple test - in real implementation,
                # you'd want to make this async and show progress
                return {
                    'output': f"Testing Crawl4AI with URL: {url}\\n(This is a demo - real implementation would crawl the URL)",
                    'type': 'text'
                }
            except ImportError:
                return {
                    'output': "Crawl4AI not available",
                    'type': 'error'
                }
            except Exception as e:
                return {
                    'output': f"Crawl4AI test error: {e}",
                    'type': 'error'
                }
