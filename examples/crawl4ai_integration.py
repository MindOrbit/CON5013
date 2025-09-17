#!/usr/bin/env python3
"""Con5013 + Crawl4AI deep integration demo."""

import asyncio
import contextlib
import logging
import random
import sys
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template_string, request

from con5013 import Con5013

try:  # pragma: no cover - optional dependency for the live demo
    from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig  # type: ignore
except Exception:  # pragma: no cover - fallback when API changes
    AsyncWebCrawler = None  # type: ignore
    CacheMode = None  # type: ignore
    CrawlerRunConfig = None  # type: ignore

try:  # pragma: no cover - optional dependency for legacy versions
    from crawl4ai import WebCrawler  # type: ignore
except Exception:  # pragma: no cover - fallback when class is missing
    WebCrawler = None  # type: ignore

CRAWL4AI_AVAILABLE = bool(AsyncWebCrawler or WebCrawler)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
crawl4ai_logger = logging.getLogger("crawl4ai")
crawl4ai_logger.setLevel(logging.INFO)

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key-here"

# Initialize Con5013 with Crawl4AI integration
console = Con5013(
    app,
    config={
        "CON5013_URL_PREFIX": "/crawl",
        "CON5013_THEME": "dark",
        "CON5013_ENABLE_LOGS": True,
        "CON5013_ENABLE_TERMINAL": True,
        "CON5013_ENABLE_API_SCANNER": True,
        "CON5013_ENABLE_SYSTEM_MONITOR": True,
        "CON5013_MONITOR_SYSTEM_INFO": False,
        "CON5013_MONITOR_APPLICATION": False,
        "CON5013_MONITOR_DISK": False,
        "CON5013_MONITOR_NETWORK": False,
        "CON5013_MONITOR_GPU": True,
        "CON5013_CRAWL4AI_INTEGRATION": True,
        "CON5013_AUTO_INJECT": True,
        "CON5013_LOG_SOURCES": [{"name": "crawl4ai"}],
        "CON5013_HOTKEY": "Alt+C",
    },
)

if console.log_monitor:
    console.log_monitor.set_logger_alias("crawl4ai", "crawl4ai")
    console.log_monitor.set_logger_alias("crawl4ai.", "crawl4ai")
    console.log_monitor.set_logger_alias("Crawl4AI", "crawl4ai")
    console.log_monitor.add_log_entry(
        "crawl4ai",
        "INFO",
        "Crawl4AI log stream ready – the overlay filters this source to ERROR entries.",
    )


def _now() -> str:
    """Return an ISO-8601 timestamp in UTC with a trailing Z."""

    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _bool_from_request(value: Any) -> bool:
    """Interpret truthy values from JSON or query string payloads."""

    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    string_value = str(value).strip().lower()
    return string_value in {"1", "true", "yes", "on", "y"}


def _format_percent(value: float) -> str:
    return f"{value:.1f}%"


def _humanize_duration(seconds: Optional[float]) -> str:
    if not seconds:
        return "—"
    minutes, remaining = divmod(int(seconds), 60)
    if minutes:
        return f"{minutes}m {remaining}s"
    return f"{remaining}s"


class Crawl4AISimulator:
    """Minimal in-memory Crawl4AI job orchestrator used for the demo."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: Dict[int, Dict[str, Any]] = {}
        self._job_counter = 0
        self._errors: deque[Dict[str, Any]] = deque(maxlen=50)
        self._bootstrapped = False

    # ------------------------------------------------------------------
    # Job lifecycle helpers
    # ------------------------------------------------------------------
    def start_job(
        self,
        url: str,
        *,
        profile: str = "default",
        fail: bool = False,
        launched_by: str = "api",
    ) -> Dict[str, Any]:
        """Queue a new Crawl4AI job and begin simulating its lifecycle."""

        with self._lock:
            self._job_counter += 1
            job_id = self._job_counter
            job = {
                "id": job_id,
                "url": url,
                "profile": profile,
                "status": "queued",
                "launched_by": launched_by,
                "fail_mode": bool(fail),
                "created_at": _now(),
                "started_at": None,
                "started_ts": None,
                "completed_at": None,
                "completed_ts": None,
                "progress": 0,
                "pages_scraped": 0,
                "items_extracted": 0,
                "duration_seconds": None,
                "last_heartbeat": None,
                "error": None,
            }
            self._jobs[job_id] = job

        crawl4ai_logger.info(
            "Queued Crawl4AI job #%s for %s (profile=%s)", job_id, url, profile
        )
        worker = threading.Thread(
            target=self._run_job, args=(job_id, fail), daemon=True
        )
        worker.start()
        return self._serialize_job(job)

    def _run_job(self, job_id: int, fail: bool) -> None:
        heartbeat = 0
        while True:
            time.sleep(1.2)
            with self._lock:
                job = self._jobs.get(job_id)
                if not job:
                    return
                if job["status"] in {"failed", "completed"}:
                    return
                if job["status"] == "queued":
                    job["status"] = "running"
                    job["started_at"] = _now()
                    job["started_ts"] = time.time()
                job["progress"] = min(100, job["progress"] + random.randint(10, 20))
                job["pages_scraped"] += random.randint(1, 3)
                job["items_extracted"] += random.randint(2, 6)
                job["last_heartbeat"] = _now()
                progress_snapshot = job["progress"]
            heartbeat += 1

            if fail and heartbeat >= 4:
                self._fail_job(
                    job_id,
                    f"Extractor pipeline crashed on {job['url']} (simulated)",
                )
                return

            crawl4ai_logger.info(
                "Job #%s heartbeat – %s%% complete", job_id, progress_snapshot
            )

            if progress_snapshot >= 100:
                self._complete_job(job_id)
                return

    def _complete_job(self, job_id: int) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job["status"] = "completed"
            job["progress"] = 100
            job["completed_ts"] = time.time()
            job["completed_at"] = _now()
            if job.get("started_ts"):
                job["duration_seconds"] = job["completed_ts"] - job["started_ts"]
        crawl4ai_logger.info("Job #%s completed successfully", job_id)

    def _fail_job(self, job_id: int, message: str) -> None:
        failure_timestamp = _now()
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job["status"] = "failed"
            job["progress"] = min(job["progress"], 95)
            job["completed_ts"] = time.time()
            job["completed_at"] = failure_timestamp
            if job.get("started_ts"):
                job["duration_seconds"] = job["completed_ts"] - job["started_ts"]
            job["error"] = message
            self._errors.appendleft(
                {
                    "job_id": job_id,
                    "url": job["url"],
                    "message": message,
                    "timestamp": failure_timestamp,
                }
            )
        crawl4ai_logger.error(message)

    def log_manual_error(self, message: str) -> Dict[str, Any]:
        entry = {
            "job_id": "diagnostics",
            "url": "manual://diagnostics",
            "message": message,
            "timestamp": _now(),
        }
        with self._lock:
            self._errors.appendleft(entry)
        crawl4ai_logger.error(message)
        return entry

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------
    def list_jobs(self) -> List[Dict[str, Any]]:
        with self._lock:
            jobs = [self._serialize_job(job) for job in self._jobs.values()]
        return sorted(jobs, key=lambda job: job["id"], reverse=True)

    def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return self._serialize_job(job) if job else None

    def get_recent_errors(self, limit: int = 5) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._errors)[:limit]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            jobs = list(self._jobs.values())
            recent_errors = list(self._errors)

        total = len(jobs)
        active = sum(1 for job in jobs if job["status"] == "running")
        queued = sum(1 for job in jobs if job["status"] == "queued")
        completed = sum(1 for job in jobs if job["status"] == "completed")
        failed = sum(1 for job in jobs if job["status"] == "failed")

        durations = [job.get("duration_seconds") for job in jobs if job.get("duration_seconds")]
        avg_runtime = sum(durations) / len(durations) if durations else 0.0
        runtime_minutes = sum(durations) / 60.0 if durations else 0.0

        total_pages = sum(job.get("pages_scraped", 0) for job in jobs)
        total_items = sum(job.get("items_extracted", 0) for job in jobs)
        pages_per_minute = total_pages / runtime_minutes if runtime_minutes else 0.0
        items_per_minute = total_items / runtime_minutes if runtime_minutes else 0.0

        success_rate = (completed / total * 100) if total else 0.0
        failure_rate = (failed / total * 100) if total else 0.0

        return {
            "total_jobs": total,
            "active": active,
            "queued": queued,
            "completed": completed,
            "failed": failed,
            "success_rate": round(success_rate, 2),
            "failure_rate": round(failure_rate, 2),
            "avg_runtime": round(avg_runtime, 2) if avg_runtime else 0.0,
            "pages_per_minute": round(pages_per_minute, 2) if pages_per_minute else 0.0,
            "items_per_minute": round(items_per_minute, 2) if items_per_minute else 0.0,
            "total_pages": total_pages,
            "total_items": total_items,
            "last_error": recent_errors[0] if recent_errors else None,
        }

    def ensure_bootstrap_jobs(self) -> None:
        with self._lock:
            if self._bootstrapped:
                return
            self._bootstrapped = True
        # Kick off sample jobs to populate metrics, including a failure
        self.start_job(
            "https://example.com/articles",
            profile="discovery",
            launched_by="bootstrap",
        )
        self.start_job(
            "https://example.com/broken",
            profile="diagnostics",
            launched_by="bootstrap",
            fail=True,
        )

    def _serialize_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(job)
        data.pop("started_ts", None)
        data.pop("completed_ts", None)
        return data


crawl4ai_simulator = Crawl4AISimulator()


# ----------------------------------------------------------------------
# Custom Con5013 system boxes
# ----------------------------------------------------------------------

def crawl4ai_overview_box() -> Dict[str, Any]:
    metrics = crawl4ai_simulator.stats()
    rows: List[Dict[str, Any]] = [
        {"name": "Active jobs", "value": metrics["active"]},
        {"name": "Queued jobs", "value": metrics["queued"]},
        {"name": "Completed", "value": metrics["completed"]},
        {
            "name": "Failed",
            "value": metrics["failed"],
            "progress": {
                "value": metrics["failure_rate"],
                "max": 100,
                "display_value": _format_percent(metrics["failure_rate"]),
                "color": "#f97316",
            },
        },
        {
            "name": "Success rate",
            "value": _format_percent(metrics["success_rate"]),
            "progress": {
                "value": metrics["success_rate"],
                "max": 100,
                "display_value": _format_percent(metrics["success_rate"]),
                "color": "#22c55e",
            },
        },
    ]
    if metrics["last_error"]:
        last_error = metrics["last_error"]
        rows.append(
            {
                "name": "Last error",
                "value": last_error["message"],
                "meta": {
                    "timestamp": last_error["timestamp"],
                    "job_id": last_error.get("job_id"),
                },
            }
        )
    return {
        "rows": rows,
        "meta": {"updated": _now()},
    }


def crawl4ai_throughput_box() -> Dict[str, Any]:
    metrics = crawl4ai_simulator.stats()
    rows = [
        {"name": "Avg runtime", "value": _humanize_duration(metrics["avg_runtime"])},
        {"name": "Pages / min", "value": metrics["pages_per_minute"]},
        {"name": "Items / min", "value": metrics["items_per_minute"]},
        {"name": "Total pages", "value": metrics["total_pages"]},
        {"name": "Total items", "value": metrics["total_items"]},
    ]
    return {
        "rows": rows,
        "meta": {"updated": _now()},
    }


console.add_system_box(
    "crawl4ai-overview",
    title="Crawl4AI Job Health",
    provider=crawl4ai_overview_box,
    description="Live queue metrics captured from Crawl4AI.",
    order=1,
)
console.add_system_box(
    "crawl4ai-throughput",
    title="Crawl4AI Throughput",
    provider=crawl4ai_throughput_box,
    description="Aggregated throughput derived from completed jobs.",
    order=2,
)


# ----------------------------------------------------------------------
# Custom terminal commands
# ----------------------------------------------------------------------
if console.terminal_engine:
    def crawl4ai_run_command(args: List[str]) -> Dict[str, Any]:
        """Run Crawl4AI from the terminal.

        Usage: crawl4ai-run [URL] [--mode markdown|clean-html|links] [--link-limit N]
                             [--simulate] [--profile name] [--fail]
        """

        default_url = "https://example.com/articles"
        url = None
        profile = "default"
        fail = False
        simulate = False
        mode = "markdown"
        mode_explicit = False
        link_limit = 5
        messages: List[str] = []
        unknown_args: List[str] = []

        index = 0

        def _consume_value(option: str) -> Optional[str]:
            """Advance the index and return the next CLI argument."""

            nonlocal index
            if index + 1 >= len(args):
                messages.append(
                    f"Missing value for {option}; keeping previous setting."
                )
                return None
            index += 1
            return args[index]

        while index < len(args):
            arg = args[index]
            if arg in {"--fail", "-f"}:
                fail = True
                simulate = True
            elif arg in {"--simulate"}:
                simulate = True
            elif arg.startswith("--profile="):
                profile = arg.split("=", 1)[1] or profile
                simulate = True
            elif arg == "--profile":
                value = _consume_value("--profile")
                if value is not None:
                    profile = value
                    simulate = True
            elif arg.startswith("--mode="):
                mode = arg.split("=", 1)[1] or mode
                mode_explicit = True
            elif arg in {"--mode", "-m"}:
                value = _consume_value("--mode")
                if value is not None:
                    mode = value
                    mode_explicit = True
            elif arg.startswith("--link-limit="):
                value = arg.split("=", 1)[1]
                try:
                    link_limit = max(1, int(value))
                except ValueError:
                    messages.append(
                        f"Invalid value '{value}' for --link-limit; using {link_limit}."
                    )
            elif arg == "--link-limit":
                value = _consume_value("--link-limit")
                if value is not None:
                    try:
                        link_limit = max(1, int(value))
                    except ValueError:
                        messages.append(
                            f"Invalid value '{value}' for --link-limit; using {link_limit}."
                        )
            elif arg.startswith("-"):
                unknown_args.append(arg)
            elif url is None:
                url = arg
            else:
                messages.append(f"Ignoring extra argument '{arg}'.")
            index += 1

        if not url:
            url = default_url

        def _normalize_url(raw: str) -> Optional[str]:
            candidate = raw.strip()
            if not candidate:
                messages.append("No URL provided; using default example crawl.")
                return default_url
            parsed = urlparse(candidate)
            if not parsed.scheme:
                candidate = f"https://{candidate}"
                parsed = urlparse(candidate)
                messages.append(f"Interpreting URL as {candidate}.")
            if parsed.scheme not in {"http", "https"}:
                messages.append(
                    f"Unsupported URL scheme '{parsed.scheme}'. Only http/https are allowed."
                )
                return None
            if not parsed.netloc:
                messages.append(f"Invalid URL '{raw}'.")
                return None
            return candidate

        normalized_url = _normalize_url(url)
        if not normalized_url:
            return {
                "output": "\n".join(messages) or "Unable to interpret the provided URL.",
                "type": "text",
            }

        mode_aliases = {
            "markdown": "markdown",
            "md": "markdown",
            "clean-html": "clean-html",
            "clean": "clean-html",
            "html": "clean-html",
            "links": "links",
            "link": "links",
        }
        normalized_mode = mode_aliases.get(mode.lower())
        if not normalized_mode:
            valid_modes = ", ".join(sorted(set(mode_aliases.values())))
            return {
                "output": (
                    f"Unknown mode '{mode}'. Supported modes: {valid_modes}."
                ),
                "type": "text",
            }

        fallback_to_simulator = False
        if not CRAWL4AI_AVAILABLE and not simulate:
            fallback_to_simulator = True
            simulate = True
            messages.append(
                "crawl4ai package is not installed – using the local simulator instead."
            )

        if simulate:
            job = crawl4ai_simulator.start_job(
                normalized_url, profile=profile, fail=fail, launched_by="terminal"
            )
            message_lines = []
            if fallback_to_simulator and mode_explicit:
                message_lines.append(
                    "Real Crawl4AI output modes are unavailable without the package."
                )
            message_lines.extend(messages)
            if unknown_args:
                message_lines.append(
                    "Ignored unsupported option(s): " + ", ".join(sorted(unknown_args))
                )
            message_lines.append(
                f"Queued Crawl4AI job #{job['id']} for {job['url']} (profile={profile})"
            )
            if fail:
                message_lines.append(
                    "Failure simulation enabled – watch the Crawl4AI error logs."
                )
            return {"output": "\n".join(filter(None, message_lines)), "type": "text"}

        result = None
        if AsyncWebCrawler is not None:

            def _run_crawl() -> Any:
                async def _crawl_async():
                    crawler = AsyncWebCrawler()
                    try:
                        try:
                            await crawler.start()
                        except Exception as start_exc:
                            raise RuntimeError("__crawler_init__") from start_exc

                        config_kwargs: Dict[str, Any] = {"verbose": False, "log_console": False}
                        if CacheMode is not None:
                            config_kwargs["cache_mode"] = CacheMode.BYPASS
                        config = (
                            CrawlerRunConfig(**config_kwargs)
                            if CrawlerRunConfig is not None
                            else None
                        )
                        if config is not None:
                            return await crawler.arun(url=normalized_url, config=config)
                        return await crawler.arun(url=normalized_url)
                    finally:
                        with contextlib.suppress(Exception):
                            await crawler.close()

                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(_crawl_async())
                finally:
                    try:
                        loop.run_until_complete(loop.shutdown_asyncgens())
                    finally:
                        asyncio.set_event_loop(None)
                        loop.close()

            try:
                result = _run_crawl()
            except RuntimeError as exc:  # pragma: no cover - optional dependency path
                root_cause = exc.__cause__ or exc
                if exc.args and exc.args[0] == "__crawler_init__":
                    logger.exception("Failed to initialize AsyncWebCrawler", exc_info=root_cause)
                    python_cmd = (
                        f"{sys.executable} -m playwright install"
                        if sys.executable
                        else "python -m playwright install"
                    )
                    lines = messages + [
                        "Unable to initialize Crawl4AI AsyncWebCrawler.",
                        " Optional browser dependencies appear to be missing.",
                        " Install the Playwright browsers by running:",
                        f"   {python_cmd}",
                        " If the command is not available, install Playwright first with `pip install playwright`.",
                        f"Error: {root_cause}",
                    ]
                else:
                    logger.exception("Crawl4AI AsyncWebCrawler run failed", exc_info=root_cause)
                    lines = messages + [
                        f"Crawl4AI AsyncWebCrawler failed to crawl {normalized_url}: {root_cause}",
                    ]
                return {"output": "\n".join(filter(None, lines)), "type": "text"}
            except Exception as exc:  # pragma: no cover - optional dependency path
                logger.exception("Crawl4AI AsyncWebCrawler run failed", exc_info=exc)
                lines = messages + [
                    f"Crawl4AI AsyncWebCrawler failed to crawl {normalized_url}: {exc}",
                ]
                return {"output": "\n".join(filter(None, lines)), "type": "text"}
        elif WebCrawler is not None:
            try:
                crawler = WebCrawler(always_by_pass_cache=True, verbose=False)
            except Exception as exc:  # pragma: no cover - optional dependency path
                logger.exception("Failed to initialize WebCrawler", exc_info=exc)
                python_cmd = (
                    f"{sys.executable} -m playwright install"
                    if sys.executable
                    else "python -m playwright install"
                )
                lines = messages + [
                    "Unable to initialize Crawl4AI WebCrawler.",
                    " Optional browser dependencies appear to be missing.",
                    " Install the Playwright browsers by running:",
                    f"   {python_cmd}",
                    " If the command is not available, install Playwright first with `pip install playwright`.",
                    f"Error: {exc}",
                ]
                return {"output": "\n".join(filter(None, lines)), "type": "text"}

            try:
                result = crawler.run(
                    normalized_url,
                    warmup=False,
                    verbose=False,
                )
            except Exception as exc:  # pragma: no cover - optional dependency path
                logger.exception("Crawl4AI run failed", exc_info=exc)
                lines = messages + [
                    f"Crawl4AI failed to crawl {normalized_url}: {exc}",
                ]
                return {"output": "\n".join(filter(None, lines)), "type": "text"}
        else:
            lines = messages + [
                "Crawl4AI runtime is unavailable. Install crawl4ai to enable live crawling.",
            ]
            return {"output": "\n".join(filter(None, lines)), "type": "text"}

        if result is None or not getattr(result, "success", False):
            failure_reason = getattr(result, "error_message", None) or "unknown error"
            lines = messages + [
                f"Crawl4AI did not return content for {normalized_url}: {failure_reason}"
            ]
            return {"output": "\n".join(filter(None, lines)), "type": "text"}

        def _truncate(text: str, limit: int = 4000) -> str:
            if len(text) <= limit:
                return text
            trimmed = text[:limit]
            return (
                f"{trimmed}\n… output truncated (remaining {len(text) - limit} characters)."
            )

        def _format_markdown() -> str:
            markdown = getattr(result, "markdown", None)
            if markdown:
                return _truncate(str(markdown).strip()) or "(Markdown response was empty.)"
            cleaned_html = getattr(result, "cleaned_html", None) or ""
            if cleaned_html:
                return _truncate(cleaned_html)
            html = getattr(result, "html", "")
            return _truncate(html) if html else "(No content returned.)"

        def _normalize_links_data(raw_links: Any) -> Dict[str, List[Dict[str, Any]]]:
            if raw_links is None:
                return {}
            if hasattr(raw_links, "model_dump"):
                raw_links = raw_links.model_dump()
            normalized: Dict[str, List[Dict[str, Any]]] = {}
            if isinstance(raw_links, dict):
                for key, values in raw_links.items():
                    normalized[key] = []
                    for item in values or []:
                        if hasattr(item, "model_dump"):
                            normalized[key].append(item.model_dump())
                        elif isinstance(item, dict):
                            normalized[key].append(item)
                        else:
                            normalized[key].append({"text": str(item)})
            return normalized

        def _format_links() -> str:
            links_data = _normalize_links_data(getattr(result, "links", None))
            if not links_data:
                return "No links were extracted from the page."
            lines: List[str] = []
            for category in ("internal", "external"):
                entries = links_data.get(category) or []
                if not entries:
                    continue
                lines.append(f"{category.capitalize()} links ({len(entries)} total):")
                for entry in entries[:link_limit]:
                    href = entry.get("href") or entry.get("url") or "—"
                    text_value = entry.get("text") or entry.get("title") or href
                    text_value = (text_value or "").strip() or "(no text)"
                    lines.append(f"  • {text_value} -> {href}")
                remaining = len(entries) - link_limit
                if remaining > 0:
                    lines.append(f"  … {remaining} more")
            if not lines:
                return "No links were extracted from the page."
            return _truncate("\n".join(lines))

        def _format_clean_html() -> str:
            cleaned_html = getattr(result, "cleaned_html", None)
            if cleaned_html:
                return _truncate(cleaned_html)
            html = getattr(result, "html", "")
            return _truncate(html) if html else "(No HTML content returned.)"

        formatter = {
            "markdown": _format_markdown,
            "clean-html": _format_clean_html,
            "links": _format_links,
        }[normalized_mode]

        header_lines = [
            f"Crawl4AI {normalized_mode.replace('-', ' ')} output for {normalized_url}",
        ]
        title = None
        metadata = getattr(result, "metadata", None)
        if isinstance(metadata, dict):
            title = metadata.get("title") or metadata.get("og:title")
        if title:
            header_lines.append(f"Title: {title}")
        redirected = getattr(result, "redirected_url", None)
        if redirected and redirected != normalized_url:
            header_lines.append(f"Redirected to: {redirected}")

        content = formatter()
        lines = messages + [
            "Ignored unsupported option(s): " + ", ".join(sorted(unknown_args))
            if unknown_args
            else "",
            "\n".join(header_lines),
            "",
            content,
        ]
        return {"output": "\n".join(filter(None, lines)), "type": "text"}

    console.add_custom_command(
        "crawl4ai-run",
        crawl4ai_run_command,
        "Run Crawl4AI for a URL (use --mode for output or --simulate to queue)",
    )

    def crawl4ai_jobs_command(args: List[str]) -> Dict[str, Any]:
        """Show a snapshot of Crawl4AI jobs."""

        limit = 5
        if args and args[0].isdigit():
            limit = max(1, int(args[0]))
        jobs = crawl4ai_simulator.list_jobs()[:limit]
        metrics = crawl4ai_simulator.stats()
        header = (
            "Crawl4AI Job Snapshot\n"
            f"Total: {metrics['total_jobs']} • Active: {metrics['active']} • "
            f"Queued: {metrics['queued']} • Completed: {metrics['completed']} • "
            f"Failed: {metrics['failed']}"
        )
        if not jobs:
            return {"output": header + "\nNo jobs have been queued yet.", "type": "text"}
        lines = [header, ""]
        for job in jobs:
            line = (
                f"#{job['id']} [{job['status'].upper()}] {job['url']}"
                f" • {job['progress']}% • pages={job['pages_scraped']}"
                f" • items={job['items_extracted']}"
            )
            if job.get("error"):
                line += f" • ERROR: {job['error']}"
            lines.append(line)
        return {"output": "\n".join(lines), "type": "text"}

    console.add_custom_command(
        "crawl4ai-jobs",
        crawl4ai_jobs_command,
        "Show the most recent Crawl4AI jobs and their progress",
    )

    def crawl4ai_errors_command(args: List[str]) -> Dict[str, Any]:
        """Display recent Crawl4AI error logs."""

        limit = 5
        if args and args[0].isdigit():
            limit = max(1, int(args[0]))
        errors = crawl4ai_simulator.get_recent_errors(limit)
        if not errors:
            return {"output": "No Crawl4AI errors recorded.", "type": "warning"}
        lines = ["Recent Crawl4AI errors:"]
        for entry in errors:
            lines.append(
                f"[{entry['timestamp']}] job {entry.get('job_id', '—')} – {entry['message']}"
            )
        return {"output": "\n".join(lines), "type": "error"}

    console.add_custom_command(
        "crawl4ai-errors",
        crawl4ai_errors_command,
        "Tail the Crawl4AI error log stream",
    )

    def crawl4ai_diagnose_command(args: List[str]) -> Dict[str, Any]:
        """Emit a diagnostic Crawl4AI error for testing."""

        message = " ".join(args).strip() or "Manual diagnostic error triggered from terminal"
        entry = crawl4ai_simulator.log_manual_error(message)
        output = f"Logged synthetic error at {entry['timestamp']}: {entry['message']}"
        return {"output": output, "type": "error"}

    console.add_custom_command(
        "crawl4ai-diagnose",
        crawl4ai_diagnose_command,
        "Generate a synthetic Crawl4AI error entry",
    )


# ----------------------------------------------------------------------
# Flask routes
# ----------------------------------------------------------------------
@app.route("/")
def home():
    """Main dashboard page with live Crawl4AI metrics."""

    crawl4ai_simulator.ensure_bootstrap_jobs()

    console_base_url = console.config.get("CON5013_URL_PREFIX", "/con5013") or "/con5013"
    if not console_base_url.startswith("/"):
        console_base_url = f"/{console_base_url}"
    if console_base_url != "/" and console_base_url.endswith("/"):
        console_base_url = console_base_url.rstrip("/")
    return render_template_string(
        """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Crawl4AI + Con5013 Deep Integration</title>
        <style>
            body {
                font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background: radial-gradient(circle at 0% 0%, rgba(56, 189, 248, 0.25), transparent 60%),
                            radial-gradient(circle at 80% 0%, rgba(244, 63, 94, 0.35), transparent 55%),
                            radial-gradient(circle at 50% 100%, rgba(99, 102, 241, 0.3), transparent 60%),
                            #0f172a;
                color: #f8fafc;
                min-height: 100vh;
            }
            a { color: inherit; }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 24px 120px;
            }
            .hero {
                display: grid;
                gap: 24px;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                align-items: stretch;
                margin-bottom: 48px;
            }
            .panel {
                background: rgba(15, 23, 42, 0.75);
                border: 1px solid rgba(148, 163, 184, 0.12);
                border-radius: 20px;
                padding: 24px;
                box-shadow: 0 24px 60px rgba(15, 23, 42, 0.4);
                backdrop-filter: blur(16px);
            }
            .panel h1 {
                margin: 0 0 16px;
                font-size: 2rem;
                line-height: 1.2;
                letter-spacing: 0.02em;
            }
            .panel p { color: rgba(226, 232, 240, 0.8); line-height: 1.6; }
            .crawl-demo {
                margin-top: 28px;
                padding: 20px;
                background: rgba(15, 23, 42, 0.55);
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 16px;
                display: flex;
                flex-direction: column;
                gap: 16px;
            }
            .crawl-demo h2 {
                margin: 0;
                font-size: 1.4rem;
                letter-spacing: 0.01em;
            }
            .crawl-demo-form {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .crawl-demo-inputs {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
            }
            .crawl-demo-inputs input[type="url"] {
                flex: 1 1 240px;
                min-width: 200px;
                padding: 12px 16px;
                border-radius: 12px;
                border: 1px solid rgba(148, 163, 184, 0.25);
                background: rgba(15, 23, 42, 0.8);
                color: #f8fafc;
                font-size: 1rem;
                transition: border-color 0.2s ease, box-shadow 0.2s ease;
            }
            .crawl-demo-inputs input[type="url"]:focus {
                outline: none;
                border-color: rgba(94, 234, 212, 0.6);
                box-shadow: 0 0 0 2px rgba(94, 234, 212, 0.2);
            }
            .crawl-demo-inputs select {
                flex: 0 0 auto;
                min-width: 160px;
                padding: 12px 16px;
                border-radius: 12px;
                border: 1px solid rgba(148, 163, 184, 0.25);
                background: rgba(15, 23, 42, 0.8);
                color: #e2e8f0;
                font-size: 0.95rem;
            }
            .crawl-demo-inputs .btn {
                flex: 0 0 auto;
                white-space: nowrap;
            }
            .crawl-demo-hint {
                margin: 0;
                font-size: 0.9rem;
                color: rgba(148, 163, 184, 0.85);
            }
            .crawl-demo-feedback {
                margin: 0;
                font-size: 0.95rem;
                border-radius: 12px;
                padding: 12px 16px;
                background: rgba(148, 163, 184, 0.12);
                color: #e2e8f0;
                display: none;
            }
            .crawl-demo-feedback.active { display: block; }
            .crawl-demo-feedback.info { background: rgba(56, 189, 248, 0.18); color: #e0f2fe; }
            .crawl-demo-feedback.success { background: rgba(34, 197, 94, 0.2); color: #dcfce7; }
            .crawl-demo-feedback.warning { background: rgba(234, 179, 8, 0.2); color: #fef3c7; }
            .crawl-demo-feedback.error { background: rgba(248, 113, 113, 0.22); color: #fee2e2; }
            .availability {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                font-weight: 600;
                color: {{ 'limegreen' if crawl4ai_available else '#f87171' }};
            }
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 16px;
                margin-top: 16px;
            }
            .metric-card {
                background: rgba(30, 41, 59, 0.85);
                border: 1px solid rgba(148, 163, 184, 0.16);
                border-radius: 16px;
                padding: 18px;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .metric-label { color: rgba(148, 163, 184, 0.85); font-size: 0.9rem; }
            .metric-value { font-size: 2rem; font-weight: 700; }
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
                gap: 20px;
                margin-top: 24px;
            }
            .feature-card {
                background: rgba(15, 23, 42, 0.65);
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 16px;
                padding: 20px;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .feature-card h3 { margin: 0; font-size: 1.3rem; }
            .btn {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 12px 18px;
                border-radius: 999px;
                border: none;
                background: linear-gradient(135deg, #38bdf8, #6366f1);
                color: #0f172a;
                font-weight: 600;
                text-decoration: none;
                cursor: pointer;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 16px 30px rgba(14, 116, 144, 0.35);
            }
            .terminal-hints {
                margin-top: 32px;
                background: rgba(15, 23, 42, 0.6);
                border-radius: 16px;
                border: 1px solid rgba(148, 163, 184, 0.16);
                padding: 20px;
            }
            code {
                background: rgba(15, 23, 42, 0.8);
                padding: 4px 8px;
                border-radius: 8px;
                font-size: 0.95rem;
            }
            .terminal-hints ul { margin: 12px 0 0 18px; }
            .terminal-hints li { margin-bottom: 8px; }
            .console-hint {
                margin-top: 28px;
                text-align: center;
                background: rgba(15, 23, 42, 0.7);
                border-radius: 16px;
                border: 1px solid rgba(148, 163, 184, 0.14);
                padding: 18px;
            }
            .console-hint strong { color: #facc15; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="hero">
                <div class="panel">
                    <h1>🕷️ Crawl4AI + Con5013</h1>
                    <p>
                        Explore a production-style integration between <strong>Crawl4AI</strong> and
                        the <strong>Con5013</strong> console. Queue crawls, watch system metrics,
                        and tail failure diagnostics in real time without leaving your browser.
                    </p>
                    <p class="availability">
                        <span>•</span>
                        <span>Crawl4AI package {{ 'detected' if crawl4ai_available else 'not installed' }}</span>
                    </p>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <span class="metric-label">Active Jobs</span>
                            <span class="metric-value" id="metric-active">0</span>
                        </div>
                        <div class="metric-card">
                            <span class="metric-label">Completed</span>
                            <span class="metric-value" id="metric-completed">0</span>
                        </div>
                        <div class="metric-card">
                            <span class="metric-label">Failed</span>
                            <span class="metric-value" id="metric-failed">0</span>
                        </div>
                        <div class="metric-card">
                            <span class="metric-label">Success Rate</span>
                            <span class="metric-value" id="metric-success">0%</span>
                        </div>
                    </div>
                    <div class="crawl-demo">
                        <h2>Instant Crawl Demo</h2>
                        <p class="crawl-demo-hint">Paste a URL and let Con5013 launch Crawl4AI for an LLM-ready summary.</p>
                        <form id="crawl-demo-form" class="crawl-demo-form">
                            <div class="crawl-demo-inputs">
                                <input id="crawl-demo-url" type="url" name="url" placeholder="https://example.com/article" autocomplete="url" required>
                                <select id="crawl-demo-mode" name="mode" aria-label="Crawl output mode">
                                    <option value="markdown" selected>LLM markdown</option>
                                    <option value="clean-html">Clean HTML</option>
                                    <option value="links">Link summary</option>
                                </select>
                                <button type="submit" class="btn">Crawl with Con5013</button>
                            </div>
                            <p class="crawl-demo-hint">Tip: We'll open the terminal tab and run <code>crawl4ai-run</code> for you.</p>
                            <p id="crawl-demo-feedback" class="crawl-demo-feedback" role="status" aria-live="polite"></p>
                        </form>
                    </div>
                </div>
                <div class="panel">
                    <h2>Real-time Actions</h2>
                    <div class="features">
                        <div class="feature-card">
                            <h3>🚀 Queue Crawl</h3>
                            <p>Hit the API to create a new Crawl4AI job and monitor its lifecycle instantly.</p>
                            <a href="/api/scrape/start" class="btn">Start job</a>
                        </div>
                        <div class="feature-card">
                            <h3>💥 Simulate Failure</h3>
                            <p>Trigger a failing crawl to populate the Crawl4AI error stream showcased in Con5013 logs.</p>
                            <a href="/api/scrape/start?fail=1" class="btn">Start failing job</a>
                        </div>
                        <div class="feature-card">
                            <h3>📋 Inspect Jobs</h3>
                            <p>Review live job snapshots, throughput metrics, and error history.</p>
                            <a href="/api/scrape/jobs" class="btn">API: /api/scrape/jobs</a>
                        </div>
                        <div class="feature-card">
                            <h3>🧪 Diagnostics</h3>
                            <p>Fire a synthetic error log to watch the console respond instantly.</p>
                            <a href="/api/crawl4ai/simulate-error" class="btn">Emit error log</a>
                        </div>
                    </div>
                </div>
            </div>

            <div class="terminal-hints panel">
                <h2>Terminal Playground</h2>
                <p>Open the Con5013 terminal and try these Crawl4AI-aware commands:</p>
                <ul>
                    <li><code>crawl4ai-run https://example.org/news --mode markdown --profile headlines</code></li>
                    <li><code>crawl4ai-run --simulate --fail</code> &mdash; queues a job that will fail for log testing.</li>
                    <li><code>crawl4ai-jobs 5</code> to stream the latest job statuses.</li>
                    <li><code>crawl4ai-errors</code> to tail the error channel that powers the Logs tab.</li>
                    <li><code>crawl4ai-diagnose Pipeline hiccup</code> to emit a synthetic diagnostic.</li>
                </ul>
                <p class="crawl-demo-hint">Prefer clicks? The instant crawl demo above fills and runs the same terminal command for you.</p>
            </div>

            <div class="console-hint">
                <p><strong>Press {{ con5013_config.get('CON5013_HOTKEY', 'Alt+C') }}</strong> to launch the Con5013 overlay anywhere.</p>
                <p>The Logs tab is pinned to <strong>Crawl4AI</strong> and filtered to <em>error</em> entries so that operational issues surface immediately.</p>
                <p>Need the full console? Visit the <a href="{{ console_base_url }}" style="color:#38bdf8; text-decoration:underline;">dedicated Con5013 dashboard</a>.</p>
            </div>
        </div>

        {{ con5013_console_html() | safe }}

        <script>
            window.CON5013_BOOTSTRAP = {{ con5013_config | tojson }};
        </script>

        <script>
            async function refreshMetrics() {
                try {
                    const response = await fetch('/api/crawl4ai/metrics');
                    const data = await response.json();
                    if (data.status === 'success') {
                        const stats = data.metrics;
                        document.getElementById('metric-active').textContent = stats.active;
                        document.getElementById('metric-completed').textContent = stats.completed;
                        document.getElementById('metric-failed').textContent = stats.failed;
                        document.getElementById('metric-success').textContent = `${stats.success_rate.toFixed(1)}%`;
                    }
                } catch (error) {
                    console.warn('Metric refresh failed', error);
                }
            }
            refreshMetrics();
            setInterval(refreshMetrics, 4000);
        </script>

        <script>
            document.addEventListener('DOMContentLoaded', () => {
                const form = document.getElementById('crawl-demo-form');
                const urlInput = document.getElementById('crawl-demo-url');
                const modeSelect = document.getElementById('crawl-demo-mode');
                const feedbackEl = document.getElementById('crawl-demo-feedback');

                let overlayReady = false;
                let logsPinned = false;

                const setFeedback = (message, status = 'info') => {
                    if (!feedbackEl) {
                        return;
                    }
                    feedbackEl.textContent = message || '';
                    feedbackEl.className = `crawl-demo-feedback ${status} ${message ? 'active' : ''}`.trim();
                };

                const ensureOverlay = () => {
                    if (!window.con5013Overlay || typeof window.con5013Overlay.refreshLogs !== 'function') {
                        return null;
                    }
                    return window.con5013Overlay;
                };

                const runCrawlFromForm = (overlay, normalizedUrl, modeValue) => {
                    if (!overlay) {
                        return false;
                    }

                    if (typeof overlay.open === 'function') {
                        overlay.open();
                    }

                    if (typeof overlay.switchPanel === 'function') {
                        overlay.switchPanel('terminal');
                    } else {
                        const terminalTab = document.querySelector('[data-panel="terminal"]');
                        terminalTab?.click();
                    }

                    const terminalInput = document.getElementById('terminalInput');
                    if (!terminalInput) {
                        setFeedback('Terminal input is still loading. Open the console manually and try again.', 'error');
                        return false;
                    }

                    const command = `crawl4ai-run ${JSON.stringify(normalizedUrl)} --mode ${modeValue || 'markdown'}`;
                    terminalInput.value = command;

                    if (typeof overlay.executeCommand === 'function') {
                        overlay.executeCommand();
                    } else {
                        terminalInput.dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter' }));
                    }

                    terminalInput.focus();
                    return true;
                };

                const tryHookOverlay = () => {
                    const overlay = ensureOverlay();
                    if (!overlay) {
                        return false;
                    }

                    if (!logsPinned) {
                        const errorLevel = 'ERROR';
                        overlay.currentSource = 'crawl4ai';
                        overlay.refreshLogs = async function () {
                            try {
                                const response = await fetch(`${this.config.CON5013_URL_PREFIX}/api/logs?source=${encodeURIComponent(this.currentSource)}&level=${errorLevel}`);
                                const data = await response.json();
                                const container = document.getElementById('logContainer');
                                if (!container) {
                                    return;
                                }
                                container.innerHTML = '';
                                if (data.status === 'success' && Array.isArray(data.logs) && data.logs.length) {
                                    data.logs.forEach((log) => {
                                        const entry = document.createElement('div');
                                        entry.className = 'log-entry error';
                                        const ts = log.timestamp ? new Date(log.timestamp * 1000).toLocaleTimeString() : '';
                                        entry.textContent = `${ts} [${(log.level || 'ERROR').toUpperCase()}] ${log.message}`;
                                        container.appendChild(entry);
                                    });
                                } else {
                                    const empty = document.createElement('div');
                                    empty.className = 'log-entry info';
                                    empty.textContent = 'No Crawl4AI errors detected. Trigger a failing job to populate this view.';
                                    container.appendChild(empty);
                                }
                                container.scrollTop = container.scrollHeight;
                            } catch (error) {
                                console.error('Failed to refresh Crawl4AI logs', error);
                            }
                        };

                        const sourceSelect = document.getElementById('logSourceSel');
                        if (sourceSelect && !sourceSelect.dataset.crawl4aiPinned) {
                            const enforceSelection = () => {
                                const options = Array.from(sourceSelect.options || []);
                                const hasCrawl4AI = options.some((option) => option.value === 'crawl4ai');
                                if (hasCrawl4AI) {
                                    sourceSelect.value = 'crawl4ai';
                                    overlay.currentSource = 'crawl4ai';
                                }
                            };
                            enforceSelection();
                            const observer = new MutationObserver(enforceSelection);
                            observer.observe(sourceSelect, { childList: true });
                            sourceSelect.addEventListener('change', () => {
                                sourceSelect.value = 'crawl4ai';
                                overlay.currentSource = 'crawl4ai';
                                overlay.refreshLogs();
                            });
                            sourceSelect.dataset.crawl4aiPinned = 'true';
                        }

                        overlay.refreshLogs();
                        logsPinned = true;
                    }

                    overlayReady = true;
                    return true;
                };

                if (!tryHookOverlay()) {
                    const interval = setInterval(() => {
                        if (tryHookOverlay()) {
                            clearInterval(interval);
                        }
                    }, 250);
                }

                if (form) {
                    form.addEventListener('submit', (event) => {
                        event.preventDefault();
                        const rawUrl = urlInput ? urlInput.value.trim() : '';
                        if (!rawUrl) {
                            setFeedback('Enter a URL to crawl.', 'warning');
                            urlInput?.focus();
                            return;
                        }

                        const normalizedUrl = /^https?:\/\//i.test(rawUrl) ? rawUrl : `https://${rawUrl}`;
                        const modeValue = modeSelect ? modeSelect.value : 'markdown';

                        if (!overlayReady) {
                            setFeedback('Initializing the Con5013 console… please retry in a moment.', 'warning');
                            tryHookOverlay();
                            return;
                        }

                        setFeedback(`Launching crawl for ${normalizedUrl}. Watch the terminal for output.`, 'info');
                        const overlay = ensureOverlay();
                        const executed = runCrawlFromForm(overlay, normalizedUrl, modeValue);
                        if (executed) {
                            setFeedback(`Sent crawl4ai-run for ${normalizedUrl}. Check the Con5013 terminal for the LLM-friendly output.`, 'success');
                        }
                    });
                }
            });
        </script>
    </body>
    </html>
        """,
        crawl4ai_available=CRAWL4AI_AVAILABLE,
        con5013_config=console.config,
        console_base_url=console_base_url,
    )


@app.route("/api/scrape/start", methods=["GET", "POST"])
def start_scraping_job():
    """Start a new Crawl4AI scraping job."""

    payload = request.get_json(silent=True) or {}
    url = payload.get("url") or request.args.get("url") or "https://example.com/articles"
    profile = payload.get("profile") or request.args.get("profile") or "default"
    fail = _bool_from_request(payload.get("fail") or request.args.get("fail"))

    job = crawl4ai_simulator.start_job(
        url,
        profile=profile,
        fail=fail,
        launched_by="api",
    )

    message = f"Crawl4AI job #{job['id']} queued for {job['url']}"
    if fail:
        message += " (failure simulation enabled)"

    return jsonify(
        {
            "success": True,
            "message": message,
            "job": job,
            "metrics": crawl4ai_simulator.stats(),
            "note": "Pass fail=true to simulate an extraction failure and emit error logs.",
        }
    )


@app.route("/api/scrape/jobs")
def get_scraping_jobs():
    """Get the list of Crawl4AI jobs."""

    return jsonify(
        {
            "success": True,
            "jobs": crawl4ai_simulator.list_jobs(),
            "metrics": crawl4ai_simulator.stats(),
        }
    )


@app.route("/api/scrape/<int:job_id>")
def get_scraping_job(job_id: int):
    """Get details for a single job."""

    job = crawl4ai_simulator.get_job(job_id)
    if not job:
        return jsonify({"success": False, "message": "Job not found"}), 404
    return jsonify({"success": True, "job": job})


@app.route("/api/scrape/errors")
def get_scraping_errors():
    """Return recent Crawl4AI errors."""

    limit = int(request.args.get("limit", 10))
    return jsonify(
        {
            "success": True,
            "errors": crawl4ai_simulator.get_recent_errors(limit),
        }
    )


@app.route("/api/crawl4ai/metrics")
def crawl4ai_metrics():
    """Return aggregated Crawl4AI metrics for dashboards."""

    return jsonify(
        {
            "status": "success",
            "metrics": crawl4ai_simulator.stats(),
            "recent_errors": crawl4ai_simulator.get_recent_errors(5),
        }
    )


@app.route("/api/crawl4ai/simulate-error", methods=["GET", "POST"])
def crawl4ai_simulate_error():
    """Emit a manual Crawl4AI error log entry."""

    payload = request.get_json(silent=True) or {}
    message = (
        payload.get("message")
        or request.args.get("message")
        or "Synthetic Crawl4AI error generated via /api/crawl4ai/simulate-error"
    )
    entry = crawl4ai_simulator.log_manual_error(message)
    return jsonify(
        {
            "success": True,
            "error": entry,
            "metrics": crawl4ai_simulator.stats(),
        }
    )


@app.route("/api/test/crawl4ai")
def test_crawl4ai():
    """Test Crawl4AI integration availability."""

    if CRAWL4AI_AVAILABLE:
        runtime_class = AsyncWebCrawler or WebCrawler
        runtime_note = (
            "Use AsyncWebCrawler() within an asyncio event loop to run actual crawls in production."
            if AsyncWebCrawler is not None
            else "Instantiate WebCrawler() to run actual crawls in production."
        )
        return jsonify(
            {
                "success": True,
                "message": "Crawl4AI package detected.",
                "details": {
                    "runtime_class": f"{runtime_class.__module__}.{runtime_class.__name__}",
                    "note": runtime_note,
                },
                "metrics": crawl4ai_simulator.stats(),
            }
        )

    return jsonify(
        {
            "success": False,
            "message": "Crawl4AI not installed. Install with: pip install crawl4ai",
            "note": "This demo ships with an in-memory simulator so you can explore the Con5013 integration immediately.",
            "metrics": crawl4ai_simulator.stats(),
        }
    )


if __name__ == "__main__":
    print("🚀 Starting Crawl4AI + Con5013 Deep Integration Demo")
    print("📊 Console available at: http://localhost:5000/crawl")
    print("✨ Press Alt+C for the overlay console (filtered to Crawl4AI errors)")
    print("🔍 Use /api/scrape/start?fail=1 to trigger failure logs")
    app.run(host="0.0.0.0", port=5000, debug=True)
