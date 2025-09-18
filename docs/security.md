# Con5013 Security Guide

Con5013 is designed to feel frictionless during early application development, so the
extension ships with an "open" security posture by default. The console automatically
registers its blueprint on `/con5013`, enables every major feature (logs, terminal, API
scanner, system monitor), and skips authentication. This mirrors how developers usually
need to work locally: short-lived environments, trusted teammates, and a desire for
full visibility with minimal setup.

That developer-first experience also means you **must** harden Con5013 before exposing
it in shared or production environments. This document explains how the default
configuration behaves, why it is intentionally permissive, and the configuration steps
required to operate the console safely when real users or sensitive infrastructure are
involved.

## Default security posture ("open" profile)

Con5013 treats security as opt-in so that cloning the repository and adding the
extension to a Flask app "just works". The default profile behaves as follows:

- `CON5013_SECURITY_PROFILE` is set to `"open"`, which leaves all high-impact features
  (terminal, API scanner, log clearing, auto-injected UI assets, floating overlay,
  Crawl4AI integration) enabled.
- `CON5013_AUTHENTICATION` is `False`, so the blueprint does not demand credentials and
  every route remains publicly reachable.
- The API scanner is free to perform outbound HTTP requests (`CON5013_API_ALLOW_EXTERNAL`
  defaults to `True`) and no allowlist is enforced.
- Dangerous terminal helpers such as HTTP probes remain active, though Python `eval`
  stays disabled until explicitly enabled with `CON5013_TERMINAL_ALLOW_PY`.

This configuration is perfect for **local development** because it keeps configuration
files short and avoids blocking the console when an engineer just wants to inspect
logs or tweak features. It is **not safe** to run this profile on the public internet
or in any shared environment.

## Hardening Con5013 for production use

When the console accompanies an application into staging or production, apply the steps
below to protect both the Con5013 surface and the application it can control.

### 1. Choose a security profile

Con5013 ships with built-in security presets you can apply via
`CON5013_SECURITY_PROFILE`:

- `"open"` *(default)* – the permissive profile described above.
- `"secured"` – disables the most sensitive capabilities unless you opt back in. The
  preset turns off the terminal, API scanner, external HTTP testing, log clearing,
  overlay auto-injection, Crawl4AI integration, WebSocket helpers, and Python `eval`.

Profiles are applied during `Con5013.init_app()`. You can still override individual
settings afterward if you need a specific feature:

```python
app.config.update({
    "CON5013_SECURITY_PROFILE": "secured",
    "CON5013_ENABLE_TERMINAL": True,  # opt back in for trusted operators
})
```

Call `console.apply_security_profile("secured")` manually if you need to re-evaluate
presets at runtime (for example, when promoting an app from staging to production).

### 2. Enable authentication

Set `CON5013_AUTHENTICATION` to protect every Con5013 route through the blueprint’s
`before_request` guard. The helper supports multiple strategies:

- **Basic auth** – configure `CON5013_AUTHENTICATION = "basic"` along with
  `CON5013_AUTH_USER` and `CON5013_AUTH_PASSWORD`. Browsers will prompt for credentials
  automatically.
- **Static token** – set `CON5013_AUTHENTICATION = "token"` and provide
  `CON5013_AUTH_TOKEN`. Clients must send an `Authorization: Bearer <token>` or
  `X-Auth-Token` header.
- **Custom callable** – supply your own function via `CON5013_AUTHENTICATION` or
  `CON5013_AUTH_CALLBACK`. The callable receives the Flask `request` and can integrate
  with Flask-Login, JWTs, corporate SSO, or any other policy. Return `True`/`None` to
  allow the request, `False` to reject it, raise `werkzeug.exceptions.Unauthorized`, or
  return a Flask/Werkzeug response object.

If you need fine-grained authorization (different roles for logs versus system
commands), enforce it inside your callable by inspecting `request.endpoint` and the
HTTP method.

### 3. Control high-risk tooling

Even with authentication enabled, re-expose only the tooling your operators need:

- **Terminal** – leave `CON5013_ENABLE_TERMINAL` disabled unless the production support
  team truly needs it. If enabled, keep `CON5013_TERMINAL_ALLOW_PY = False` to prevent
  arbitrary Python execution.
- **API scanner** – keep `CON5013_ENABLE_API_SCANNER` disabled unless you must document
  routes in production. When enabled, set `CON5013_API_ALLOW_EXTERNAL = False` and
  populate `CON5013_API_EXTERNAL_ALLOWLIST` with explicit URLs that are safe to probe.
- **Log management** – consider disabling log clearing (`CON5013_ALLOW_LOG_CLEAR = False`)
  so the console cannot erase audit trails.
- **System monitor** – review the data exposed by `/api/system/*` and ensure it does
  not violate operational policies before leaving it enabled.

### 4. Restrict network exposure

Treat the Con5013 blueprint like any other administrative interface:

- Serve it only over HTTPS.
- Place it behind a VPN, bastion host, or reverse proxy that performs its own
  authentication and rate limiting.
- Run it on a separate host name or path segment that your WAF or API gateway can
  monitor.

### 5. Audit and monitor usage

- Enable access logging for the Con5013 routes so you can trace operator activity.
- Review the terminal history and `/api/config` output regularly; the secured profile
  keeps them protected, but authenticated users may still perform sensitive actions.
- Rotate credentials or tokens whenever staff changes or incidents occur.

## Usage warnings

- **Do not expose the open profile to untrusted users.** Anyone who can reach the
  console can read your logs, run terminal commands, probe internal APIs, or execute
  custom commands.
- **Treat custom commands as production code.** They can modify databases, call third-
  party services, or change application state. Secure them with the same rigor as the
  rest of your admin tooling.
- **Remember the primary audience.** Con5013 is a development aid; production usage is
  supported, but only after deliberate hardening and ongoing monitoring.

By combining the secured profile, explicit authentication, and conservative feature
selection, you can transform Con5013 from a rapid-development console into a controlled
operations dashboard suitable for production environments.
