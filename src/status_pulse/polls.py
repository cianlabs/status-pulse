"""Status polls for external services."""

from __future__ import annotations

import errno
import json
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

GITHUB_STATUS_URL = "https://www.githubstatus.com/api/v2/status.json"
TIMEOUT_SECONDS = 10

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
    request = Request(
        GITHUB_STATUS_URL,
        headers={"User-Agent": "status-pulse", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            try:
                payload = json.load(response)
            except json.JSONDecodeError as exc:
                raise GitHubStatusBadAnswerError(
                    _bad_answer_message("the reply was not valid JSON")
                ) from exc
    except GitHubStatusError:
        raise
    except HTTPError as exc:
        raise GitHubStatusWebsiteDownError(
            _website_down_message(f"it returned HTTP {exc.code}")
        ) from exc
    except TimeoutError as exc:
        raise GitHubStatusTimeoutError(_timeout_message()) from exc
    except URLError as exc:
        raise _from_url_error(exc) from exc
    except OSError as exc:
        raise _from_os_error(exc) from exc

    return _require_status_payload(payload)


def github_is_up(payload: dict[str, Any]) -> bool:
    return payload["status"]["indicator"] == "none"


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


def _from_url_error(exc: URLError) -> GitHubStatusError:
    reason = exc.reason
    if _is_timeout(reason):
        return GitHubStatusTimeoutError(_timeout_message())
    if _is_offline(reason):
        return GitHubStatusOfflineError(_offline_message())
    detail = str(reason) if reason else str(exc)
    return GitHubStatusWebsiteDownError(_website_down_message(detail))


def _from_os_error(exc: OSError) -> GitHubStatusError:
    if _is_timeout(exc):
        return GitHubStatusTimeoutError(_timeout_message())
    if _is_offline(exc):
        return GitHubStatusOfflineError(_offline_message())
    return GitHubStatusWebsiteDownError(_website_down_message(str(exc)))


def _is_timeout(exc: BaseException | str | None) -> bool:
    return isinstance(exc, (TimeoutError, socket.timeout))


def _is_offline(exc: BaseException | str | None) -> bool:
    if isinstance(exc, socket.gaierror):
        return True
    if isinstance(exc, OSError) and exc.errno in _OFFLINE_ERRNOS:
        return True
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
