import argparse
import asyncio
import json
import os
import sys
import time
from typing import TypedDict

from dotenv import load_dotenv
from slack_sdk import WebClient
from tests import ALL_TESTS, QA_TESTS

from devin_api_client import DevinAPIClient, DevinAPISessionStatusResponse

# Load environment variables from .env file
load_dotenv()

# Default Slack channel for test results
SLACK_TEST_RESULTS_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "test-results")

DEVIN_API_KEY = os.getenv("DEVIN_API_KEY")
if not DEVIN_API_KEY:
    raise ValueError("DEVIN_API_KEY environment variable is required")

devin_api_client = DevinAPIClient(DEVIN_API_KEY)
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
slack_client = WebClient(token=SLACK_BOT_TOKEN)


class QATestResult(TypedDict, total=False):
    test_name: str
    session_id: str
    session_url: str
    status_enum: str
    success: bool
    message: str  # one-line summary (or the old free-text message)
    checks: list[dict]  # [{part, name, passed, details}]
    archived_cases: list[str]


MAX_TIME_PER_TEST = 60 * 60  # 60 minutes (combined tests run two parts on one case)
PROGRESS_INTERVAL = int(os.getenv("QA_PROGRESS_MINUTES", "1")) * 60
# Devin statuses after which the session won't do more work on its own.
DONE_STATUSES = {"blocked", "stopped", "finished", "expired"}

# Passed when creating each session so Devin gets its structured-output tool.
QA_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean", "description": "true only if every CHECK passed"},
        "summary": {"type": "string", "description": "One short sentence, max 150 characters"},
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "part": {"type": "string", "description": "Test name of the part (combined sessions), else empty"},
                    "name": {"type": "string", "description": "What was checked, max 60 characters"},
                    "passed": {"type": "boolean"},
                    "details": {"type": "string", "description": "If failed: what happened, max 150 characters; else empty"},
                },
                "required": ["part", "name", "passed", "details"],
                "additionalProperties": False,
            },
        },
        "archived_cases": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["success", "summary", "checks", "archived_cases"],
    "additionalProperties": False,
}


def result_from_messages(status: dict) -> dict | None:
    """Fallback: find a {"success": ..., "message": ...} JSON object Devin wrote in the chat."""
    decoder = json.JSONDecoder()
    for m in reversed(status.get("messages") or []):
        text = m.get("message") or ""
        if "user" in (m.get("type") or "") or '"success"' not in text:
            continue
        for i in [i for i, ch in enumerate(text) if ch == "{"]:
            try:
                obj, _ = decoder.raw_decode(text, i)
            except ValueError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("success"), bool):
                return obj
    return None


# Latest state per test, written by poll_session_and_eval, read by log_progress.
progress: dict[str, dict] = {}


def last_devin_message(status: dict) -> str:
    """Latest message Devin wrote in the session (skips the user's messages)."""
    for m in reversed(status.get("messages") or []):
        if "user" not in (m.get("type") or "") and m.get("message"):
            return " ".join(m["message"].split())
    return ""


async def log_progress(session_links: list[tuple[str, str, str]]) -> None:
    """Every PROGRESS_INTERVAL, log each session's status and Devin's latest message."""
    start = time.time()
    while True:
        await asyncio.sleep(PROGRESS_INTERVAL)
        lines = [f"=== QA progress after {int((time.time() - start) / 60)} min ==="]
        for _, session_url, test_name in session_links:
            p = progress.get(test_name, {})
            if "success" in p:
                state = "PASSED" if p["success"] else "FAILED"
            else:
                state = p.get("status") or "starting"
            line = f"[{state}] {test_name} ({session_url})"
            if p.get("last_message") and "success" not in p:
                msg = p["last_message"]
                line += f"\n    Devin: {msg[:300]}{'...' if len(msg) > 300 else ''}"
            lines.append(line)
        print("\n".join(lines), flush=True)

# Per-environment names of the Devin secrets (app.devin.ai/secrets) holding the
# HTTP basic auth (username:password), the External API key and the app login.
ENVIRONMENTS = {
    "dev": {
        "basic_auth_secret": "DEV_BASIC_AUTH",
        "api_key_secret": "SKY_API_KEY_DEV",
        "user_email_secret": "DEV_USER_EMAIL",
        "user_password_secret": "DEV_USER_PASSWORD",
    },
    "staging": {
        "basic_auth_secret": "STAGING_BASIC_AUTH",
        "api_key_secret": "SKY_API_KEY_STAGING",
        "user_email_secret": "STAGING_USER_EMAIL",
        "user_password_secret": "STAGING_USER_PASSWORD",
    },
}


async def poll_session_and_eval(
    test_name: str, session_id: str, session_url: str
) -> QATestResult:
    status = None
    start_time = time.time()
    while True:
        status: DevinAPISessionStatusResponse | None = (
            await devin_api_client.get_session_status(session_id)
        )
        if status:
            progress[test_name] = {
                "status": status["status_enum"] or "starting",
                "last_message": last_devin_message(status),
            }
        if (
            status
            and status["status_enum"] is not None
            and status["status_enum"].lower() in DONE_STATUSES
        ):
            break

        if time.time() - start_time > MAX_TIME_PER_TEST:
            break
        await asyncio.sleep(20)

    output = (status and status.get("structured_output")) or (status and result_from_messages(status))
    if status and not status.get("structured_output") and output:
        print(f"{test_name}: no structured output, using the JSON from Devin's chat message", flush=True)
    if not output:
        return {
            "test_name": test_name,
            "session_id": session_id,
            "session_url": session_url,
            "status_enum": (
                status["status_enum"] or "unknown" if status else "never_started"
            ),
            "success": False,
            "message": (
                f"Devin didn't report a result (session {status['status_enum'] or 'unknown'}"
                + (", timed out" if time.time() - start_time > MAX_TIME_PER_TEST else "")
                + "). Open the session to see what happened."
                if status
                else "The Devin session never started."
            ),
        }

    success: bool = output.get("success", False)
    x: QATestResult = {
        "test_name": test_name,
        "session_id": session_id,
        "session_url": session_url,
        "status_enum": status["status_enum"] or "unknown",
        "success": success,
        # "message" is the old free-text format (and what the chat fallback may find)
        "message": output.get("summary") or output.get("message", ""),
        "checks": [c for c in output.get("checks") or [] if isinstance(c, dict)],
        "archived_cases": output.get("archived_cases") or [],
    }
    print(f"Test finished: {x}", flush=True)
    progress.setdefault(test_name, {})["success"] = success
    return x


def slack_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def shorten(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def check_counts(result: QATestResult) -> str:
    checks = result.get("checks") or []
    if not checks:
        return ""
    passed = sum(1 for c in checks if c.get("passed"))
    return f"{passed}/{len(checks)} checks"


def format_summary(results: list[QATestResult], environment: str, minutes: int) -> str:
    """Top-level message: one line for the run, one line per test."""
    failed = [r for r in results if not r["success"]]
    if failed:
        headline = f"❌ {len(failed)} of {len(results)} tests failed"
    else:
        headline = f"✅ all {len(results)} tests passed"
    lines = [f"*QA {environment}* · {headline} · {minutes} min"]
    for r in results:
        icon = "✅" if r["success"] else "❌"
        line = f"{icon} <{r['session_url']}|{r['test_name']}>"
        if check_counts(r):
            line += f" · {check_counts(r)}"
        lines.append(line)
    if failed:
        lines.append("_Details for failed tests in the thread._")
    return "\n".join(lines)


def format_failure(r: QATestResult) -> str:
    """Thread reply for a failed test: only the failed checks."""
    header = f"❌ *{r['test_name']}*"
    if check_counts(r):
        header += f" · {check_counts(r)} passed"
    header += f" · <{r['session_url']}|Devin session>"
    lines = [header]
    failed_checks = [c for c in r.get("checks") or [] if not c.get("passed")]
    for c in failed_checks:
        part = f"[{c['part'].removeprefix('test-')}] " if c.get("part") else ""
        name = slack_escape(shorten(c.get("name", ""), 80))
        details = slack_escape(shorten(c.get("details", ""), 200))
        lines.append(f"• *{part}{name}*" + (f": {details}" if details else ""))
    if not failed_checks and r.get("message"):
        # No per-check data (old format, or the session never reported).
        lines.append(slack_escape(shorten(r["message"], 400)))
    if r.get("archived_cases"):
        lines.append(f"🗄 Archived {len(r['archived_cases'])} case(s)")
    return "\n".join(lines)


def post_to_slack(text: str, thread_ts: str | None = None) -> str | None:
    if not SLACK_BOT_TOKEN:
        return None
    response = slack_client.chat_postMessage(
        channel=SLACK_TEST_RESULTS_CHANNEL_ID,
        text=text,
        thread_ts=thread_ts,
        unfurl_links=False,  # no "Devin | The AI Software Engineer" preview cards
        unfurl_media=False,
    )
    return response["ts"]


async def send_final_results_to_slack(
    results: list[QATestResult], environment: str = "dev", minutes: int = 0
):
    summary = format_summary(results, environment, minutes)
    print(summary, flush=True)
    thread_ts = post_to_slack(summary)
    for r in results:
        if r["success"]:
            continue
        text = format_failure(r)
        print(text, flush=True)
        post_to_slack(text, thread_ts=thread_ts)


async def run_tests_and_send_to_slack(
    url: str,
    test_names: list[str] | None,
    external_api_specs_url: str,
    sample_pdf_url: str,
    johndoejunior_zip_url: str,
    environment: str = "dev",
) -> list[QATestResult]:
    run_start = time.time()
    eval_tasks = []
    session_links: list[tuple[str, str, str]] = []
    if test_names:
        unknown = [n for n in test_names if n not in ALL_TESTS]
        if unknown:
            raise ValueError(f"Unknown tests: {unknown}. Known: {sorted(ALL_TESTS)}")
        selected = [ALL_TESTS[n] for n in test_names]
    else:
        selected = QA_TESTS
    for test in selected:
        prompt = test["user_prompt"].format(
            url=url,
            external_api_specs_url=external_api_specs_url,
            sample_pdf_url=sample_pdf_url,
            johndoejunior_zip_url=johndoejunior_zip_url,
            **ENVIRONMENTS[environment],
        )
        session_response = await devin_api_client.start_session(
            prompt,
            title=f"QA {environment}: {test['test_name']}",
            structured_output_schema=QA_RESULT_SCHEMA,
        )
        assert session_response["session_id"] is not None
        session_id = session_response["session_id"]
        session_url = session_response["url"]

        eval_tasks.append(
            asyncio.create_task(
                poll_session_and_eval(test["test_name"], session_id, session_url)
            )
        )
        session_links.append((session_id, session_url, test["test_name"]))
        await asyncio.sleep(0.1)
    print("Done starting sessions")

    # Send initial message with session links
    links_message = f"*QA {environment}* · started {len(session_links)} Devin sessions: " + ", ".join(
        f"<{session_url}|{test_name}>" for _, session_url, test_name in session_links
    )
    print(links_message, flush=True)
    post_to_slack(links_message)

    progress_task = asyncio.create_task(log_progress(session_links))
    # Use return_exceptions=True to prevent exceptions from stopping other tasks
    results = await asyncio.gather(*eval_tasks, return_exceptions=True)
    progress_task.cancel()

    # Filter out exceptions and convert them to error results
    processed_results: list[QATestResult] = []
    for result, (session_id, session_url, test_name) in zip(results, session_links):
        if isinstance(result, Exception):
            processed_results.append(
                {
                    "test_name": test_name,
                    "session_id": session_id,
                    "session_url": session_url,
                    "status_enum": "error",
                    "success": False,
                    "message": f"Test failed with exception: {str(result)}",
                }
            )
        elif isinstance(result, dict):
            processed_results.append(QATestResult(**result))
        else:
            raise ValueError(f"Unknown result type: {type(result)}")

    await send_final_results_to_slack(
        processed_results, environment, round((time.time() - run_start) / 60)
    )
    return processed_results


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tests", type=str, help="Comma separated test names to run", default=None
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Base URL for testing",
        default="https://dev.app.sky-tech.ai/",
    )
    parser.add_argument(
        "--external-api-specs-url",
        type=str,
        help="URL for external API specs",
        default="https://dev-api.app.sky-tech.ai/external-api/docs-json",
    )
    parser.add_argument(
        "--sample-pdf-url",
        type=str,
        help="URL for sample PDF document",
        default="https://pdfobject.com/pdf/sample.pdf",
    )
    parser.add_argument(
        "--johndoejunior-zip-url",
        type=str,
        help="URL for John Doe Junior zip archive",
        default="https://dev-assets.app.sky-tech.ai/previews/John_Doe_Junior.zip",
    )
    parser.add_argument(
        "--environment",
        choices=sorted(ENVIRONMENTS),
        default="dev",
        help="Which basic auth and Devin secrets (API key, login) to use",
    )
    args = parser.parse_args()

    test_names = args.tests.split(",") if args.tests else None
    results = await run_tests_and_send_to_slack(
        url=args.url,
        test_names=test_names,
        external_api_specs_url=args.external_api_specs_url,
        sample_pdf_url=args.sample_pdf_url,
        johndoejunior_zip_url=args.johndoejunior_zip_url,
        environment=args.environment,
    )
    if not results:
        sys.exit("No tests ran")
    failed = [r["test_name"] for r in results if not r["success"]]
    if failed:
        sys.exit(f"{len(failed)}/{len(results)} QA tests failed: {', '.join(failed)}")
    print(f"All {len(results)} QA tests passed")


if __name__ == "__main__":
    asyncio.run(main())
