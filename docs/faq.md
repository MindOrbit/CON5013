# Con5013 FAQ

A collection of deeper questions and answers about integrating, customizing, and operating the Con5013 console in real-world projects.

## General Architecture

### Q1. When should I embed the console as an overlay versus using the dedicated `/con5013/` route?
Use the overlay when you want in-app observability without leaving the page—e.g., debugging UI workflows while monitoring logs. The standalone route is better for operational teams who need a persistent dashboard or who access the console from a second monitor. You can support both simultaneously by leaving the default prefix in place and including the overlay script only on selected templates.

### Q2. How does Con5013 fit into an application factory pattern?
Initialize the extension after you create your Flask app instance. Either call `Con5013(app, config=...)` inside your `create_app` function, or build once and reuse by storing `console = Con5013()` globally and calling `console.init_app(app)` for each factory-created instance. The extension automatically registers its blueprint per application instance.

### Q3. Can I mount the console under a custom admin blueprint?
Yes. Set `CON5013_URL_PREFIX` when initializing or instantiate the `Con5013Blueprint` helper and register it within your admin blueprint namespace. All static assets and API routes honor the prefix, so reverse proxies and custom URL hierarchies stay clean.

## Security & Access Control

### Q4. How do I lock the console down in production?
Pair Con5013 with your existing Flask authentication. Because everything is served under the configured prefix, wrapping the blueprint registration with `@login_required` decorators or using a `before_request` guard is enough. For extra safety, disable sensitive modules (e.g., Terminal) via config and restrict the console route at the proxy layer (Basic Auth, IP allowlists, VPN-only access).

### Q5. Can I offer read-only access to certain users?
Yes. Disable modules per role before the request is processed. For example, on each request you can toggle `console.feature_flags` based on the logged-in user, hiding the Terminal tab while keeping Logs and API Scanner available. Additionally, expose curated custom commands that surface diagnostics without granting shell access.

### Q6. How do I audit who executed terminal commands or triggered scans?
Subscribe to Flask’s signal system or wrap `terminal_engine.execute_command` with a logging decorator. Persist metadata such as user ID, command, IP, and timestamp to your audit store. If you are behind a proxy, capture the `X-Forwarded-For` header as part of the audit event.

## Logging & Observability

### Q7. What’s the recommended way to stream logs from Celery or other worker processes?
Attach Con5013 handlers to the worker loggers and point them to a shared file or structured sink. Alternatively, expose a lightweight log-forwarding endpoint from your worker that Con5013 can poll via a custom log source. For Celery, configure the worker logger to propagate to root so the default capture picks it up.

### Q8. How do I prevent massive log files from slowing down the Logs tab?
Cap the UI payload using `CON5013_MAX_LOG_ENTRIES`, rotate files aggressively, and favor structured logging (JSON) so filtering can happen server-side. For extreme volumes, point Con5013 to a tailing microservice that streams only the latest window instead of the full file.

### Q9. What happens if a configured log file disappears or rotates?
Con5013 detects `ENOENT` errors and displays a warning badge in the Logs tab. Once the file reappears, the watcher resumes automatically. For rotation schemes that rename files (e.g., `logfile.log.1`), prefer symlinks or copy-truncate rotation so the watched path stays stable.

## Customization & Extensibility

### Q10. How can I theme the console to match my brand?
Set `CON5013_THEME` to `custom` and provide `CON5013_CUSTOM_CSS`. Start from the default CSS bundle (inspect `/con5013/static/css`) and override variables like accent colors, blur intensity, and font stacks. Test in overlay mode to make sure contrast and transparency look good against your app’s background.

### Q11. What are best practices for custom terminal commands?
Treat commands like micro-APIs: validate input, return structured dictionaries, and keep execution deterministic. For slow tasks, kick off background jobs (Celery, RQ) and respond with a task ID that users can poll using another command. Always sanitize or scope filesystem access to avoid exposing secrets.

### Q12. Can I expose health data from external services in the System tab?
Yes. Use the `system_monitor` hooks to register new collectors that fetch metrics from services like Redis, Elasticsearch, or Kubernetes. Return normalized dictionaries so they render alongside CPU/memory stats. For read-only dashboards, disable Terminal but keep these collectors active for a holistic operations view.

### Q13. How do I add a custom card to the System tab?
Call `console.add_system_box` after initializing Con5013. Provide a unique ID (or let the helper derive one from the title) plus a list of row dictionaries. Each row needs a `name` and `value`, and can optionally include a `progress` spec for inline gauges. For dynamic content, supply `callable` values or a `provider` function that returns the entire box payload. You can toggle visibility via `console.set_system_box_enabled` or remove it altogether with `console.remove_system_box`. The Matrix demo shows a static example, while the advanced implementation demonstrates dynamic provider-driven boxes.【F:examples/matrix_app.py†L74-L90】【F:examples/advanced_implementation.py†L128-L194】

### Q14. How do I integrate Crawl4AI telemetry if I already have bespoke scraping logic?
Enable `CON5013_CRAWL4AI_INTEGRATION` and attach your custom crawler loggers with aliases such as `crawl4ai-mybot`. Implement custom commands (e.g., `crawl status`, `crawl restart`) that call into your scraping orchestration layer. The API Scanner remains independent, so you can monitor REST endpoints and scraping jobs from the same console.

## Deployment & Operations

### Q15. Does Con5013 work behind Gunicorn or uWSGI with multiple workers?
Yes, but shared state matters. Use a centralized backend for terminal command execution queues and log storage if workers are stateless. For streaming features, enable sticky sessions or run the console on a single worker via a sidecar Flask process that proxies to your main app.

### Q16. What should I consider when deploying behind a reverse proxy (Nginx, Traefik)?
Forward WebSocket traffic for the terminal endpoint, set proper `X-Forwarded-*` headers so system metrics report client info accurately, and, if SSL termination happens at the proxy, configure Flask’s `PREFERRED_URL_SCHEME` so generated links point to HTTPS.

### Q17. Can I run Con5013 in environments without internet access?
Absolutely. All static assets ship with the package, and the Matrix demo app runs offline. Make sure your virtual environment has the dependencies pre-installed, or build a wheel in a connected environment and transport it to the air-gapped network.

### Q18. How do I integrate Con5013 in CI pipelines?
Use the API endpoints to trigger self-tests. For instance, spin up a Flask app in your CI job, call `/con5013/api/system/health` to verify the extension loaded, and hit `/con5013/api/scanner/test-all` for route validation. You can also run pytest suites against the demo Matrix app as part of regression checks.

### Q19. Is it possible to script console actions from external tools?
Yes. Every tab corresponds to REST APIs documented under `/con5013/api`. Script actions using HTTP clients, or integrate with observability platforms by exporting logs, system metrics, or API test reports in JSON. Authentication is left to your Flask app, so reuse existing tokens or session cookies.

