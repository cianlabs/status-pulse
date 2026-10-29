"""Tests for each way the GitHub status check can fail."""

from __future__ import annotations

import json
import socket
from io import BytesIO
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from status_pulse.polls import (
    GITHUB_STATUS_URL,
    GitHubStatusBadAnswerError,
    GitHubStatusOfflineError,
    GitHubStatusTimeoutError,
    GitHubStatusWebsiteDownError,
    fetch_github_status,
)


class FakeResponse:
    """Stand-in for the object urlopen() returns on a successful fetch."""

    def __init__(self, body: bytes) -> None:
        self._body = BytesIO(body)

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)


def _http_error(code: int) -> HTTPError:
    return HTTPError(GITHUB_STATUS_URL, code, "unavailable", hdrs=None, fp=None)


class FetchGitHubStatusErrorTests(TestCase):
    @patch("status_pulse.polls.urlopen")
    def test_no_internet_raises_offline_error(self, urlopen: object) -> None:
        urlopen.side_effect = URLError(socket.gaierror("nodename not known"))

        with self.assertRaises(GitHubStatusOfflineError) as caught:
            fetch_github_status()

        message = str(caught.exception)
        self.assertIn(GITHUB_STATUS_URL, message)
        self.assertIn("offline", message)
        self.assertIn("Wi-Fi or Ethernet", message)

    @patch("status_pulse.polls.urlopen")
    def test_website_down_raises_website_down_error(self, urlopen: object) -> None:
        urlopen.side_effect = _http_error(503)

        with self.assertRaises(GitHubStatusWebsiteDownError) as caught:
            fetch_github_status()

        message = str(caught.exception)
        self.assertIn(GITHUB_STATUS_URL, message)
        self.assertIn("HTTP 503", message)
        self.assertIn("browser", message)

    @patch("status_pulse.polls.urlopen")
    def test_slow_reply_raises_timeout_error(self, urlopen: object) -> None:
        urlopen.side_effect = TimeoutError()

        with self.assertRaises(GitHubStatusTimeoutError) as caught:
            fetch_github_status()

        message = str(caught.exception)
        self.assertIn(GITHUB_STATUS_URL, message)
        self.assertIn("too slow", message)
        self.assertIn("10 seconds", message)

    @patch("status_pulse.polls.urlopen")
    def test_bad_answer_raises_bad_answer_error(self, urlopen: object) -> None:
        urlopen.return_value = FakeResponse(b"<!DOCTYPE html> not json")

        with self.assertRaises(GitHubStatusBadAnswerError) as caught:
            fetch_github_status()

        message = str(caught.exception)
        self.assertIn(GITHUB_STATUS_URL, message)
        self.assertIn("not valid JSON", message)
        self.assertIn("Try again later", message)
