/**
 * Con5013 Console Extension JavaScript
 * Interactive console functionality for Flask applications
 */

const CON5013_SCRIPT_ELEMENT = typeof document !== 'undefined' ? document.currentScript : null;
const CON5013_VALID_TABS = ['logs', 'terminal', 'api', 'system'];

function ensureCon5013ReadyPromise() {
    if (typeof window === 'undefined') {
        return null;
    }

    if (window.CON5013_READY && window.CON5013_READY_DETAIL) {
        return Promise.resolve(window.CON5013_READY_DETAIL);
    }

    if (window.CON5013_READY_PROMISE && typeof window.CON5013_READY_PROMISE.then === 'function') {
        return window.CON5013_READY_PROMISE;
    }

    window.CON5013_READY_PROMISE = new Promise(resolve => {
        const handler = event => {
            window.removeEventListener('con5013:ready', handler);
            resolve(event?.detail ?? { instance: window.con5013, kind: 'modern', api: window.con5013 });
        };
        try {
            window.addEventListener('con5013:ready', handler, { once: true });
        } catch (_) {
            window.addEventListener('con5013:ready', handler);
        }
    });

    return window.CON5013_READY_PROMISE;
}

async function openCon5013Console(options = {}) {
    if (typeof window === 'undefined') {
        throw new Error('Con5013 console is not available in this environment');
    }

    const readyPromise = ensureCon5013ReadyPromise();
    if (!readyPromise) {
        throw new Error('Con5013 readiness promise could not be created');
    }

    const detail = await readyPromise;
    const instance = detail?.instance || window.con5013;

    if (!instance || typeof instance.openConsole !== 'function') {
        throw new Error('Con5013 console instance is not ready');
    }

    return instance.openConsole(options);
}

if (typeof window !== 'undefined') {
    window.openCon5013Console = openCon5013Console;
    window.launchCon5013Console = openCon5013Console;
    ensureCon5013ReadyPromise();
}

class Con5013Console {
    constructor(options = {}) {
        this.options = {
            baseUrl: options.baseUrl || '/con5013',
            hotkey: options.hotkey || 'Alt+C',
            updateInterval: options.updateInterval || 5000,
            maxLogEntries: options.maxLogEntries || 1000,
            // Floating button behavior (auto overlay trigger)
            autoFloatingButton: options.autoFloatingButton !== undefined ? options.autoFloatingButton : true,
            floatingButtonPosition: options.floatingButtonPosition || 'bottom-right',
            hideFabWhenOpen: options.hideFabWhenOpen !== undefined ? options.hideFabWhenOpen : true,
            hideFabIfCustomButton: options.hideFabIfCustomButton !== undefined ? options.hideFabIfCustomButton : true,
            customButtonSelector: options.customButtonSelector || '[data-con5013-button]',
            ...options
        };

        this.options.baseUrl = this.normalizeBaseUrl(this.options.baseUrl);

        this.isOpen = false;
        this.currentTab = 'logs';
        this.currentLogSource = 'flask';
        this.currentLogLevel = '';
        this.currentLogSort = 'desc';
        this.terminalHistory = [];
        this.terminalHistoryIndex = -1;
        this.endpoints = [];
        this.apiFilters = { active: true, excluded: false, system: false };
        this.apiTestResults = [];
        this.apiSummary = null;
        this.apiVisibleEndpoints = [];
        this.consolePrefix = this.deriveConsolePrefix(this.options.baseUrl);
        this.apiFilterElements = { dropdown: null, toggle: null, menu: null, summary: null };
        this.systemStats = {};
        this.features = {
            logs: true,
            terminal: true,
            api_scanner: true,
            system_monitor: true,
            allow_log_clear: true,
        };
        this.systemMetrics = {
            system_info: true,
            application: true,
            cpu: true,
            memory: true,
            disk: true,
            network: true,
            gpu: true,
        };
        this.connectivityOk = null; // null=unknown, true=ok, false=error
        this.prevNetwork = null;
        this.logAutoScrollPaused = false;

        this.init();
    }

    normalizeBaseUrl(baseUrl) {
        let normalized = '';
        if (typeof baseUrl === 'string') {
            normalized = baseUrl.trim();
        }
        if (!normalized) {
            normalized = '/con5013';
        }
        if (/^https?:\/\//i.test(normalized)) {
            const trimmed = normalized.replace(/\/+$/, '');
            return trimmed || normalized;
        }
        if (!normalized.startsWith('/')) {
            normalized = `/${normalized}`;
        }
        normalized = normalized.replace(/\/+$/, '');
        return normalized;
    }

    deriveConsolePrefix(baseUrl) {
        if (!baseUrl) {
            return '/';
        }
        if (/^https?:\/\//i.test(baseUrl)) {
            try {
                const url = new URL(baseUrl);
                const path = url.pathname ? url.pathname.replace(/\/+$/, '') : '';
                return path || '/';
            } catch (_) {
                const stripped = baseUrl.replace(/^https?:\/\/[^/]+/i, '');
                const sanitized = stripped.replace(/\/+$/, '');
                return sanitized || '/';
            }
        }
        if (!baseUrl.startsWith('/')) {
            const sanitized = `/${baseUrl}`.replace(/\/+$/, '');
            return sanitized || '/';
        }
        const cleaned = baseUrl.replace(/\/+$/, '');
        return cleaned || '/';
    }

    init() {
        this.ensureStylesInjected();
        this.createConsoleHTML();
        this.createFloatingButton();
        this.bindEvents();
        this.setupHotkey();
        this.updateApiFilterSummary();
        this.loadInitialData();
        
        // Start periodic updates
        this.startPeriodicUpdates();
    }
    
    ensureStylesInjected() {
        try {
            const href = `${this.options.baseUrl}/static/css/con5013.css`;
            const absoluteHref = (() => {
                try {
                    return new URL(href, window.location.origin).href;
                } catch (_) {
                    return href;
                }
            })();
            const already = Array.from(document.querySelectorAll('link[rel="stylesheet"]'))
                .some(link => {
                    const current = link?.href || '';
                    if (!current) return false;
                    try {
                        return new URL(current, window.location.href).href === absoluteHref;
                    } catch (_) {
                        return current === href || current.endsWith('/static/css/con5013.css');
                    }
                });
            if (!already) {
                const link = document.createElement('link');
                link.rel = 'stylesheet';
                link.href = href;
                link.id = 'con5013-styles';
                document.head.appendChild(link);
                link.addEventListener('load', () => {
                    this.onStylesReady();
                });
            }
            if (already) {
                setTimeout(() => this.onStylesReady(), 0);
            }
        } catch (e) {
            console.debug('Con5013: could not auto-inject styles', e);
        }
    }

    onStylesReady() {
        const overlay = document.getElementById('con5013-overlay');
        if (overlay && overlay.style && overlay.style.display === 'none') {
            overlay.style.display = '';
        }
        const fab = document.getElementById('con5013-fab');
        if (fab && fab.style && fab.style.display === 'none') {
            fab.style.display = '';
            this.updateFabVisibility();
        }
        // Refresh connectivity paint once DOM is ready
        this.paintConnectivity();
    }

    createConsoleHTML() {
        const consoleHTML = `
            <div id="con5013-overlay" class="con5013-overlay" style="display:none;">
                <div class="con5013-console">
                    <div class="con5013-header">
                        <h3 class="con5013-title">
                            <div class="con5013-logo" aria-hidden="true">
                                <svg id="con5013-b-icon" width="48" height="24" viewBox="0 0 240 120" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="CON5013 monogram icon">
                                  <rect x="8" y="8" rx="16" ry="16" width="224" height="104" fill="#0d1520" stroke="#1f2a37" stroke-width="2" />
                                  <path d="M56 60 l36 -24" stroke="#31d0aa" stroke-width="8" stroke-linecap="round" fill="none" />
                                  <path d="M56 60 l36 24" stroke="#31d0aa" stroke-width="8" stroke-linecap="round" fill="none" />
                                  <path d="M188 36 l-40 48" stroke="#7aa2f7" stroke-width="8" stroke-linecap="round" fill="none" />
                                  <path d="M112 60 h16" stroke="#cbd5e1" stroke-width="8" stroke-linecap="round" />
                                </svg>
                            </div>
                            CON5013
                        </h3>
                        <button class="con5013-close" onclick="con5013.close()">&times;</button>
                    </div>
                    
                    <div class="con5013-tabs">
                        <button class="con5013-tab active" data-tab="logs">Logs</button>
                        <button class="con5013-tab" data-tab="terminal">Terminal</button>
                        <button class="con5013-tab" data-tab="api">API</button>
                        <button class="con5013-tab" data-tab="system">System</button>
                    </div>
                    
                    <div class="con5013-content">
                        <!-- Logs Tab -->
                        <div id="con5013-logs-tab" class="con5013-tab-content active">
                            <div class="con5013-ascii">
  __|   _ \\   \\ |  __|    \\ _ | __ /
 (     (   | .  | __ \\  (  |  |  _ \\
\\___| \\___/ _|\\_| ___/ \\__/  _| ___/
            </div>
                            <div class="con5013-subtitle">Flask Application Console & Monitor</div>
                            
                            <div class="con5013-api-controls" style="display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
                                <label style="color: var(--con5013-text-muted); font-size:12px;">Source</label>
                                <select id="con5013-log-source" class="con5013-select"></select>
                                <label style="color: var(--con5013-text-muted); font-size:12px;">Level</label>
                                <select id="con5013-log-level" class="con5013-select">
                                    <option value="">All</option>
                                    <option value="DEBUG">DEBUG</option>
                                    <option value="INFO">INFO</option>
                                    <option value="WARNING">WARNING</option>
                                    <option value="ERROR">ERROR</option>
                                    <option value="CRITICAL">CRITICAL</option>
                                </select>
                                <label style="color: var(--con5013-text-muted); font-size:12px;">Sort</label>
                                <select id="con5013-log-sort" class="con5013-select">
                                    <option value="desc">Newest first</option>
                                    <option value="asc">Oldest first</option>
                                </select>
                                <button class="con5013-btn" onclick="con5013.refreshLogs()">Refresh</button>
                                <button class="con5013-btn secondary" data-con5013-clear-logs onclick="con5013.clearLogs()">Clear</button>
                                <button class="con5013-btn secondary" onclick="con5013.exportLogs()">Export</button>
                            </div>
                            
                            <div class="con5013-logs-wrapper">
                                <div id="con5013-logs" class="con5013-logs">
                                    <div class="con5013-log-entry">
                                        <span class="con5013-log-timestamp">16:53:00</span>
                                        <span class="con5013-log-level INFO">INFO</span>
                                        <span class="con5013-log-message">Con5013 console initialized successfully</span>
                                    </div>
                                    <div class="con5013-log-entry">
                                        <span class="con5013-log-timestamp">16:53:01</span>
                                        <span class="con5013-log-level SUCCESS">SUCCESS</span>
                                        <span class="con5013-log-message">Flask application ready</span>
                                    </div>
                                    <div class="con5013-log-entry">
                                        <span class="con5013-log-timestamp">16:53:02</span>
                                        <span class="con5013-log-level INFO">INFO</span>
                                        <span class="con5013-log-message">Database connection established</span>
                                    </div>
                                </div>
                                <div id="con5013-logs-autoscroll-indicator" class="con5013-autoscroll-indicator" style="display:none;">
                                    <span>Auto-scroll paused</span>
                                    <button type="button" id="con5013-logs-resume" class="con5013-autoscroll-resume">Resume</button>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Terminal Tab -->
                        <div id="con5013-terminal-tab" class="con5013-tab-content">
                            <div class="con5013-ascii">
  __|   _ \\   \\ |  __|    \\ _ | __ /
 (     (   | .  | __ \\  (  |  |  _ \\
\\___| \\___/ _|\\_| ___/ \\__/  _| ___/
            </div>
                            <div class="con5013-subtitle">Interactive Terminal Interface</div>
                            
                            <div class="con5013-terminal">
                                <div id="con5013-terminal-output" class="con5013-terminal-output">
                                    <div>Con5013 Terminal v1.0.0</div>
                                    <div>Type 'help' for available commands</div>
                                    <div></div>
                                </div>
                                <div class="con5013-terminal-input">
                                    <span class="con5013-terminal-prompt">con5013@flask:~$</span>
                                    <textarea id="con5013-terminal-command" class="con5013-terminal-command" 
                                              placeholder="Enter command..." rows="1"></textarea>
                                </div>
                            </div>
                        </div>
                        
                        <!-- API Tab -->
                        <div id="con5013-api-tab" class="con5013-tab-content">
                            <div class="con5013-ascii">
  __|   _ \\   \\ |  __|    \\ _ | __ /
 (     (   | .  | __ \\  (  |  |  _ \\
\\___| \\___/ _|\\_| ___/ \\__/  _| ___/
            </div>
                            <div class="con5013-subtitle">API Endpoint Discovery & Testing</div>
                            
                            <div class="con5013-api">
                                <div class="con5013-api-controls">
                                    <button class="con5013-btn" onclick="con5013.discoverEndpoints()">Discover</button>
                                    <button class="con5013-btn" onclick="con5013.testAllEndpoints()">Test All</button>
                                    <button class="con5013-btn secondary" onclick="con5013.exportApiResults()">Export</button>
                                    <div class="con5013-dropdown" id="con5013-api-filter-dropdown">
                                        <button class="con5013-btn secondary" id="con5013-api-filter-toggle" type="button">
                                            Filters <span class="con5013-filter-summary" id="con5013-api-filter-summary">Active</span>
                                        </button>
                                        <div class="con5013-dropdown-menu" id="con5013-api-filter-menu">
                                            <button class="con5013-dropdown-item active" data-filter="active">
                                                <span class="con5013-dropdown-check">✔</span>
                                                Active
                                            </button>
                                            <button class="con5013-dropdown-item" data-filter="excluded">
                                                <span class="con5013-dropdown-check">✔</span>
                                                Excluded
                                            </button>
                                            <button class="con5013-dropdown-item" data-filter="system">
                                                <span class="con5013-dropdown-check">✔</span>
                                                System
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                
                                <div id="con5013-api-stats" class="con5013-api-stats">
                                    <div class="con5013-stat">
                                        <div class="con5013-stat-value" id="total-endpoints">0</div>
                                        <div class="con5013-stat-label">Total Endpoints</div>
                                    </div>
                                    <div class="con5013-stat">
                                        <div class="con5013-stat-value" id="working-endpoints">0</div>
                                        <div class="con5013-stat-label">Working</div>
                                    </div>
                                    <div class="con5013-stat">
                                        <div class="con5013-stat-value" id="failed-endpoints">0</div>
                                        <div class="con5013-stat-label">Failed</div>
                                    </div>
                                    <div class="con5013-stat">
                                        <div class="con5013-stat-value" id="avg-response-time">0ms</div>
                                        <div class="con5013-stat-label">Avg Response</div>
                                    </div>
                                </div>
                                
                                <div id="con5013-endpoints" class="con5013-endpoints">
                                    <div style="padding: 40px; text-align: center; color: #9ca3af;">
                                        Click "Discover" to scan API endpoints
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- System Tab -->
                        <div id="con5013-system-tab" class="con5013-tab-content">
                            <div class="con5013-ascii">
  __|   _ \\   \\ |  __|    \\ _ | __ /
 (     (   | .  | __ \\  (  |  |  _ \\
\\___| \\___/ _|\\_| ___/ \\__/  _| ___/
            </div>
                            <div class="con5013-subtitle">System Performance & Monitoring</div>

                            <div id="con5013-system" class="con5013-system">
                                <div class="con5013-system-card" id="con5013-system-info-card">
                                    <div class="con5013-system-title">System Info</div>
                                    <div class="con5013-metric">
                                        <span class="con5013-metric-label">Platform</span>
                                        <span class="con5013-metric-value" id="system-platform">Loading...</span>
                                    </div>
                                    <div class="con5013-metric">
                                        <span class="con5013-metric-label">Python Version</span>
                                        <span class="con5013-metric-value" id="python-version">Loading...</span>
                                    </div>
                                    <div class="con5013-metric">
                                        <span class="con5013-metric-label">Uptime</span>
                                        <span class="con5013-metric-value" id="system-uptime">Loading...</span>
                                    </div>
                                    <div class="con5013-metric">
                                        <span class="con5013-metric-label">Hostname</span>
                                        <span class="con5013-metric-value" id="system-hostname">Loading...</span>
                                    </div>
                                    <div class="con5013-metric">
                                        <span class="con5013-metric-label">Architecture</span>
                                        <span class="con5013-metric-value" id="system-arch">Loading...</span>
                                    </div>
                                </div>

                                <div class="con5013-system-card" id="con5013-cpu-card">
                                    <div class="con5013-system-title">CPU</div>
                                    <div class="con5013-metric has-progress">
                                        <span class="con5013-metric-label">Usage</span>
                                        <span class="con5013-metric-value" id="cpu-usage">Loading...</span>
                                    </div>
                                    <div class="con5013-progress after-metric">
                                        <div class="con5013-progress-bar" id="cpu-progress" style="width: 0%"></div>
                                    </div>
                                </div>

                                <div class="con5013-system-card" id="con5013-memory-card">
                                    <div class="con5013-system-title">Memory</div>
                                    <div class="con5013-metric has-progress">
                                        <span class="con5013-metric-label">Usage</span>
                                        <span class="con5013-metric-value" id="memory-usage">Loading...</span>
                                    </div>
                                    <div class="con5013-progress after-metric">
                                        <div class="con5013-progress-bar" id="memory-progress" style="width: 0%"></div>
                                    </div>
                                </div>

                                <div class="con5013-system-card" id="con5013-disk-card">
                                    <div class="con5013-system-title">Storage</div>
                                    <div class="con5013-metric has-progress">
                                        <span class="con5013-metric-label">Disk Usage</span>
                                        <span class="con5013-metric-value" id="disk-usage">Loading...</span>
                                    </div>
                                    <div class="con5013-progress after-metric">
                                        <div class="con5013-progress-bar" id="disk-progress" style="width: 0%"></div>
                                    </div>
                                    <div class="con5013-divider"></div>
                                    <div class="con5013-metric">
                                        <span class="con5013-metric-label">Free Space</span>
                                        <span class="con5013-metric-value" id="disk-free">Loading...</span>
                                    </div>
                                </div>

                                <div class="con5013-system-card" id="con5013-network-card">
                                    <div class="con5013-system-title">Network</div>
                                    <div class="con5013-metric">
                                        <span class="con5013-metric-label">Download</span>
                                        <span class="con5013-metric-value" id="net-down">0 B/s</span>
                                    </div>
                                    <div class="con5013-metric">
                                        <span class="con5013-metric-label">Upload</span>
                                        <span class="con5013-metric-value" id="net-up">0 B/s</span>
                                    </div>
                                    <div class="con5013-metric">
                                        <span class="con5013-metric-label">Connections</span>
                                        <span class="con5013-metric-value" id="net-conns">0</span>
                                    </div>
                                    <div class="con5013-metric">
                                        <span class="con5013-metric-label">Totals</span>
                                        <span class="con5013-metric-value" id="net-totals">0 / 0</span>
                                    </div>
                                </div>

                                <div class="con5013-system-card" id="con5013-gpu-card">
                                    <div class="con5013-system-title">GPU</div>
                                    <div id="con5013-gpu-list" class="con5013-gpu-list">
                                        <div class="con5013-metric">
                                            <span class="con5013-metric-label">GPUs</span>
                                            <span class="con5013-metric-value" id="gpu-count">Detecting...</span>
                                        </div>
                                    </div>
                                </div>

                                <div class="con5013-system-card" id="con5013-application-card">
                                    <div class="con5013-system-title">Application</div>
                                    <div class="con5013-metric">
                                        <span class="con5013-metric-label">Routes</span>
                                        <span class="con5013-metric-value" id="app-routes">Loading...</span>
                                    </div>
                                    <div class="con5013-metric">
                                        <span class="con5013-metric-label">Extensions</span>
                                        <span class="con5013-metric-value" id="app-extensions">Loading...</span>
                                    </div>
                                    <div class="con5013-metric">
                                        <span class="con5013-metric-label">Debug Mode</span>
                                        <span class="con5013-metric-value" id="app-debug">Loading...</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add to body
        document.body.insertAdjacentHTML('beforeend', consoleHTML);
    }

    createFloatingButton() {
        // Respect opt-out via meta or option
        const metaNoFab = document.querySelector('meta[name="con5013-no-fab"][content="1"]');
        if (metaNoFab || !this.options.autoFloatingButton) return;

        // If a custom Con5013 button exists, wire it and optionally hide FAB
        const customBtn = document.querySelector(this.options.customButtonSelector);
        if (customBtn) {
            try { customBtn.addEventListener('click', (e) => { e.preventDefault(); this.toggle(); }); } catch (_) {}
            if (this.options.hideFabIfCustomButton) return; // do not render default FAB
        }

        if (document.getElementById('con5013-fab')) return; // already created

        const fab = document.createElement('button');
        fab.id = 'con5013-fab';
        fab.type = 'button';
        fab.className = `con5013-fab ${this.options.floatingButtonPosition}`;
        fab.setAttribute('aria-label', 'Open Con5013 Console');
        fab.innerHTML = `<span class="con5013-fab-ring"></span>
            <span class="con5013-fab-icon" aria-hidden="true">
                <svg id="con5013-b-icon" width="36" height="18" viewBox="0 0 240 120" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="CON5013 monogram icon">
                  <rect x="8" y="8" rx="16" ry="16" width="224" height="104" fill="#0d1520" stroke="#1f2a37" stroke-width="2" />
                  <path d="M56 60 l36 -24" stroke="#31d0aa" stroke-width="8" stroke-linecap="round" fill="none" />
                  <path d="M56 60 l36 24" stroke="#31d0aa" stroke-width="8" stroke-linecap="round" fill="none" />
                  <path d="M188 36 l-40 48" stroke="#7aa2f7" stroke-width="8" stroke-linecap="round" fill="none" />
                  <path d="M112 60 h16" stroke="#cbd5e1" stroke-width="8" stroke-linecap="round" />
                </svg>
            </span>`;
        fab.addEventListener('click', () => this.toggle());
        // Prevent unstyled flash until CSS is applied
        fab.style.display = 'none';
        document.body.appendChild(fab);

        // Initial visibility sync
        this.updateFabVisibility();
    }

    updateFabVisibility() {
        const fab = document.getElementById('con5013-fab');
        if (!fab) return;
        if (this.options.hideFabWhenOpen && this.isOpen) {
            fab.classList.add('hidden');
        } else {
            fab.classList.remove('hidden');
        }
    }
    
    bindEvents() {
        // Tab switching
        document.querySelectorAll('.con5013-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
        
        // Terminal input
        const terminalInput = document.getElementById('con5013-terminal-command');
        if (terminalInput) {
            const autoResize = () => {
                terminalInput.style.height = 'auto';
                const maxPx = Math.round(window.innerHeight * 0.4);
                const cs = window.getComputedStyle(terminalInput);
                const lh = parseFloat(cs.lineHeight) || (parseFloat(cs.fontSize) * 1.4) || 18;
                const pad = (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0);
                const minPx = Math.ceil(lh + pad);
                const desired = Math.max(minPx, Math.min(terminalInput.scrollHeight, maxPx));
                terminalInput.style.height = desired + 'px';
                this.updateTerminalInputMetrics();
            };
            terminalInput.addEventListener('input', autoResize);
            // Initialize height
            autoResize();
            terminalInput.addEventListener('keydown', (e) => {
                // Shift+Enter inserts a newline
                if (e.key === 'Enter' && e.shiftKey) {
                    // allow default newline in textarea
                    return;
                }
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.executeTerminalCommand(e.target.value);
                    e.target.value = '';
                    autoResize();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    this.navigateTerminalHistory(-1);
                    autoResize();
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    this.navigateTerminalHistory(1);
                    autoResize();
                }
            });
        }

        window.addEventListener('resize', () => this.updateTerminalInputMetrics());
        
        // Logs scroll pause/resume
        const logsContainer = document.getElementById('con5013-logs');
        if (logsContainer) {
            logsContainer.addEventListener('scroll', () => this.onLogsScroll());
        }
        const logsResume = document.getElementById('con5013-logs-resume');
        if (logsResume) {
            logsResume.addEventListener('click', (event) => {
                event.preventDefault();
                this.resumeLogAutoScroll(true);
            });
        }
        
        // Close on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
        
        // Close on overlay click
        document.getElementById('con5013-overlay').addEventListener('click', (e) => {
            if (e.target.id === 'con5013-overlay') {
                this.close();
            }
        });

        const apiFilterDropdown = document.getElementById('con5013-api-filter-dropdown');
        const apiFilterToggle = document.getElementById('con5013-api-filter-toggle');
        const apiFilterMenu = document.getElementById('con5013-api-filter-menu');
        const apiFilterSummary = document.getElementById('con5013-api-filter-summary');
        this.apiFilterElements = { dropdown: apiFilterDropdown, toggle: apiFilterToggle, menu: apiFilterMenu, summary: apiFilterSummary };

        if (apiFilterToggle && apiFilterDropdown) {
            apiFilterToggle.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                apiFilterDropdown.classList.toggle('open');
            });
        }
        if (apiFilterMenu && apiFilterDropdown) {
            apiFilterMenu.querySelectorAll('[data-filter]').forEach(item => {
                item.addEventListener('click', (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    const filter = item.getAttribute('data-filter');
                    this.toggleApiFilter(filter);
                });
            });
        }
        document.addEventListener('click', (event) => {
            if (apiFilterDropdown && !apiFilterDropdown.contains(event.target)) {
                apiFilterDropdown.classList.remove('open');
            }
        });
    }
    
    setupHotkey() {
        const rawHotkey = (this.options.hotkey || 'Alt+C').trim();
        if (!rawHotkey) return;

        const segments = rawHotkey.split('+').map(part => part.trim()).filter(Boolean);
        if (segments.length === 0) return;

        const keySegment = segments.pop();
        const modifiers = segments.map(s => s.toLowerCase());
        const key = (keySegment || '').toLowerCase();
        const requiresAlt = modifiers.includes('alt');
        const requiresShift = modifiers.includes('shift');
        const requiresCtrl = modifiers.includes('ctrl') || modifiers.includes('control');
        const requiresMeta = modifiers.includes('meta') || modifiers.includes('cmd') || modifiers.includes('command') || modifiers.includes('super');

        document.addEventListener('keydown', (event) => {
            const eventKey = (event.key || '').toLowerCase();
            if (key && eventKey !== key) return;
            if (requiresAlt !== !!event.altKey) return;
            if (requiresShift !== !!event.shiftKey) return;
            if (requiresCtrl !== !!event.ctrlKey) return;
            if (requiresMeta !== !!event.metaKey) return;
            // Prevent triggering when extra modifiers pressed
            if (!requiresAlt && event.altKey) return;
            if (!requiresShift && event.shiftKey) return;
            if (!requiresCtrl && event.ctrlKey) return;
            if (!requiresMeta && event.metaKey) return;

            event.preventDefault();
            this.toggle();
        });
    }
    
    async loadInitialData() {
        try {
            const res = await fetch(`${this.options.baseUrl}/api/info`);
            const payload = await res.json();
            if (payload && payload.info && payload.info.features) {
                this.features = {
                    ...this.features,
                    ...payload.info.features,
                };
                this.updateSystemMetrics(payload.info.features.system_monitor_metrics);
            }
            if (payload && payload.info && payload.info.default_log_source) {
                this.defaultLogSource = payload.info.default_log_source;
            }
            this.setConnectivity(true);
        } catch (e) {
            // ignore; keep defaults (all enabled)
            this.setConnectivity(false);
        }
        this.applyFeatureToggles();
        // Load per-feature data
        if (this.features.logs) {
            await this.loadLogSources();
            await this.refreshLogs();
        }
        if (this.features.system_monitor) {
            await this.refreshSystemStats();
        }
    }

    applyFeatureToggles() {
        const tabAvailability = {
            logs: () => !!this.features.logs,
            terminal: () => !!this.features.terminal,
            api: () => !!this.features.api_scanner,
            system: () => !!this.features.system_monitor,
        };

        const hideTab = (name, enabled) => {
            const tabBtn = document.querySelector(`.con5013-tab[data-tab="${name}"]`);
            const panel = document.getElementById(`con5013-${name}-tab`);
            if (!tabBtn || !panel) return;

            const shouldHide = !enabled;
            tabBtn.classList.toggle('con5013-hidden', shouldHide);
            panel.classList.toggle('con5013-hidden', shouldHide);
            if (shouldHide) {
                tabBtn.classList.remove('active');
                panel.classList.remove('active');
                tabBtn.setAttribute('aria-hidden', 'true');
                panel.setAttribute('aria-hidden', 'true');
                panel.setAttribute('hidden', '');
                if (this.currentTab === name) {
                    const order = ['logs', 'terminal', 'api', 'system'];
                    const nextTab = order.find((tab) => tab !== name && tabAvailability[tab]?.());
                    if (nextTab) {
                        this.switchTab(nextTab);
                    } else {
                        this.currentTab = null;
                    }
                }
            } else {
                tabBtn.removeAttribute('aria-hidden');
                panel.removeAttribute('aria-hidden');
                panel.removeAttribute('hidden');
                if (!this.currentTab || !tabAvailability[this.currentTab]?.()) {
                    this.switchTab(name);
                }
            }
        };

        hideTab('logs', !!this.features.logs);
        hideTab('terminal', !!this.features.terminal);
        hideTab('api', !!this.features.api_scanner);
        hideTab('system', !!this.features.system_monitor);

        this.updateLogControls();
        this.applySystemMetricToggles();
    }

    updateLogControls() {
        const clearBtn = document.querySelector('[data-con5013-clear-logs]');
        if (!clearBtn) return;

        const allowed = !!this.features.logs && !!this.features.allow_log_clear;
        clearBtn.classList.toggle('con5013-hidden', !allowed);
        if (allowed) {
            clearBtn.removeAttribute('disabled');
            clearBtn.removeAttribute('aria-hidden');
            clearBtn.removeAttribute('hidden');
        } else {
            clearBtn.setAttribute('disabled', 'disabled');
            clearBtn.setAttribute('aria-hidden', 'true');
            clearBtn.setAttribute('hidden', '');
        }
    }

    updateSystemMetrics(settings = {}) {
        const normalized = { ...this.systemMetrics };
        Object.entries(settings || {}).forEach(([key, value]) => {
            if (value === undefined) return;
            normalized[key] = value !== false;
        });
        this.systemMetrics = normalized;
    }

    isMetricEnabled(name) {
        return !this.systemMetrics || this.systemMetrics[name] !== false;
    }

    applySystemMetricToggles() {
        const selectors = {
            system_info: '#con5013-system-info-card',
            application: '#con5013-application-card',
            cpu: '#con5013-cpu-card',
            memory: '#con5013-memory-card',
            disk: '#con5013-disk-card',
            network: '#con5013-network-card',
            gpu: '#con5013-gpu-card',
        };
        Object.entries(selectors).forEach(([metric, selector]) => {
            const card = document.querySelector(selector);
            if (!card) return;
            const shouldHide = !this.isMetricEnabled(metric);
            card.classList.toggle('con5013-hidden', shouldHide);
            card.setAttribute('aria-hidden', shouldHide ? 'true' : 'false');
        });
    }
    
    startPeriodicUpdates() {
        setInterval(() => {
            if (this.isOpen) {
                if (this.currentTab === 'logs' && this.features.logs) {
                    this.refreshLogs();
                } else if (this.currentTab === 'system' && this.features.system_monitor) {
                    this.refreshSystemStats();
                }
            }
        }, this.options.updateInterval);
    }

    async waitForElement(selector, timeout = 2000, interval = 50) {
        const deadline = Date.now() + Math.max(0, timeout);
        let element = document.querySelector(selector);
        while (!element && Date.now() < deadline) {
            await new Promise(resolve => setTimeout(resolve, interval));
            element = document.querySelector(selector);
        }
        return element || null;
    }

    // Public API
    open() {
        this.isOpen = true;
        const overlay = document.getElementById('con5013-overlay');
        overlay.classList.add('open');
        this.updateFabVisibility();
        
        // Focus terminal input if on terminal tab
        if (this.currentTab === 'terminal') {
            setTimeout(() => {
                document.getElementById('con5013-terminal-command')?.focus();
            }, 300);
        }
    }
    
    close() {
        this.isOpen = false;
        const overlay = document.getElementById('con5013-overlay');
        overlay.classList.remove('open');
        this.updateFabVisibility();
    }
    
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    async openConsole(options = {}) {
        const opts = typeof options === 'string' ? { tab: options } : { ...options };
        const tabCandidate = typeof opts.tab === 'string' ? opts.tab.trim().toLowerCase() : '';
        const shouldRunCommand = typeof opts.command === 'string' && opts.command.trim() !== '';

        this.open();

        let targetTab = CON5013_VALID_TABS.includes(tabCandidate) ? tabCandidate : this.currentTab || 'logs';
        if (shouldRunCommand && this.features.terminal) {
            targetTab = 'terminal';
        }

        if (!this.features.terminal && targetTab === 'terminal') {
            console.warn('Con5013: terminal tab unavailable; staying on current tab');
            targetTab = this.currentTab || 'logs';
        }

        if (targetTab && targetTab !== this.currentTab) {
            const tabButton = document.querySelector(`[data-tab="${targetTab}"]`);
            const tabPanel = document.getElementById(`con5013-${targetTab}-tab`);
            if (tabButton && tabPanel) {
                this.switchTab(targetTab);
            } else {
                console.warn(`Con5013: requested tab "${targetTab}" is not available`);
                targetTab = this.currentTab || 'logs';
            }
        }

        if (targetTab === 'terminal' && !shouldRunCommand && opts.focusCommandInput !== false) {
            setTimeout(() => {
                document.getElementById('con5013-terminal-command')?.focus();
            }, 100);
        }

        if (!shouldRunCommand) {
            return this;
        }

        if (!this.features.terminal) {
            console.warn('Con5013: terminal feature disabled; cannot run command');
            return this;
        }

        const previewDelay = Number.isFinite(opts.previewDelay) ? Number(opts.previewDelay) : 0;
        const clearDelay = Number.isFinite(opts.clearDelay) ? Number(opts.clearDelay) : 200;
        const inputTimeout = Number.isFinite(opts.inputTimeout) ? Number(opts.inputTimeout) : 4000;

        const input = await this.waitForElement('#con5013-terminal-command', inputTimeout);
        if (!input) {
            console.warn('Con5013: terminal input unavailable; command skipped');
            return this;
        }

        const command = opts.command.trim();
        input.value = command;
        input.dispatchEvent(new Event('input', { bubbles: true }));

        if (previewDelay > 0) {
            await new Promise(resolve => setTimeout(resolve, previewDelay));
        }

        await this.executeTerminalCommand(command);

        if (clearDelay > 0) {
            await new Promise(resolve => setTimeout(resolve, clearDelay));
        }

        input.value = '';
        input.dispatchEvent(new Event('input', { bubbles: true }));

        return this;
    }

    switchTab(tabName) {
        // Update tab buttons
        const isTabAvailable = (name) => {
            const btn = document.querySelector(`.con5013-tab[data-tab="${name}"]`);
            const panel = document.getElementById(`con5013-${name}-tab`);
            if (!btn || !panel) return false;
            return !btn.classList.contains('con5013-hidden') && !panel.classList.contains('con5013-hidden');
        };

        let targetTab = tabName;
        if (!isTabAvailable(targetTab)) {
            const order = ['logs', 'terminal', 'api', 'system'];
            targetTab = order.find((tab) => isTabAvailable(tab)) || null;
            if (!targetTab) {
                this.currentTab = null;
                return;
            }
        }

        document.querySelectorAll('.con5013-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${targetTab}"]`)?.classList.add('active');

        document.querySelectorAll('.con5013-tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`con5013-${targetTab}-tab`)?.classList.add('active');

        this.currentTab = targetTab;

        // Load tab-specific data
        if (targetTab === 'terminal') {
            setTimeout(() => {
                document.getElementById('con5013-terminal-command')?.focus();
                this.updateTerminalInputMetrics();
            }, 100);
        } else if (targetTab === 'system') {
            this.refreshSystemStats();
        }
    }
    
    // Logs functionality
    async refreshLogs() {
        try {
            const params = new URLSearchParams();
            if (this.currentLogSource) params.set('source', this.currentLogSource);
            if (this.currentLogLevel) params.set('level', this.currentLogLevel);
            const response = await fetch(`${this.options.baseUrl}/api/logs?${params.toString()}`);
            const payload = await response.json();
            const logs = payload && payload.logs ? payload.logs : (Array.isArray(payload) ? payload : []);
            this.displayLogs(logs);
            this.setConnectivity(true);
        } catch (error) {
            console.error('Error refreshing logs:', error);
            this.setConnectivity(false);
        }
    }
    
    displayLogs(logs) {
        const logsContainer = document.getElementById('con5013-logs');
        if (!logsContainer) return;
        
        const list = Array.isArray(logs) ? [...logs] : [];
        if (this.currentLogSort === 'asc') list.reverse();
        const logsHTML = list.map(log => {
            const timestamp = new Date(log.timestamp * 1000).toLocaleTimeString();
            return `
                <div class="con5013-log-entry">
                    <span class="con5013-log-timestamp">${timestamp}</span>
                    <span class="con5013-log-level ${log.level}">${log.level}</span>
                    <span class="con5013-log-message">${this.escapeHtml(log.message)}</span>
                </div>
            `;
        }).join('');
        
        const previousScrollTop = logsContainer.scrollTop;
        const previousScrollHeight = logsContainer.scrollHeight;

        logsContainer.innerHTML = logsHTML;

        if (!this.logAutoScrollPaused) {
            this.autoScrollLogs();
        } else {
            const newScrollHeight = logsContainer.scrollHeight;
            if (this.currentLogSort === 'desc') {
                const delta = newScrollHeight - previousScrollHeight;
                logsContainer.scrollTop = Math.max(0, previousScrollTop + delta);
            } else {
                const maxScroll = Math.max(0, newScrollHeight - logsContainer.clientHeight);
                logsContainer.scrollTop = Math.min(previousScrollTop, maxScroll);
            }
        }
    }

    autoScrollLogs() {
        const logsContainer = document.getElementById('con5013-logs');
        if (!logsContainer) return;

        if (this.currentLogSort === 'asc') {
            logsContainer.scrollTop = logsContainer.scrollHeight;
        } else {
            logsContainer.scrollTop = 0;
        }
    }

    onLogsScroll() {
        const logsContainer = document.getElementById('con5013-logs');
        if (!logsContainer) return;

        const resumeThreshold = 10;
        const atTop = logsContainer.scrollTop <= resumeThreshold;
        const atBottom = (logsContainer.scrollHeight - logsContainer.clientHeight - logsContainer.scrollTop) <= resumeThreshold;
        // Determine if the viewport is anchored to the edge we auto-scroll toward.
        const alignedWithLiveEdge = this.currentLogSort === 'asc' ? atBottom : atTop;

        if (alignedWithLiveEdge) {
            if (this.logAutoScrollPaused) {
                this.resumeLogAutoScroll(false);
            }
        } else if (!this.logAutoScrollPaused) {
            this.pauseLogAutoScroll();
        }
    }

    pauseLogAutoScroll() {
        if (this.logAutoScrollPaused) return;
        this.logAutoScrollPaused = true;
        this.toggleLogAutoScrollIndicator(true);
    }

    resumeLogAutoScroll(snap = false) {
        const wasPaused = this.logAutoScrollPaused;
        this.logAutoScrollPaused = false;
        this.toggleLogAutoScrollIndicator(false);
        if (snap || wasPaused) {
            this.autoScrollLogs();
        }
    }

    toggleLogAutoScrollIndicator(show) {
        const indicator = document.getElementById('con5013-logs-autoscroll-indicator');
        if (!indicator) return;
        indicator.style.display = show ? 'flex' : 'none';
    }

    async clearLogs() {
        if (!this.features.allow_log_clear || !this.features.logs) {
            console.warn('Con5013: log clearing is disabled by configuration');
            return;
        }
        try {
            const sourceSelect = document.getElementById('con5013-log-source');
            const source = sourceSelect?.value || this.currentLogSource || 'app';
            await fetch(`${this.options.baseUrl}/api/logs/clear`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source })
            });
            this.refreshLogs();
        } catch (e) {
            console.error('Failed to clear logs', e);
        }
    }
    
    exportLogs() {
        try {
            const rows = document.querySelectorAll('#con5013-logs .con5013-log-entry');
            const data = Array.from(rows).map(r => r.textContent.trim());
            const blob = new Blob([data.join('\n')], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const src = this.currentLogSource || 'logs';
            a.download = `con5013_${src}_logs.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error('Export failed', e);
        }
    }
    
    // Terminal functionality
    async executeTerminalCommand(command) {
        if (!command.trim()) return;
        
        // Add to history
        this.terminalHistory.push(command);
        this.terminalHistoryIndex = this.terminalHistory.length;
        
        // Display command in output
        this.addTerminalOutput(`con5013@flask:~$ ${command}`, 'command');
        
        try {
            const response = await fetch(`${this.options.baseUrl}/api/terminal/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ command })
            });
            
            const payload = await response.json();
            const result = payload && payload.result ? payload.result : payload;
            this.addTerminalOutput(result.output || JSON.stringify(result), result.type || 'text');
            this.setConnectivity(true);
        } catch (error) {
            this.addTerminalOutput(`Error: ${error.message}`, 'error');
            this.setConnectivity(false);
        }
        // Reset input height after execution
        const inputEl = document.getElementById('con5013-terminal-command');
        if (inputEl) {
            inputEl.style.height = 'auto';
            this.updateTerminalInputMetrics();
        }
    }

    addTerminalOutput(text, type = 'text') {
        const output = document.getElementById('con5013-terminal-output');
        if (!output) return;

        // Handle clear type
        if (type === 'clear') {
            output.innerHTML = '';
            return;
        }

        // Command echo styling
        if (type === 'command') {
            const div = document.createElement('div');
            div.textContent = text;
            div.style.color = '#10b981';
            div.style.fontWeight = 'bold';
            output.appendChild(div);
            output.scrollTop = output.scrollHeight;
            return;
        }

        // Pretty formatting for common content types
        const block = document.createElement('div');
        block.className = 'con5013-term-block';

        let detected = this.detectContentFormat(text);
        let pretty = this.formatContent(text, detected);

        // Header label
        const label = document.createElement('div');
        label.className = 'con5013-code-label';
        label.textContent = detected.toUpperCase();
        block.appendChild(label);

        const pre = document.createElement('pre');
        pre.className = `con5013-code con5013-lang-${detected}`;
        pre.textContent = pretty; // keep escaped for safety
        block.appendChild(pre);

        if (type === 'error') {
            block.style.borderColor = 'var(--con5013-error)';
        }

        output.appendChild(block);
        output.scrollTop = output.scrollHeight;
    }

    updateTerminalInputMetrics() {
        const containers = document.querySelectorAll('.con5013-terminal');
        containers.forEach((container) => {
            const inputWrapper = container.querySelector('.con5013-terminal-input');
            if (!inputWrapper || inputWrapper.offsetParent === null) return;
            const styles = window.getComputedStyle(inputWrapper);
            const marginTop = parseFloat(styles.marginTop) || 0;
            const marginBottom = parseFloat(styles.marginBottom) || 0;
            const total = inputWrapper.offsetHeight + marginTop + marginBottom;
            container.style.setProperty('--con5013-terminal-input-height', `${Math.ceil(total)}px`);
        });
    }

    // Determine content format using simple hints
    detectContentFormat(text) {
        if (!text || typeof text !== 'string') return 'text';

        // Heuristic for our HTTP helper output
        if (text.startsWith('HTTP ') && text.includes('Headers:')) {
            const ctMatch = text.match(/content-type=([^\n\r]+)/i);
            const ct = (ctMatch && ctMatch[1] || '').toLowerCase();
            if (ct.includes('json')) return 'json';
            if (ct.includes('html')) return 'html';
            if (ct.includes('css')) return 'css';
            if (ct.includes('javascript') || ct.includes('ecmascript')) return 'js';
            if (ct.includes('text/plain')) return 'text';
        }

        // Raw JSON detection
        const trimmed = text.trim();
        if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
            try { JSON.parse(trimmed); return 'json'; } catch (_) {}
        }
        // HTML hint
        if (trimmed.startsWith('<') && trimmed.includes('>')) return 'html';
        // CSS hint
        if (/\{\s*[^}]*:\s*[^}]*\}/m.test(trimmed)) return 'css';
        // JS/PY hints (very rough)
        if (/\bfunction\b|=>|console\./.test(trimmed)) return 'js';
        if (/\bdef\b|\bimport\b|\bclass\b/.test(trimmed)) return 'py';
        return 'text';
    }

    // Format content based on detected type
    formatContent(text, kind) {
        if (!text || typeof text !== 'string') return String(text || '');

        // If HTTP helper output, split headers/body so we pretty-print only the body
        let headers = '';
        let body = text;
        if (text.startsWith('HTTP ') && text.includes('\n\n')) {
            const idx = text.indexOf('\n\n');
            headers = text.substring(0, idx);
            body = text.substring(idx + 2);
            // keep headers on top of pretty body
        }

        try {
            switch (kind) {
                case 'json': {
                    const pretty = JSON.stringify(JSON.parse(body.trim()), null, 2);
                    return headers ? `${headers}\n\n${pretty}` : pretty;
                }
                case 'html': {
                    const formatted = body.replace(/>\s*</g, '>$NEWLINE<$').replace(/\$NEWLINE\$/g, '$NEWLINE$');
                    const withBreaks = formatted.split('$NEWLINE$').join('\n');
                    return headers ? `${headers}\n\n${withBreaks}` : withBreaks;
                }
                case 'css': {
                    let s = body
                        .replace(/;/g, ';\n')
                        .replace(/\{/g, '{\n')
                        .replace(/\}/g, '\n}\n');
                    return headers ? `${headers}\n\n${s}` : s;
                }
                case 'js': {
                    let s = body.replace(/;\s*/g, ';\n').replace(/\{\s*/g, '{\n').replace(/\}\s*/g, '\n}\n');
                    return headers ? `${headers}\n\n${s}` : s;
                }
                case 'py': {
                    // For Python, keep as-is but ensure lines are visible
                    return headers ? `${headers}\n\n${body}` : body;
                }
                default:
                    return text;
            }
        } catch (_) {
            return text;
        }
    }
    
    navigateTerminalHistory(direction) {
        const input = document.getElementById('con5013-terminal-command');
        if (!input || this.terminalHistory.length === 0) return;
        
        this.terminalHistoryIndex += direction;
        
        if (this.terminalHistoryIndex < 0) {
            this.terminalHistoryIndex = 0;
        } else if (this.terminalHistoryIndex >= this.terminalHistory.length) {
            this.terminalHistoryIndex = this.terminalHistory.length;
            input.value = '';
            return;
        }
        
        input.value = this.terminalHistory[this.terminalHistoryIndex] || '';
    }

    // API functionality
    isSystemEndpoint(rule, endpointName) {
        const cleanRule = rule || '';
        const name = endpointName || '';
        const prefix = this.consolePrefix;
        if (prefix && prefix !== '/' && cleanRule.startsWith(prefix)) return true;
        if (cleanRule.startsWith('/con5013/')) return true;
        if (name.includes('con5013')) return true;
        return false;
    }

    categorizeEndpoint(endpoint) {
        if (endpoint && endpoint.protected) return 'excluded';
        const rule = endpoint?.rule || endpoint?.url || '';
        const name = endpoint?.endpoint || '';
        if (this.isSystemEndpoint(rule, name)) return 'system';
        return 'active';
    }

    updateApiFilterSummary() {
        const labels = { active: 'Active', excluded: 'Excluded', system: 'System' };
        const menu = this.apiFilterElements?.menu;
        const summary = this.apiFilterElements?.summary;
        if (menu) {
            menu.querySelectorAll('[data-filter]').forEach(item => {
                const key = item.getAttribute('data-filter');
                if (!key) return;
                if (this.apiFilters[key]) item.classList.add('active');
                else item.classList.remove('active');
            });
        }
        if (summary) {
            const enabled = Object.entries(this.apiFilters)
                .filter(([, enabled]) => enabled)
                .map(([key]) => labels[key] || key);
            summary.textContent = enabled.length ? enabled.join(', ') : 'None';
        }
    }

    applyApiFilters() {
        const endpoints = Array.isArray(this.endpoints) ? this.endpoints : [];
        const filtered = endpoints.filter(ep => this.apiFilters[(ep && ep.category) || this.categorizeEndpoint(ep)]);
        this.apiVisibleEndpoints = filtered;
        this.displayEndpoints(filtered);
        this.reapplyApiResults();
        this.updateApiStats();
        this.updateApiFilterSummary();
    }

    reapplyApiResults() {
        if (!Array.isArray(this.apiTestResults)) return;
        this.apiTestResults.forEach(result => {
            const id = `status-${(result.endpoint || '').replace(/[^a-zA-Z0-9]/g, '')}`;
            const indicator = document.getElementById(id);
            if (indicator) {
                indicator.className = `con5013-status-indicator ${result.status === 'success' ? 'success' : 'error'}`;
            }
        });
    }

    toggleApiFilter(filter) {
        if (!filter || !(filter in this.apiFilters)) return;
        this.apiFilters[filter] = !this.apiFilters[filter];
        this.updateApiFilterSummary();
        if (filter === 'system') {
            this.discoverEndpoints();
        } else {
            this.applyApiFilters();
        }
        if (this.apiFilterElements && this.apiFilterElements.dropdown) {
            this.apiFilterElements.dropdown.classList.remove('open');
        }
    }

    async discoverEndpoints() {
        try {
            const includeSystem = !!this.apiFilters.system;
            const response = await fetch(`${this.options.baseUrl}/api/scanner/discover?include_con5013=${includeSystem ? 'true' : 'false'}`);
            const payload = await response.json();
            const endpoints = payload && payload.endpoints ? payload.endpoints : [];
            this.endpoints = endpoints.map(ep => ({ ...ep, category: this.categorizeEndpoint(ep) }));
            this.apiTestResults = [];
            this.apiSummary = null;
            this.applyApiFilters();
            this.setConnectivity(true);
        } catch (error) {
            console.error('Error discovering endpoints:', error);
            this.setConnectivity(false);
        }
    }
    
    displayEndpoints(endpoints) {
        const container = document.getElementById('con5013-endpoints');
        if (!container) return;

        if (endpoints.length === 0) {
            container.innerHTML = '<div style="padding: 40px; text-align: center; color: #9ca3af;">No endpoints found</div>';
            return;
        }

        const endpointsHTML = endpoints.map(endpoint => {
            const category = endpoint.category || this.categorizeEndpoint(endpoint);
            const defaultMethod = this.getEndpointDefaultMethod(endpoint.methods);
            const sanitizedPath = (endpoint.sample_path || endpoint.rule).replace(/'/g, "\'");
            const termBtn = this.features.terminal
                ? `<button class="con5013-btn secondary" onclick="con5013.runEndpointInTerminal('${sanitizedPath}', '${defaultMethod}')">Run in Terminal</button>`
                : '';
            const badge = category === 'system'
                ? '<span class="con5013-badge system">System</span>'
                : (category === 'excluded' ? '<span class="con5013-badge excluded">Excluded</span>' : '');
            const testControls = endpoint.protected
                ? '<span class="con5013-endpoint-note">Tests disabled</span>'
                : `<button class="con5013-btn" onclick="con5013.testEndpoint('${sanitizedPath}', '${defaultMethod}')">Test</button>${termBtn ? ` ${termBtn}` : ''}`;
            return `
            <div class="con5013-endpoint">
                <div class="con5013-endpoint-info">
                    <div class="con5013-endpoint-url">${endpoint.rule}</div>
                    <div class="con5013-endpoint-methods">
                        ${endpoint.methods.map(method => `<span class=\"con5013-method ${method}\">${method}</span>`).join('')}
                    </div>
                </div>
                <div class="con5013-endpoint-status">
                    ${badge}
                    <div class="con5013-status-indicator" id="status-${endpoint.rule.replace(/[^a-zA-Z0-9]/g, '')}"></div>
                    ${testControls}
                </div>
            </div>`;
        }).join('');

        container.innerHTML = endpointsHTML;
    }

    getEndpointDefaultMethod(methods = []) {
        if (!Array.isArray(methods) || methods.length === 0) {
            return 'GET';
        }

        const preferredOrder = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD'];
        for (const pref of preferredOrder) {
            const match = methods.find(method => (method || '').toUpperCase() === pref);
            if (match) {
                return match;
            }
        }

        const fallback = methods.find(method => (method || '').toUpperCase() !== 'OPTIONS');
        return fallback || methods[0];
    }

    async testEndpoint(pathOrUrl, method) {
        const statusIndicator = document.querySelector(`#status-${(pathOrUrl || '').replace(/[^a-zA-Z0-9]/g, '')}`);
        if (statusIndicator) {
            statusIndicator.className = 'con5013-status-indicator testing';
        }
        
        try {
            const response = await fetch(`${this.options.baseUrl}/api/scanner/test`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ endpoint: pathOrUrl, method })
            });
            
            const payload = await response.json();
            const result = payload && payload.result ? payload.result : payload;
            
            if (statusIndicator) {
                statusIndicator.className = `con5013-status-indicator ${result.status === 'success' ? 'success' : 'error'}`;
            }
            this.setConnectivity(true);
        } catch (error) {
            if (statusIndicator) {
                statusIndicator.className = 'con5013-status-indicator error';
            }
            this.setConnectivity(false);
        }
    }
    
    async testAllEndpoints() {
        try {
            const includeSystem = !!this.apiFilters.system;
            const response = await fetch(`${this.options.baseUrl}/api/scanner/test-all?include_con5013=${includeSystem ? 'true' : 'false'}`, { method: 'POST' });
            const payload = await response.json();
            const results = payload && payload.results ? payload.results : payload;
            this.displayTestResults(results);
            this.updateApiStats(results);
            this.setConnectivity(true);
        } catch (error) {
            console.error('Error testing endpoints:', error);
            this.setConnectivity(false);
        }
    }
    
    displayTestResults(results) {
        // Accept either the aggregated results object or just the payload
        const list = Array.isArray(results) ? results : (results && results.results ? results.results : []);
        if (Array.isArray(list)) {
            this.apiTestResults = list;
        }
        this.reapplyApiResults();
    }

    async runEndpointInTerminal(pathOrUrl, method) {
        const cmd = `http ${method} ${pathOrUrl}`;
        await this.openConsole({ tab: 'terminal', command: cmd, previewDelay: 200 });
    }
    
    updateApiStats(results = null) {
        if (results) {
            const list = Array.isArray(results) ? results : (results && results.results ? results.results : []);
            if (Array.isArray(list)) {
                this.apiTestResults = list;
            }
            if (results && !Array.isArray(results)) {
                this.apiSummary = results;
            }
        }

        const totalEl = document.getElementById('total-endpoints');
        const workingEl = document.getElementById('working-endpoints');
        const failedEl = document.getElementById('failed-endpoints');
        const avgEl = document.getElementById('avg-response-time');

        if (totalEl) {
            totalEl.textContent = this.apiVisibleEndpoints.length;
        }

        if (!workingEl || !failedEl || !avgEl) {
            return;
        }

        const visibleRules = new Set((this.apiVisibleEndpoints || []).map(ep => ep.rule));
        const resultsList = Array.isArray(this.apiTestResults) ? this.apiTestResults : [];
        let success = 0;
        let fail = 0;
        let totalTime = 0;
        let count = 0;

        resultsList.forEach(result => {
            if (!visibleRules.has(result.endpoint)) return;
            count += 1;
            if (result.status === 'success') success += 1;
            else fail += 1;
            totalTime += Number(result.response_time_ms || 0);
        });

        workingEl.textContent = success;
        failedEl.textContent = fail;
        avgEl.textContent = count ? `${Math.round(totalTime / count)}ms` : '--';
    }
    
    exportApiResults() {
        try {
            const payload = {
                generated_at: new Date().toISOString(),
                filters: { ...this.apiFilters },
                endpoints: this.endpoints,
                visible_endpoints: this.apiVisibleEndpoints,
                test_results: this.apiTestResults,
                summary: this.apiSummary
            };
            const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `con5013-api-${Date.now()}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Error exporting API results:', error);
        }
    }
    
    // System functionality
    async refreshSystemStats() {
        try {
            const response = await fetch(`${this.options.baseUrl}/api/system/stats`);
            const payload = await response.json();
            const stats = payload && payload.stats ? payload.stats : payload;
            this.systemStats = stats || {};
            this.displaySystemStats(this.systemStats);
            this.setConnectivity(true);
        } catch (error) {
            console.error('Error refreshing system stats:', error);
            this.setConnectivity(false);
        }
    }
    
    displaySystemStats(stats) {
        const customBoxes = (stats && Array.isArray(stats.custom_boxes)) ? stats.custom_boxes : [];
        this.renderCustomSystemBoxes(customBoxes);

        // System info
        const systemEnabled = this.isMetricEnabled('system_info');
        if (systemEnabled && stats.system) {
            const platformEl = document.getElementById('system-platform');
            if (platformEl) platformEl.textContent = stats.system.platform || 'Unknown';
            const pythonEl = document.getElementById('python-version');
            if (pythonEl) pythonEl.textContent = stats.system.python_version || 'Unknown';
            const hostEl = document.getElementById('system-hostname');
            if (hostEl) hostEl.textContent = stats.system.hostname || 'Unknown';
            const archEl = document.getElementById('system-arch');
            if (archEl) archEl.textContent = (stats.system.machine || stats.system.arch || 'Unknown');
        }

        // Application info
        const applicationStats = stats.application;
        const applicationEnabled = this.isMetricEnabled('application');
        if (applicationEnabled && applicationStats) {
            const routesEl = document.getElementById('app-routes');
            if (routesEl) routesEl.textContent = String(applicationStats.routes_count || '0');
            const extensionsEl = document.getElementById('app-extensions');
            if (extensionsEl) {
                const count = Array.isArray(applicationStats.extensions)
                    ? applicationStats.extensions.length
                    : (applicationStats.extensions?.length || 0);
                extensionsEl.textContent = String(count);
            }
            const debugEl = document.getElementById('app-debug');
            if (debugEl) debugEl.textContent = applicationStats.debug ? 'Enabled' : 'Disabled';
        }

        if (applicationStats) {
            const uptimeEl = document.getElementById('system-uptime');
            if (uptimeEl) {
                if (applicationStats.uptime_formatted) {
                    uptimeEl.textContent = applicationStats.uptime_formatted;
                } else if (typeof applicationStats.uptime_seconds === 'number') {
                    uptimeEl.textContent = this.formatDuration(applicationStats.uptime_seconds);
                }
            }
        } else if (systemEnabled) {
            const uptimeEl = document.getElementById('system-uptime');
            if (uptimeEl) {
                uptimeEl.textContent = '—';
            }
        }
        
        // Performance metrics
        if (this.isMetricEnabled('cpu') && stats.cpu) {
            const cpuUsage = Math.round(stats.cpu.usage_percent || 0);
            document.getElementById('cpu-usage').textContent = `${cpuUsage}%`;
            document.getElementById('cpu-progress').style.width = `${cpuUsage}%`;

            // Color coding
            const cpuProgress = document.getElementById('cpu-progress');
            cpuProgress.className = 'con5013-progress-bar';
            if (cpuUsage > 80) cpuProgress.classList.add('error');
            else if (cpuUsage > 60) cpuProgress.classList.add('warning');
        }

        if (this.isMetricEnabled('memory') && stats.memory && stats.memory.virtual) {
            const memoryUsage = Math.round(stats.memory.virtual.percent || 0);
            document.getElementById('memory-usage').textContent = `${memoryUsage}% (${stats.memory.virtual.used_gb}GB / ${stats.memory.virtual.total_gb}GB)`;
            document.getElementById('memory-progress').style.width = `${memoryUsage}%`;

            // Color coding
            const memoryProgress = document.getElementById('memory-progress');
            memoryProgress.className = 'con5013-progress-bar';
            if (memoryUsage > 80) memoryProgress.classList.add('error');
            else if (memoryUsage > 60) memoryProgress.classList.add('warning');
        }

        if (this.isMetricEnabled('disk') && stats.disk && stats.disk.usage) {
            const diskUsage = Math.round(stats.disk.usage.percent || 0);
            document.getElementById('disk-usage').textContent = `${diskUsage}%`;
            document.getElementById('disk-free').textContent = `${stats.disk.usage.free_gb}GB free`;
            document.getElementById('disk-progress').style.width = `${diskUsage}%`;

            // Color coding
            const diskProgress = document.getElementById('disk-progress');
            diskProgress.className = 'con5013-progress-bar';
            if (diskUsage > 90) diskProgress.classList.add('error');
            else if (diskUsage > 75) diskProgress.classList.add('warning');
        }

        // GPU info (if available)
        const gpuList = this.isMetricEnabled('gpu') ? document.getElementById('con5013-gpu-list') : null;
        if (gpuList && stats.gpus && (stats.gpus.devices || stats.gpus).length !== undefined) {
            const g = stats.gpus.devices ? stats.gpus : { devices: stats.gpus.devices, count: stats.gpus.count };
            const devices = g.devices || [];
            const countEl = document.getElementById('gpu-count');
            if (countEl) countEl.textContent = String(devices.length);
            // Render each GPU
            const inner = devices.map(dev => {
                const util = Math.round(dev.utilization_percent || 0);
                const memUsed = dev.memory_used_mb || 0;
                const memTotal = dev.memory_total_mb || 0;
                const memPct = memTotal ? Math.round((memUsed / memTotal) * 100) : 0;
                const temp = dev.temperature_c;
                const utilClass = util > 80 ? 'error' : (util > 60 ? 'warning' : 'ok');
                const tempClass = (temp !== null && temp !== undefined) ? (temp > 85 ? 'error' : (temp > 70 ? 'warning' : 'ok')) : 'ok';
                const memString = `${this.formatBytes(memUsed * 1024 * 1024)} / ${this.formatBytes(memTotal * 1024 * 1024)}`;
                return `
                    <div class="con5013-metric has-progress">
                        <span class="con5013-metric-label">${this.escapeHtml(dev.name || ('GPU ' + dev.index))}</span>
                        <span class="con5013-metric-value">
                            <span class="con5013-badges">
                                <span class="con5013-badge ${utilClass}">${util}%</span>
                                <span class="con5013-badge">${memString}</span>
                                ${temp !== null && temp !== undefined ? `<span class="con5013-badge ${tempClass}">${temp}°C</span>` : ''}
                            </span>
                        </span>
                    </div>
                    <div class="con5013-progress after-metric">
                        <div class="con5013-progress-bar${util>80?' error':(util>60?' warning':'')}" style="width:${util}%"></div>
                    </div>
                    <div class="con5013-divider"></div>
                `;
            }).join('');
            // Keep the count metric on top, then add details
            gpuList.innerHTML = `
                <div class="con5013-metric">
                    <span class="con5013-metric-label">GPUs</span>
                    <span class="con5013-metric-value" id="gpu-count">${devices.length}</span>
                </div>
                ${inner}
            `;
        } else if (gpuList) {
            const countEl = document.getElementById('gpu-count');
            if (countEl) countEl.textContent = '0';
            gpuList.innerHTML = `
                <div class="con5013-metric">
                    <span class="con5013-metric-label">GPUs</span>
                    <span class="con5013-metric-value" id="gpu-count">0</span>
                </div>
                <div class="con5013-metric">
                    <span class="con5013-metric-label">Status</span>
                    <span class="con5013-metric-value">No GPU metrics available</span>
                </div>
            `;
        }

        // Network info (rates computed client-side)
        if (this.isMetricEnabled('network') && stats.network && stats.network.io) {
            const io = stats.network.io;
            const ts = stats.timestamp || (Date.now() / 1000);
            let downRate = 0, upRate = 0;
            if (this.prevNetwork && this.prevNetwork.ts && ts > this.prevNetwork.ts) {
                const dt = ts - this.prevNetwork.ts;
                const dRecv = Math.max(0, io.bytes_recv - (this.prevNetwork.bytes_recv || 0));
                const dSent = Math.max(0, io.bytes_sent - (this.prevNetwork.bytes_sent || 0));
                downRate = dRecv / dt;
                upRate = dSent / dt;
            }
            const downEl = document.getElementById('net-down');
            const upEl = document.getElementById('net-up');
            const connsEl = document.getElementById('net-conns');
            const totalsEl = document.getElementById('net-totals');
            if (downEl) downEl.textContent = this.formatRate(downRate);
            if (upEl) upEl.textContent = this.formatRate(upRate);
            if (connsEl) connsEl.textContent = String(stats.network.connections_count || 0);
            if (totalsEl) totalsEl.textContent = `${this.formatBytes(io.bytes_recv)} / ${this.formatBytes(io.bytes_sent)}`;

            this.prevNetwork = { ts, bytes_recv: io.bytes_recv, bytes_sent: io.bytes_sent };
        } else if (!this.isMetricEnabled('network')) {
            this.prevNetwork = null;
        }
    }

    renderCustomSystemBoxes(boxes = []) {
        const container = document.getElementById('con5013-system');
        if (!container) return;

        // Remove previously rendered custom cards
        const previous = Array.from(container.querySelectorAll('[data-custom-system-card="true"]'));
        previous.forEach((card) => card.remove());

        if (!Array.isArray(boxes) || !boxes.length) {
            return;
        }

        const sorted = boxes
            .filter((box) => box && box.enabled !== false)
            .sort((a, b) => {
                const orderA = Number.isFinite(Number(a?.order)) ? Number(a.order) : 0;
                const orderB = Number.isFinite(Number(b?.order)) ? Number(b.order) : 0;
                if (orderA === orderB) {
                    return String(a?.title || '').localeCompare(String(b?.title || ''));
                }
                return orderA - orderB;
            });

        sorted.forEach((box) => {
            const card = document.createElement('div');
            card.className = 'con5013-system-card';
            card.dataset.customSystemCard = 'true';
            if (box && box.id) {
                card.id = `con5013-system-custom-${box.id}`;
            }

            const title = document.createElement('div');
            title.className = 'con5013-system-title';
            title.textContent = box?.title || 'Custom Metric';
            card.appendChild(title);

            let rows = Array.isArray(box?.rows) ? box.rows : [];
            if ((!rows || !rows.length) && box?.error) {
                rows = [{ name: 'Status', value: box.error }];
            }

            rows.forEach((row, index) => {
                if (!row) return;
                const label = row.name || row.label;
                if (!label) return;

                const metric = document.createElement('div');
                metric.className = 'con5013-metric';

                const hasProgress = row.progress && typeof row.progress.value === 'number' && !Number.isNaN(row.progress.value);
                if (hasProgress) {
                    metric.classList.add('has-progress');
                }

                const labelEl = document.createElement('span');
                labelEl.className = 'con5013-metric-label';
                labelEl.textContent = label;
                metric.appendChild(labelEl);

                const valueEl = document.createElement('span');
                valueEl.className = 'con5013-metric-value';
                let displayValue = row.display_value;
                if (displayValue === undefined || displayValue === null) {
                    displayValue = row.value;
                }
                if ((displayValue === undefined || displayValue === null || displayValue === '') && row.progress && row.progress.display_value !== undefined) {
                    displayValue = row.progress.display_value;
                }
                valueEl.textContent = displayValue !== undefined && displayValue !== null ? String(displayValue) : '';
                metric.appendChild(valueEl);

                card.appendChild(metric);

                if (hasProgress) {
                    const toNumber = (val, fallback) => {
                        const num = Number(val);
                        return Number.isFinite(num) ? num : fallback;
                    };
                    const min = toNumber(row.progress.min, 0);
                    let max = toNumber(row.progress.max, 100);
                    if (max <= min) {
                        max = min + 1;
                    }
                    const rawValue = toNumber(row.progress.value, min);
                    const clamped = Math.min(Math.max(rawValue, min), max);
                    const percent = ((clamped - min) / (max - min)) * 100;

                    const progressContainer = document.createElement('div');
                    progressContainer.className = 'con5013-progress after-metric';

                    const progressBar = document.createElement('div');
                    progressBar.className = 'con5013-progress-bar';
                    progressBar.style.width = `${Math.max(0, Math.min(100, percent))}%`;
                    progressBar.setAttribute('aria-valuemin', String(min));
                    progressBar.setAttribute('aria-valuemax', String(max));
                    progressBar.setAttribute('aria-valuenow', String(clamped));

                    if (row.progress && row.progress.tooltip) {
                        progressBar.title = String(row.progress.tooltip);
                    }

                    const progressClass = this.resolveProgressClass(row.progress, clamped);
                    if (progressClass) {
                        progressClass.split(/\s+/).filter(Boolean).forEach((cls) => progressBar.classList.add(cls));
                    }

                    progressContainer.appendChild(progressBar);
                    card.appendChild(progressContainer);

                    const includeDivider = (row.progress.divider !== false) && (index !== rows.length - 1);
                    if (includeDivider) {
                        const divider = document.createElement('div');
                        divider.className = 'con5013-divider';
                        card.appendChild(divider);
                    }
                } else if (row.divider && index !== rows.length - 1) {
                    const divider = document.createElement('div');
                    divider.className = 'con5013-divider';
                    card.appendChild(divider);
                }
            });

            container.appendChild(card);
        });
    }

    resolveProgressClass(progress, value) {
        if (!progress) return '';
        if (progress.color) {
            return String(progress.color);
        }
        const rules = Array.isArray(progress.color_rules) ? [...progress.color_rules] : [];
        rules.sort((a, b) => {
            const thresholdA = Number.isFinite(Number(a?.threshold)) ? Number(a.threshold) : -Infinity;
            const thresholdB = Number.isFinite(Number(b?.threshold)) ? Number(b.threshold) : -Infinity;
            return thresholdB - thresholdA;
        });

        for (const rule of rules) {
            if (!rule) continue;
            const threshold = Number(rule.threshold);
            if (!Number.isFinite(threshold)) continue;
            const cls = rule.class || rule.color;
            if (!cls) continue;
            const operator = (rule.operator || 'gte').toLowerCase();
            switch (operator) {
                case 'gt':
                case '>':
                    if (value > threshold) return cls;
                    break;
                case 'lt':
                case '<':
                    if (value < threshold) return cls;
                    break;
                case 'lte':
                case '<=':
                    if (value <= threshold) return cls;
                    break;
                case 'eq':
                case '==':
                    if (value === threshold) return cls;
                    break;
                case 'ne':
                case '!=':
                    if (value !== threshold) return cls;
                    break;
                case 'gte':
                case '>=':
                default:
                    if (value >= threshold) return cls;
                    break;
            }
        }
        return '';
    }

    // Utility functions
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    formatBytes(bytes) {
        const units = ['B','KB','MB','GB','TB'];
        let b = Math.max(0, Number(bytes) || 0), i = 0;
        while (b >= 1024 && i < units.length - 1) { b /= 1024; i++; }
        return `${b.toFixed(b < 10 && i>0 ? 1 : 0)} ${units[i]}`;
    }
    
    formatRate(bps) {
        // bytes per second to human readable
        return `${this.formatBytes(bps)}/s`;
    }
    
    formatDuration(seconds) {
        const s = Math.max(0, Math.floor(seconds || 0));
        const d = Math.floor(s / 86400);
        const h = Math.floor((s % 86400) / 3600);
        const m = Math.floor((s % 3600) / 60);
        const sec = s % 60;
        const parts = [];
        if (d) parts.push(`${d}d`);
        if (h) parts.push(`${h}h`);
        if (m) parts.push(`${m}m`);
        if (!parts.length || sec) parts.push(`${sec}s`);
        return parts.join(' ');
    }
    
    async loadLogSources() {
        try {
            const res = await fetch(`${this.options.baseUrl}/api/logs/sources`);
            const payload = await res.json();
            const sources = (payload && payload.sources) ? payload.sources : [];
            const sel = document.getElementById('con5013-log-source');
            if (sel) {
                sel.innerHTML = '';
                sources.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s;
                    opt.textContent = s;
                    sel.appendChild(opt);
                });
                if (this.defaultLogSource && sources.includes(this.defaultLogSource)) {
                    this.currentLogSource = this.defaultLogSource;
                } else if (sources.includes('flask')) this.currentLogSource = 'flask';
                else if (sources.length) this.currentLogSource = sources[0];
                sel.value = this.currentLogSource;
                sel.addEventListener('change', () => {
                    this.currentLogSource = sel.value;
                    this.refreshLogs();
                });
            }
            const lvl = document.getElementById('con5013-log-level');
            if (lvl) {
                lvl.addEventListener('change', () => {
                    this.currentLogLevel = lvl.value;
                    this.refreshLogs();
                });
            }
            const sort = document.getElementById('con5013-log-sort');
            if (sort) {
                sort.addEventListener('change', () => {
                    this.currentLogSort = sort.value;
                    this.resumeLogAutoScroll(false);
                    this.refreshLogs();
                });
            }
            this.setConnectivity(true);
        } catch (e) {
            console.error('Failed to load log sources', e);
            this.setConnectivity(false);
        }
    }

    // Connectivity indicator painter using inline SVG logo
    setConnectivity(ok) {
        this.connectivityOk = !!ok;
        this.paintConnectivity();
    }

    paintConnectivity() {
        const okColor = '#31d0aa';
        const errColor = '#d03157';
        const color = this.connectivityOk === false ? errColor : okColor;
        try {
            const svgs = document.querySelectorAll('#con5013-b-icon');
            svgs.forEach(svg => {
                const paths = svg.querySelectorAll('path');
                if (paths.length >= 2) {
                    paths[0].setAttribute('stroke', color);
                    paths[1].setAttribute('stroke', color);
                }
            });
        } catch (_) {}
    }
}

// Global instance
let con5013;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const bootstrap = window.CON5013_BOOTSTRAP || window.CON5013_CONFIG || window.con5013_bootstrap || {};
    const explicit = window.CON5013_OPTIONS || {};
    const derived = {};

    const pickString = (...values) => {
        for (const value of values) {
            if (typeof value === 'string' && value.trim()) {
                return value;
            }
        }
        return undefined;
    };

    if (explicit.baseUrl === undefined || explicit.baseUrl === null || explicit.baseUrl === '') {
        const prefix = pickString(
            explicit.baseUrl,
            bootstrap.baseUrl,
            bootstrap.url_prefix,
            bootstrap.CON5013_URL_PREFIX
        );
        if (prefix) {
            derived.baseUrl = prefix;
        }
    }

    if (explicit.hotkey === undefined || explicit.hotkey === null || explicit.hotkey === '') {
        const hotkey = pickString(explicit.hotkey, bootstrap.hotkey, bootstrap.CON5013_HOTKEY);
        if (hotkey) {
            derived.hotkey = hotkey;
        }
    }

    if (explicit.updateInterval === undefined || explicit.updateInterval === null) {
        const intervalCandidate = bootstrap.updateInterval ?? bootstrap.CON5013_SYSTEM_UPDATE_INTERVAL;
        const numericInterval = Number(intervalCandidate);
        if (!Number.isNaN(numericInterval) && numericInterval > 0) {
            derived.updateInterval = numericInterval * 1000;
        }
    }

    if (!derived.baseUrl || derived.baseUrl === '') {
        const scripts = [];
        if (CON5013_SCRIPT_ELEMENT) scripts.push(CON5013_SCRIPT_ELEMENT);
        scripts.push(...document.querySelectorAll('script[data-con5013-base]'));
        scripts.push(...document.querySelectorAll('script[src*="con5013/static/js/con5013.js"]'));
        const scriptEl = scripts.find(el => el && el.getAttribute);
        if (scriptEl) {
            const attrBase = scriptEl.getAttribute('data-con5013-base');
            if (attrBase && attrBase.trim()) {
                derived.baseUrl = attrBase.trim();
            }
            if ((!derived.hotkey || derived.hotkey === '') && scriptEl.getAttribute('data-con5013-hotkey')) {
                derived.hotkey = scriptEl.getAttribute('data-con5013-hotkey').trim();
            }
            if ((!derived.baseUrl || derived.baseUrl === '') && scriptEl.src) {
                try {
                    const parsed = new URL(scriptEl.src, window.location.href);
                    const path = parsed.pathname.replace(/\/+static\/js\/con5013\.js$/i, '');
                    if (parsed.origin === window.location.origin) {
                        derived.baseUrl = path;
                    } else {
                        derived.baseUrl = `${parsed.origin}${path}`;
                    }
                } catch (_) {
                    const raw = scriptEl.getAttribute('src') || '';
                    const sanitized = raw.split('?')[0].split('#')[0].replace(/\/+static\/js\/con5013\.js$/i, '');
                    if (sanitized) {
                        derived.baseUrl = sanitized;
                    }
                }
            }
        }
    }

    const options = { ...derived, ...explicit };
    con5013 = new Con5013Console(options);

    try {
        if (typeof window !== 'undefined') {
            window.con5013 = con5013;
            // Backwards compatibility shim for legacy integrations
            if (!window.con5013Overlay) {
                window.con5013Overlay = con5013;
            }
            window.Con5013Console = Con5013Console;

            const readyDetail = { instance: con5013, kind: 'modern', api: con5013 };
            try {
                window.dispatchEvent(new CustomEvent('con5013:ready', { detail: readyDetail }));
            } catch (dispatchError) {
                try {
                    const legacyEvent = document.createEvent('CustomEvent');
                    legacyEvent.initCustomEvent('con5013:ready', false, false, readyDetail);
                    window.dispatchEvent(legacyEvent);
                } catch (_) {
                    // Ignore environments without CustomEvent support
                }
            }

            if (!window.CON5013_READY_PROMISE || typeof window.CON5013_READY_PROMISE.then !== 'function') {
                window.CON5013_READY_PROMISE = Promise.resolve(readyDetail);
            } else {
                window.CON5013_READY_PROMISE = window.CON5013_READY_PROMISE.then(() => readyDetail);
            }

            window.CON5013_READY = true;
            window.CON5013_READY_DETAIL = readyDetail;
        }
    } catch (err) {
        console.warn('Con5013: unable to expose console globally', err);
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Con5013Console;
    module.exports.openCon5013Console = openCon5013Console;
}




