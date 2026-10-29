"""Status polls for external services."""

from __future__ import annotations

import errno
import json
import socket
import time
from typing import Any

import httpx

GITHUB_STATUS_URL = "https://www.githubstatus.com/api/v2/status.json"
TIMEOUT_SECONDS = 5
MAX_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 0.5

_OFFLINE_ERRNOS = {
    errno.ENETUNREACH,
    errno.EHOSTUNREACH,
    errno.ENETDOWN,
    errno.EHOSTDOWN,
}


class GitHubStatusError(Exception):
    """Something went wrong while checking GitHub's public status page."""


class GitHubStatusOfflineError(GitHubStatusError):
    """This computer could not get on the internet (or DNS failed)."""


class GitHubStatusWebsiteDownError(GitHubStatusError):
    """GitHub's status website did not answer like a working site."""


class GitHubStatusTimeoutError(GitHubStatusError):
    """GitHub's status website took too long to answer."""


class GitHubStatusBadAnswerError(GitHubStatusError):
    """GitHub's status website answered, but the reply was not usable."""


def fetch_github_status() -> dict[str, Any]:
    last_error: GitHubStatusError | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return _fetch_github_status_once()
        except GitHubStatusBadAnswerError:
            raise
        except GitHubStatusError as exc:
            last_error = exc
            if attempt >= MAX_ATTEMPTS:
                raise
            time.sleep(RETRY_WAIT_SECONDS)
    assert last_error is not None
    raise last_error


def github_is_up(payload: dict[str, Any]) -> bool:
    return payload["status"]["indicator"] == "none"


def github_status_message(payload: dict[str, Any]) -> str:
    if github_is_up(payload):
        return "Good news: GitHub is up right now."
    return "Heads up: GitHub is not fully up right now."


def _fetch_github_status_once() -> dict[str, Any]:
    try:
        response = httpx.get(
            GITHUB_STATUS_URL,
            headers={"User-Agent": "status-pulse", "Accept": "application/json"},
            timeout=TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubStatusWebsiteDownError(
                _website_down_message(f"it returned HTTP {exc.response.status_code}")
            ) from exc
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise GitHubStatusBadAnswerError(
                _bad_answer_message("the reply was not valid JSON")
            ) from exc
    except GitHubStatusError:
        raise
    except httpx.TimeoutException as exc:
        raise GitHubStatusTimeoutError(_timeout_message()) from exc
    except httpx.RequestError as exc:
        raise _from_request_error(exc) from exc

    return _require_status_payload(payload)


def _require_status_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise GitHubStatusBadAnswerError(
            _bad_answer_message("the reply was JSON, but not an object")
        )
    status = payload.get("status")
    if not isinstance(status, dict):
        raise GitHubStatusBadAnswerError(
            _bad_answer_message("the reply was missing a status object")
        )
    indicator = status.get("indicator")
    if not isinstance(indicator, str) or not indicator:
        raise GitHubStatusBadAnswerError(
            _bad_answer_message("the reply was missing status.indicator")
        )
    return payload


def _from_request_error(exc: httpx.RequestError) -> GitHubStatusError:
    if _is_offline(exc):
        return GitHubStatusOfflineError(_offline_message())
    return GitHubStatusWebsiteDownError(_website_down_message(str(exc)))


def _is_offline(exc: BaseException) -> bool:
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, socket.gaierror):
            return True
        if isinstance(current, OSError) and current.errno in _OFFLINE_ERRNOS:
            return True
        current = current.__cause__ or current.__context__
    return False


def _offline_message() -> str:
    return (
        f"Could not reach GitHub's status page at {GITHUB_STATUS_URL} "
        "because this computer appears to be offline (no internet, or the "
        "site name could not be looked up). Check your Wi-Fi or Ethernet, "
        "then try again."
    )


def _timeout_message() -> str:
    return (
        f"GitHub's status page at {GITHUB_STATUS_URL} was too slow and did "
        f"not answer within {TIMEOUT_SECONDS} seconds. Check whether your "
        "connection is slow, then try again."
    )


def _website_down_message(detail: str) -> str:
    return (
        f"GitHub's status page at {GITHUB_STATUS_URL} looks down ({detail}). "
        "Wait a minute and try again, or open that URL in a browser to see "
        "if the site is up."
    )


def _bad_answer_message(detail: str) -> str:
    return (
        f"GitHub's status page at {GITHUB_STATUS_URL} sent an answer Status "
        f"Pulse could not use ({detail}). Try again later, or open that URL "
        "to see what the site returned."
    )
