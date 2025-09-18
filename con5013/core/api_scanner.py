"""
Con5013 API Scanner
Automatic API endpoint discovery and testing for Flask applications.
"""

import time
import requests
import re
from typing import List, Dict, Any, Optional, Iterable, Tuple
from urllib.parse import urljoin, urlparse

class APIScanner:
    """
    API endpoint discovery and testing system for Con5013.
    
    Automatically discovers Flask routes and provides comprehensive
    testing capabilities with performance metrics.
    """
    
    def __init__(self, app, config):
        self.app = app
        self.config = config
        self.timeout = config.get('CON5013_API_TEST_TIMEOUT', 10)
        self.include_methods = config.get('CON5013_API_INCLUDE_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
        # Show Con5013 endpoints by default so users can inspect and test them too
        self.exclude_endpoints = config.get('CON5013_API_EXCLUDE_ENDPOINTS', ['/static'])
        self.base_url = None

    @staticmethod
    def normalize_allowlist(allowlist: Optional[Iterable[Any]]) -> List[str]:
        """Normalize an allowlist configuration value to a list of strings."""
        if not allowlist:
            return []
        if isinstance(allowlist, (str, bytes)):
            allowlist = [allowlist]

        normalized: List[str] = []
        for item in allowlist:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized

    @classmethod
    def describe_policy_from_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Return a human-readable snapshot of the external scanning policy."""
        allow_external = bool(config.get('CON5013_API_ALLOW_EXTERNAL', True))
        allowlist = cls.normalize_allowlist(config.get('CON5013_API_EXTERNAL_ALLOWLIST'))

        if not allow_external:
            mode = 'disabled'
        elif allowlist:
            mode = 'allowlist'
        else:
            mode = 'allow_all'

        return {
            'allow_external': allow_external,
            'external_allowlist': allowlist,
            'mode': mode,
        }

    def get_external_policy(self) -> Dict[str, Any]:
        """Expose the currently active external scanning policy."""
        return self.describe_policy_from_config(self.config)

    def _get_base_url(self) -> str:
        """Get the base URL for the application."""
        if self.base_url:
            return self.base_url
        
        # Try to determine base URL from Flask app
        with self.app.test_request_context():
            from flask import request
            self.base_url = request.url_root.rstrip('/')
        
        return self.base_url or 'http://localhost:5000'

    def _is_local_url(self, url: str) -> bool:
        """Return True if the absolute URL points to this Flask app base URL."""
        try:
            if not url:
                return False
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            base = urlparse(self._get_base_url())
            # Compare host:port and scheme; treat 127.0.0.1 and localhost as equivalent
            def host_key(p):
                h = (p.hostname or '').lower()
                if h in ('127.0.0.1', '::1'):
                    h = 'localhost'
                return (p.scheme or 'http', h, p.port or (443 if p.scheme=='https' else 80))
            return host_key(parsed) == host_key(base)
        except Exception:
            return False

    def _to_path(self, url_or_path: str) -> str:
        """Return just the path (with query if provided) for a URL or path."""
        if not url_or_path:
            return '/'
        if url_or_path.startswith('http://') or url_or_path.startswith('https://'):
            p = urlparse(url_or_path)
            path = p.path or '/'
            if p.query:
                path = f"{path}?{p.query}"
            return path
        return url_or_path if url_or_path.startswith('/') else f"/{url_or_path}"
    
    def discover_endpoints(self, include_con5013: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Discover all API endpoints in the Flask application.

        include_con5013: when False, hides Con5013's own routes (e.g., /con5013/*).
        Defaults to True if not specified.
        """
        endpoints = []
        if include_con5013 is None:
            include_con5013 = True
        
        # Build effective exclude list based on include_con5013 flag
        prefix = self.config.get('CON5013_URL_PREFIX', '/con5013')
        excludes = list(self.exclude_endpoints)
        if include_con5013:
            excludes = [e for e in excludes if e and (prefix not in e and e not in (prefix,))]

        protected_list = set(self.config.get('CON5013_API_PROTECTED_ENDPOINTS', []))

        for rule in self.app.url_map.iter_rules():
            # Skip excluded endpoints
            if any(exclude in rule.rule for exclude in excludes):
                continue

            # Optionally exclude Con5013 endpoints
            if not include_con5013:
                if rule.rule.startswith(prefix):
                    continue
            
            # Filter methods
            methods = [method for method in rule.methods 
                      if method in self.include_methods]
            
            if not methods:
                continue
            
            # Get endpoint function
            endpoint_func = self.app.view_functions.get(rule.endpoint)
            
            sample_path = self._build_sample_path(rule)
            # Determine if this rule is protected (exact or prefix match)
            is_protected = False
            for p in protected_list:
                if not p:
                    continue
                if rule.rule == p or rule.rule.startswith(p):
                    is_protected = True
                    break

            endpoint_info = {
                'rule': rule.rule,
                'endpoint': rule.endpoint,
                'methods': sorted(methods),
                'description': self._get_endpoint_description(endpoint_func),
                'parameters': self._extract_parameters(rule),
                'url': urljoin(self._get_base_url(), rule.rule),
                'sample_path': sample_path,
                'protected': is_protected,
                'status': 'discovered',
                'last_tested': None,
                'test_results': {}
            }
            
            endpoints.append(endpoint_info)
        
        return sorted(endpoints, key=lambda x: x['rule'])
    
    def _get_endpoint_description(self, func) -> str:
        """Get description from endpoint function docstring."""
        if func and hasattr(func, '__doc__') and func.__doc__:
            # Get first line of docstring
            return func.__doc__.strip().split('\\n')[0]
        return "No description available"
    
    def _extract_parameters(self, rule) -> List[Dict[str, str]]:
        """Extract parameters from URL rule."""
        parameters = []
        
        for arg in rule.arguments:
            param_info = {
                'name': arg,
                'type': 'string',  # Default type
                'required': True,
                'location': 'path'
            }
            
            # Try to determine type from rule defaults
            if rule.defaults and arg in rule.defaults:
                param_info['required'] = False
                param_info['default'] = rule.defaults[arg]
            
            parameters.append(param_info)
        
        return parameters

    def _build_sample_path(self, rule) -> str:
        """Build a sample concrete path by replacing path parameters with example values."""
        path = rule.rule
        converters = getattr(rule, '_converters', {}) or {}

        def sample_for(conv) -> str:
            name = conv.__class__.__name__.lower()
            if 'integer' in name or 'int' in name:
                return '1'
            if 'float' in name:
                return '1.0'
            if 'uuid' in name:
                return '123e4567-e89b-12d3-a456-426614174000'
            if 'path' in name or 'string' in name or 'unicode' in name or 'any' in name:
                return 'sample'
            if 'bool' in name:
                return 'true'
            return 'sample'

        # Replace occurrences like <int:id> or <id>
        pattern = re.compile(r'<([^<>:]+:)?([^<>]+)?>')

        def repl(m):
            param_name = m.group(2) or ''
            conv = converters.get(param_name)
            return sample_for(conv) if conv else 'sample'

        return pattern.sub(repl, path)
    
    def test_endpoint(self, endpoint_url: str, method: str = 'GET',
                     data: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """Test a specific API endpoint."""
        start_time = time.time()

        try:
            method_up = method.upper()
            is_absolute = endpoint_url.lower().startswith('http://') or endpoint_url.lower().startswith('https://')
            policy = None

            if is_absolute:
                allowed, reason, policy = self._check_external_policy(endpoint_url)
                if not allowed:
                    return {
                        'status': 'blocked',
                        'status_code': None,
                        'error': reason,
                        'response_time_ms': round((time.time() - start_time) * 1000, 2),
                        'timestamp': time.time(),
                        'policy': policy or self.get_external_policy(),
                    }

            # Prefer Flask test client for app-local routes (relative OR absolute pointing to our base)
            if (not is_absolute) or self._is_local_url(endpoint_url):
                # Call using Flask test client for app-relative paths
                path = self._to_path(endpoint_url)
                with self.app.test_client() as client:
                    func = getattr(client, method_up.lower())
                    # Split query if present
                    if '?' in path:
                        path_only, query = path.split('?', 1)
                    else:
                        path_only, query = path, ''
                    if data and method_up in ['POST', 'PUT', 'PATCH']:
                        response = func(path_only, json=data, headers=headers or {})
                    else:
                        # Merge any data into query string
                        qs = data or {}
                        response = func(path_only, query_string=qs, headers=headers or {})
                    status_code = response.status_code
                    content_type = response.headers.get('Content-Type', 'unknown')
                    content = response.get_data()
                    text = response.get_data(as_text=True)
                    headers_map = dict(response.headers)
                    try:
                        json_resp = response.get_json(silent=True)
                    except Exception:
                        json_resp = None
            else:
                # External HTTP call
                request_kwargs = {
                    'timeout': self.timeout,
                    'headers': headers or {}
                }
                if data:
                    if method_up in ['POST', 'PUT', 'PATCH']:
                        request_kwargs['json'] = data
                    else:
                        request_kwargs['params'] = data
                resp = requests.request(method_up, endpoint_url, **request_kwargs)
                status_code = resp.status_code
                content_type = resp.headers.get('Content-Type', 'unknown')
                content = resp.content
                text = resp.text
                headers_map = dict(resp.headers)
                try:
                    json_resp = resp.json()
                except Exception:
                    json_resp = None
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Analyze response
            result = {
                'status': 'success' if status_code < 400 else 'error',
                'status_code': status_code,
                'response_time_ms': round(response_time, 2),
                'content_type': content_type,
                'content_length': len(content or b''),
                'headers': headers_map,
                'timestamp': time.time()
            }
            
            # Try to parse JSON response
            try:
                if json_resp is not None or 'application/json' in content_type:
                    result['json_response'] = json_resp if json_resp is not None else None
                else:
                    result['text_response'] = (text or '')[:500]  # Truncate long responses
            except Exception:
                result['text_response'] = (text or '')[:500]
            
            return result
            
        except requests.exceptions.Timeout:
            return {
                'status': 'timeout',
                'error': f'Request timed out after {self.timeout} seconds',
                'response_time_ms': (time.time() - start_time) * 1000,
                'timestamp': time.time()
            }
        except requests.exceptions.ConnectionError:
            return {
                'status': 'connection_error',
                'error': 'Could not connect to the endpoint',
                'response_time_ms': (time.time() - start_time) * 1000,
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'response_time_ms': (time.time() - start_time) * 1000,
                'timestamp': time.time()
            }

    def _check_external_policy(self, url: str) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Validate that an external URL complies with the configured policy."""
        policy = self.get_external_policy()

        if self._is_local_url(url):
            return True, None, policy

        is_absolute = url.lower().startswith('http://') or url.lower().startswith('https://')
        if not is_absolute:
            return True, None, policy

        if not policy.get('allow_external', True):
            return False, 'External API testing is disabled by configuration (CON5013_API_ALLOW_EXTERNAL=False).', policy

        allowlist = policy.get('external_allowlist', [])
        if allowlist and not self._is_url_allowlisted(url, allowlist):
            return False, 'The requested URL is not present in CON5013_API_EXTERNAL_ALLOWLIST.', policy

        return True, None, policy

    def _is_url_allowlisted(self, url: str, allowlist: List[str]) -> bool:
        """Return True when the given absolute URL matches an allowlisted entry."""
        try:
            parsed = urlparse(url)
        except Exception:
            return False

        if not parsed.scheme or not parsed.netloc:
            return False

        path = parsed.path or '/'
        query = parsed.query

        for entry in allowlist:
            entry_str = str(entry)
            if not entry_str:
                continue

            if url == entry_str:
                return True

            try:
                entry_parsed = urlparse(entry_str)
            except Exception:
                continue

            if not entry_parsed.scheme or not entry_parsed.netloc:
                continue

            if parsed.scheme != entry_parsed.scheme or parsed.netloc != entry_parsed.netloc:
                continue

            if entry_parsed.query:
                if query != entry_parsed.query:
                    continue
            allow_path = entry_parsed.path or '/'
            if allow_path in ('', '/'):
                return True

            normalized_allow = allow_path.rstrip('/')
            normalized_path = path.rstrip('/')

            if normalized_path == normalized_allow:
                return True

            if normalized_allow and path.startswith(normalized_allow + '/'):
                return True

        return False
    
    def test_all_endpoints(self, include_con5013: Optional[bool] = None) -> Dict[str, Any]:
        """Test all discovered endpoints."""
        endpoints = self.discover_endpoints(include_con5013=include_con5013)
        results = {
            'total_endpoints': len(endpoints),
            'tested_endpoints': 0,
            'successful_tests': 0,
            'failed_tests': 0,
            'total_time_ms': 0,
            'results': [],
            'summary': {},
            'timestamp': time.time()
        }
        
        start_time = time.time()
        
        for endpoint in endpoints:
            # Test each method for the endpoint
            for method in endpoint['methods']:
                if endpoint.get('protected'):
                    continue
                # Use sample_path to ensure local testing via test_client with example params
                test_result = self.test_endpoint(endpoint.get('sample_path') or endpoint['rule'], method)
                
                endpoint_result = {
                    'endpoint': endpoint['rule'],
                    'url': endpoint['url'],
                    'method': method,
                    'description': endpoint['description'],
                    **test_result
                }
                
                results['results'].append(endpoint_result)
                results['tested_endpoints'] += 1
                
                if test_result['status'] == 'success':
                    results['successful_tests'] += 1
                else:
                    results['failed_tests'] += 1
        
        # Calculate summary statistics
        results['total_time_ms'] = round((time.time() - start_time) * 1000, 2)
        results['success_rate'] = (results['successful_tests'] / results['tested_endpoints'] * 100) if results['tested_endpoints'] > 0 else 0
        results['average_response_time'] = sum(r.get('response_time_ms', 0) for r in results['results']) / len(results['results']) if results['results'] else 0
        
        # Group results by status
        results['summary'] = {
            'by_status': {},
            'by_method': {},
            'slowest_endpoints': [],
            'fastest_endpoints': []
        }
        
        # Analyze by status
        for result in results['results']:
            status = result['status']
            results['summary']['by_status'][status] = results['summary']['by_status'].get(status, 0) + 1
        
        # Analyze by method
        for result in results['results']:
            method = result['method']
            results['summary']['by_method'][method] = results['summary']['by_method'].get(method, 0) + 1
        
        # Find slowest and fastest endpoints
        sorted_by_time = sorted(results['results'], key=lambda x: x.get('response_time_ms', 0))
        results['summary']['fastest_endpoints'] = sorted_by_time[:3]
        results['summary']['slowest_endpoints'] = sorted_by_time[-3:]
        
        return results
    
    def get_endpoint_documentation(self) -> Dict[str, Any]:
        """Generate API documentation from discovered endpoints."""
        endpoints = self.discover_endpoints()
        
        documentation = {
            'title': f'{self.app.name} API Documentation',
            'version': '1.0.0',
            'base_url': self._get_base_url(),
            'total_endpoints': len(endpoints),
            'endpoints': [],
            'generated_at': time.time()
        }
        
        for endpoint in endpoints:
            doc_entry = {
                'path': endpoint['rule'],
                'methods': endpoint['methods'],
                'description': endpoint['description'],
                'parameters': endpoint['parameters'],
                'examples': self._generate_examples(endpoint)
            }
            
            documentation['endpoints'].append(doc_entry)
        
        return documentation
    
    def _generate_examples(self, endpoint: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate example requests for an endpoint."""
        examples = []
        
        for method in endpoint['methods']:
            example = {
                'method': method,
                'url': endpoint['url'],
                'description': f'{method} request to {endpoint["rule"]}'
            }
            
            # Add example data for POST/PUT requests
            if method in ['POST', 'PUT', 'PATCH']:
                example['example_data'] = {
                    'example_field': 'example_value'
                }
            
            examples.append(example)
        
        return examples
