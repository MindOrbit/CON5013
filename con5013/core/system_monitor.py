"""
Con5013 System Monitor
Real-time system monitoring and performance tracking for Flask applications.
"""

import time
import platform
from typing import Dict, Any, Optional

class SystemMonitor:
    """
    System monitoring and performance tracking for Con5013.
    
    Provides real-time system metrics including CPU, memory, disk usage,
    and application-specific performance data.
    """
    
    def __init__(self, app, config):
        self.app = app
        self.config = config
        self.update_interval = config.get('CON5013_SYSTEM_UPDATE_INTERVAL', 5)
        self.monitor_cpu = config.get('CON5013_MONITOR_CPU', True)
        self.monitor_memory = config.get('CON5013_MONITOR_MEMORY', True)
        self.monitor_disk = config.get('CON5013_MONITOR_DISK', True)
        self.monitor_network = config.get('CON5013_MONITOR_NETWORK', True)
        self.monitor_gpu = config.get('CON5013_MONITOR_GPU', True)
        
        # Try to import psutil for system monitoring
        self.psutil_available = False
        try:
            import psutil
            self.psutil = psutil
            self.psutil_available = True
        except ImportError:
            self.psutil = None

        # Try to import NVIDIA NVML via pynvml
        self.pynvml_available = False
        self.nvml = None
        if self.monitor_gpu:
            try:
                import pynvml
                self.nvml = pynvml
                try:
                    self.nvml.nvmlInit()
                    self.pynvml_available = True
                except Exception:
                    self.nvml = None
            except Exception:
                self.nvml = None
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current system statistics."""
        stats = {
            'timestamp': time.time(),
            'system': self._get_system_info(),
            'application': self._get_application_stats(),
            'psutil_available': self.psutil_available
        }
        
        if self.psutil_available:
            if self.monitor_cpu:
                stats['cpu'] = self._get_cpu_stats()
            
            if self.monitor_memory:
                stats['memory'] = self._get_memory_stats()
            
            if self.monitor_disk:
                stats['disk'] = self._get_disk_stats()
            
            if self.monitor_network:
                stats['network'] = self._get_network_stats()

        # GPU stats (handled separately and safely)
        if self.monitor_gpu:
            try:
                gpu_stats = self._get_gpu_stats()
                if gpu_stats is not None:
                    stats['gpus'] = gpu_stats
            except Exception:
                # Do not crash if GPU collection fails
                pass
        
        return stats
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information."""
        return {
            'platform': platform.platform(),
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'hostname': platform.node()
        }
    
    def _get_application_stats(self) -> Dict[str, Any]:
        """Get Flask application statistics."""
        stats = {
            'name': self.app.name,
            'debug': self.app.debug,
            'testing': self.app.testing,
            'routes_count': len(self.app.url_map._rules),
            'blueprints_count': len(self.app.blueprints),
            'extensions': list(getattr(self.app, 'extensions', {}).keys())
        }
        
        # Add uptime if start_time is available
        if hasattr(self.app, 'start_time'):
            stats['uptime_seconds'] = time.time() - self.app.start_time
            stats['uptime_formatted'] = self._format_uptime(stats['uptime_seconds'])
        
        return stats
    
    def _get_cpu_stats(self) -> Dict[str, Any]:
        """Get CPU usage statistics."""
        if not self.psutil_available:
            return {'error': 'psutil not available'}
        
        try:
            return {
                'usage_percent': self.psutil.cpu_percent(interval=1),
                'count_logical': self.psutil.cpu_count(logical=True),
                'count_physical': self.psutil.cpu_count(logical=False),
                'frequency': self.psutil.cpu_freq()._asdict() if self.psutil.cpu_freq() else None,
                'load_average': self.psutil.getloadavg() if hasattr(self.psutil, 'getloadavg') else None
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        if not self.psutil_available:
            return {'error': 'psutil not available'}
        
        try:
            virtual_memory = self.psutil.virtual_memory()
            swap_memory = self.psutil.swap_memory()
            
            return {
                'virtual': {
                    'total_bytes': virtual_memory.total,
                    'available_bytes': virtual_memory.available,
                    'used_bytes': virtual_memory.used,
                    'free_bytes': virtual_memory.free,
                    'percent': virtual_memory.percent,
                    'total_gb': round(virtual_memory.total / (1024**3), 2),
                    'used_gb': round(virtual_memory.used / (1024**3), 2),
                    'available_gb': round(virtual_memory.available / (1024**3), 2)
                },
                'swap': {
                    'total_bytes': swap_memory.total,
                    'used_bytes': swap_memory.used,
                    'free_bytes': swap_memory.free,
                    'percent': swap_memory.percent,
                    'total_gb': round(swap_memory.total / (1024**3), 2),
                    'used_gb': round(swap_memory.used / (1024**3), 2)
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_disk_stats(self) -> Dict[str, Any]:
        """Get disk usage statistics."""
        if not self.psutil_available:
            return {'error': 'psutil not available'}
        
        try:
            # Get disk usage for root partition
            disk_usage = self.psutil.disk_usage('/')
            
            # Get disk I/O statistics
            disk_io = self.psutil.disk_io_counters()
            
            stats = {
                'usage': {
                    'total_bytes': disk_usage.total,
                    'used_bytes': disk_usage.used,
                    'free_bytes': disk_usage.free,
                    'percent': round((disk_usage.used / disk_usage.total) * 100, 2),
                    'total_gb': round(disk_usage.total / (1024**3), 2),
                    'used_gb': round(disk_usage.used / (1024**3), 2),
                    'free_gb': round(disk_usage.free / (1024**3), 2)
                }
            }
            
            if disk_io:
                stats['io'] = {
                    'read_count': disk_io.read_count,
                    'write_count': disk_io.write_count,
                    'read_bytes': disk_io.read_bytes,
                    'write_bytes': disk_io.write_bytes,
                    'read_time': disk_io.read_time,
                    'write_time': disk_io.write_time
                }
            
            return stats
        except Exception as e:
            return {'error': str(e)}
    
    def _get_network_stats(self) -> Dict[str, Any]:
        """Get network usage statistics."""
        if not self.psutil_available:
            return {'error': 'psutil not available'}
        
        try:
            net_io = self.psutil.net_io_counters()
            net_connections = len(self.psutil.net_connections())
            
            return {
                'io': {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv,
                    'errin': net_io.errin,
                    'errout': net_io.errout,
                    'dropin': net_io.dropin,
                    'dropout': net_io.dropout
                },
                'connections_count': net_connections
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status."""
        stats = self.get_current_stats()
        health = {
            'status': 'healthy',
            'issues': [],
            'warnings': [],
            'timestamp': time.time()
        }
        
        if self.psutil_available:
            # Check CPU usage
            if 'cpu' in stats and stats['cpu'].get('usage_percent', 0) > 90:
                health['warnings'].append('High CPU usage detected')
                health['status'] = 'warning'
            
            # Check memory usage
            if 'memory' in stats and stats['memory']['virtual'].get('percent', 0) > 90:
                health['warnings'].append('High memory usage detected')
                health['status'] = 'warning'
            
            # Check disk usage
            if 'disk' in stats and stats['disk']['usage'].get('percent', 0) > 90:
                health['warnings'].append('High disk usage detected')
                health['status'] = 'warning'
        
        # Check if there are critical issues
        if health['issues']:
            health['status'] = 'critical'
        
        return health

    def add_crawl4ai_metrics(self):
        """Add Crawl4AI-specific monitoring metrics."""
        # This would be implemented to monitor Crawl4AI specific metrics
        # such as active crawling jobs, queue sizes, etc.
        pass

    def get_processes(self, sort_by: str = 'cpu', page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """Return a paginated list of processes sorted by CPU or memory.

        sort_by: 'cpu' or 'memory'
        page: 1-based page index
        page_size: items per page
        """
        result = {
            'available': self.psutil_available,
            'sort_by': sort_by,
            'page': page,
            'page_size': page_size,
            'total': 0,
            'processes': []
        }

        if not self.psutil_available:
            return result

        try:
            # First pass to prime CPU percent measurements
            proc_list = list(self.psutil.process_iter(['pid', 'name', 'status']))
            for p in proc_list:
                try:
                    p.cpu_percent(None)
                except Exception:
                    continue
            # Short sleep to allow percent interval
            time.sleep(0.1)

            procs = []
            for p in proc_list:
                try:
                    cpu = p.cpu_percent(None)
                    try:
                        mem = p.memory_info().rss
                    except Exception:
                        mem = 0
                    try:
                        status = p.status()
                    except Exception:
                        status = p.info.get('status', '')
                    procs.append({
                        'pid': p.info.get('pid'),
                        'name': p.info.get('name') or '',
                        'status': status or '',
                        'cpu_percent': round((cpu or 0.0), 1),
                        'memory_bytes': int(mem or 0)
                    })
                except Exception:
                    continue

            if sort_by == 'memory':
                procs.sort(key=lambda x: x['memory_bytes'], reverse=True)
            else:
                procs.sort(key=lambda x: x['cpu_percent'], reverse=True)

            total = len(procs)
            result['total'] = total
            # pagination
            start = max(0, (page - 1) * page_size)
            end = start + page_size
            result['processes'] = procs[start:end]
            return result
        except Exception as e:
            return {**result, 'error': str(e)}

    # =========================
    # GPU Monitoring
    # =========================
    def _get_gpu_stats(self) -> Optional[Dict[str, Any]]:
        """Collect GPU usage and temperatures across multiple GPUs.

        Tries, in order:
        - pynvml (NVIDIA NVML)
        - nvidia-smi CLI (if available)
        Future work: support AMD via rocm-smi or other backends.
        """
        # NVML path
        if self.pynvml_available and self.nvml is not None:
            try:
                nvml = self.nvml
                count = nvml.nvmlDeviceGetCount()
                gpus = []
                for i in range(count):
                    try:
                        handle = nvml.nvmlDeviceGetHandleByIndex(i)
                        name = nvml.nvmlDeviceGetName(handle).decode('utf-8', 'ignore') if isinstance(nvml.nvmlDeviceGetName(handle), bytes) else nvml.nvmlDeviceGetName(handle)
                        mem = nvml.nvmlDeviceGetMemoryInfo(handle)
                        util = None
                        try:
                            util = nvml.nvmlDeviceGetUtilizationRates(handle).gpu
                        except Exception:
                            util = None
                        temp = None
                        try:
                            temp = nvml.nvmlDeviceGetTemperature(handle, nvml.NVML_TEMPERATURE_GPU)
                        except Exception:
                            temp = None
                        power = None
                        try:
                            power = nvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
                        except Exception:
                            power = None
                        driver = None
                        try:
                            driver = nvml.nvmlSystemGetDriverVersion().decode('utf-8', 'ignore')
                        except Exception:
                            driver = None
                        gpus.append({
                            'index': i,
                            'vendor': 'NVIDIA',
                            'name': name,
                            'memory_total_mb': int(getattr(mem, 'total', 0) / (1024*1024)),
                            'memory_used_mb': int(getattr(mem, 'used', 0) / (1024*1024)),
                            'utilization_percent': util,
                            'temperature_c': temp,
                            'power_watts': power,
                            'driver_version': driver,
                        })
                    except Exception:
                        # Skip device on any error retrieving its metrics
                        continue
                return {
                    'available': True,
                    'backend': 'pynvml',
                    'count': len(gpus),
                    'devices': gpus,
                }
            except Exception:
                # fall through to CLI method
                pass

        # nvidia-smi CLI path
        try:
            import subprocess, shlex
            query = 'index,name,utilization.gpu,temperature.gpu,memory.total,memory.used,driver_version'
            cmd = f"nvidia-smi --query-gpu={query} --format=csv,noheader,nounits"
            proc = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1.5)
            if proc.returncode == 0:
                out = proc.stdout.decode('utf-8', 'ignore').strip().splitlines()
                gpus = []
                for line in out:
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 7:
                        idx, name, util, temp, mem_total, mem_used, driver = parts[:7]
                        try:
                            gpus.append({
                                'index': int(idx),
                                'vendor': 'NVIDIA',
                                'name': name,
                                'utilization_percent': int(util),
                                'temperature_c': int(temp),
                                'memory_total_mb': int(mem_total),
                                'memory_used_mb': int(mem_used),
                                'driver_version': driver,
                            })
                        except Exception:
                            continue
                return {
                    'available': True,
                    'backend': 'nvidia-smi',
                    'count': len(gpus),
                    'devices': gpus,
                }
        except Exception:
            pass

        # Fallback: no GPU info
        return {
            'available': False,
            'backend': None,
            'count': 0,
            'devices': []
        }
