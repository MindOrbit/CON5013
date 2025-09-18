"""Security helpers for Con5013 protected endpoints."""

from __future__ import annotations

import base64
import hmac
import logging
from typing import Any, Callable, Optional

from flask import Response, current_app, jsonify, render_template, request
from werkzeug.exceptions import Unauthorized
from werkzeug.wrappers.response import Response as WerkzeugResponse

logger = logging.getLogger(__name__)


def _get_extension_config() -> Optional[dict[str, Any]]:
    """Return the Con5013 configuration from the current Flask app."""
    ext = getattr(current_app, "extensions", {}).get("con5013")
    if ext is None:
        logger.debug("Con5013 extension not registered on current app")
        return None
    return getattr(ext, "config", None)


def _is_api_request(config: dict[str, Any]) -> bool:
    endpoint = request.endpoint or ""
    if endpoint.startswith("con5013."):
        endpoint_name = endpoint.split(".", 1)[1]
        if endpoint_name.startswith("api_"):
            return True
    url_prefix = config.get("CON5013_URL_PREFIX", "/con5013")
    api_prefix = f"{url_prefix.rstrip('/')}/api"
    full_path = request.path or ""
    return full_path.startswith(api_prefix)


def _json_response(message: str, status_code: int) -> Response:
    return jsonify({"status": "error", "message": message}), status_code


def _html_response(message: str, status_code: int) -> Response:
    return render_template(
        "auth_required.html",
        status_code=status_code,
        message=message,
        request_path=request.path,
    ), status_code


def _unauthorized(
    message: str,
    *,
    is_api: bool,
    status_code: int = 401,
    headers: Optional[dict[str, str]] = None,
) -> Response:
    response = _json_response(message, status_code) if is_api else _html_response(message, status_code)
    if headers:
        resp, code = response
        for key, value in headers.items():
            resp.headers[key] = value
        return resp, code
    return response


def _get_basic_credentials() -> tuple[Optional[str], Optional[str]]:
    auth = request.authorization
    if auth is None and "Authorization" in request.headers:
        try:
            scheme, encoded = request.headers["Authorization"].split(" ", 1)
        except ValueError:
            return None, None
        if scheme.lower() == "basic":
            try:
                decoded = base64.b64decode(encoded).decode("utf-8")
            except Exception:
                return None, None
            if ":" not in decoded:
                return None, None
            username, password = decoded.split(":", 1)
            return username, password
        return None, None
    if auth is None:
        return None, None
    return auth.username, auth.password


def _extract_token() -> Optional[str]:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    if header.lower().startswith("token "):
        return header[6:].strip()
    return request.headers.get("X-Auth-Token")


def _execute_callback(callback: Callable[[Any], Any], *, is_api: bool) -> Optional[Response]:
    try:
        result = callback(request)
    except Unauthorized as exc:
        logger.info("Con5013 auth callback raised Unauthorized: %s", exc)
        return _unauthorized(str(exc), is_api=is_api)
    except Exception:  # pragma: no cover - user callback can raise anything
        logger.exception("Con5013 auth callback raised an unexpected error")
        return _unauthorized("Authentication callback error", is_api=is_api, status_code=500)

    if result is None or result is True:
        return None
    if result is False:
        return _unauthorized("Access denied", is_api=is_api, status_code=403)
    if isinstance(result, (Response, WerkzeugResponse)):
        return result
    if isinstance(result, tuple):
        return current_app.make_response(result)
    return current_app.make_response(result)


def enforce_con5013_security() -> Optional[Response]:
    """Validate access to the Con5013 blueprint based on configuration."""
    config = _get_extension_config()
    if not config:
        return None

    mode = config.get("CON5013_AUTHENTICATION")
    if not mode:
        return None
    if isinstance(mode, str) and mode.lower() in {"none", "false"}:
        return None

    is_api = _is_api_request(config)

    if callable(mode):
        callback_response = _execute_callback(mode, is_api=is_api)
        if callback_response is None:
            return None
        return callback_response

    normalized = mode.lower() if isinstance(mode, str) else str(mode).lower()

    if normalized == "basic":
        expected_user = config.get("CON5013_AUTH_USER")
        expected_password = config.get("CON5013_AUTH_PASSWORD")
        if not expected_user or expected_password is None:
            logger.warning("Basic authentication is enabled but credentials are not configured")
            return _unauthorized(
                "Authentication is not properly configured",
                is_api=is_api,
                status_code=500,
            )
        username, password = _get_basic_credentials()
        if not username or not password:
            return _unauthorized(
                "Authentication required",
                is_api=is_api,
                headers={"WWW-Authenticate": 'Basic realm="Con5013"'},
            )
        if hmac.compare_digest(username, str(expected_user)) and hmac.compare_digest(password, str(expected_password)):
            return None
        return _unauthorized(
            "Invalid credentials",
            is_api=is_api,
            headers={"WWW-Authenticate": 'Basic realm="Con5013"'},
        )

    if normalized == "token":
        expected_token = config.get("CON5013_AUTH_TOKEN")
        if expected_token is None:
            logger.warning("Token authentication is enabled but no token is configured")
            return _unauthorized(
                "Authentication is not properly configured",
                is_api=is_api,
                status_code=500,
            )
        provided_token = _extract_token()
        if not provided_token:
            return _unauthorized("Missing token", is_api=is_api)
        if hmac.compare_digest(str(provided_token), str(expected_token)):
            return None
        return _unauthorized("Invalid token", is_api=is_api)

    callback = config.get("CON5013_AUTH_CALLBACK")
    if callable(callback):
        callback_response = _execute_callback(callback, is_api=is_api)
        if callback_response is None:
            return None
        return callback_response

    logger.warning("Unknown CON5013_AUTHENTICATION mode: %s", mode)
    return _unauthorized("Access denied", is_api=is_api, status_code=403)
