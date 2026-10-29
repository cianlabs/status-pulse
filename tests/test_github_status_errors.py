"""Tests for each way the GitHub status check can fail."""

from __future__ import annotations

import socket
from unittest import TestCase
from unittest.mock import patch

import httpx

from status_pulse.polls import (
    GITHUB_STATUS_URL,
    GitHubStatusBadAnswerError,
    GitHubStatusOfflineError,
    GitHubStatusTimeoutError,
    GitHubStatusWebsiteDownError,
    fetch_github_status,
)


def _request() -> httpx.Request:
    return httpx.Request("GET", GITHUB_STATUS_URL)


def _response(status_code: int, text: str = "") -> httpx.Response:
    return httpx.Response(status_code, text=text, request=_request())


def _connect_error_offline() -> httpx.ConnectError:
    error = httpx.ConnectError("Failed to resolve host", request=_request())
    error.__cause__ = socket.gaierror("nodename not known")
    return error


class FetchGitHubStatusErrorTests(TestCase):
    @patch("status_pulse.polls.time.sleep")
    @patch("status_pulse.polls.httpx.get")
    def test_no_internet_raises_offline_error(
        self, httpx_get: object, sleep: object
    ) -> None:
        httpx_get.side_effect = _connect_error_offline()

        with self.assertRaises(GitHubStatusOfflineError) as caught:
            fetch_github_status()

        message = str(caught.exception)
        self.assertIn(GITHUB_STATUS_URL, message)
        self.assertIn("offline", message)
        self.assertIn("Wi-Fi or Ethernet", message)

    @patch("status_pulse.polls.time.sleep")
    @patch("status_pulse.polls.httpx.get")
    def test_website_down_raises_website_down_error(
        self, httpx_get: object, sleep: object
    ) -> None:
        httpx_get.return_value = _response(503)

        with self.assertRaises(GitHubStatusWebsiteDownError) as caught:
            fetch_github_status()

        message = str(caught.exception)
        self.assertIn(GITHUB_STATUS_URL, message)
        self.assertIn("HTTP 503", message)
        self.assertIn("browser", message)

    @patch("status_pulse.polls.time.sleep")
    @patch("status_pulse.polls.httpx.get")
    def test_slow_reply_raises_timeout_error(
        self, httpx_get: object, sleep: object
    ) -> None:
        httpx_get.side_effect = httpx.TimeoutException("timed out")

        with self.assertRaises(GitHubStatusTimeoutError) as caught:
            fetch_github_status()

        message = str(caught.exception)
        self.assertIn(GITHUB_STATUS_URL, message)
        self.assertIn("too slow", message)
        self.assertIn("5 seconds", message)

    @patch("status_pulse.polls.time.sleep")
    @patch("status_pulse.polls.httpx.get")
    def test_bad_answer_raises_bad_answer_error(
        self, httpx_get: object, sleep: object
    ) -> None:
        httpx_get.return_value = _response(200, "<!DOCTYPE html> not json")

        with self.assertRaises(GitHubStatusBadAnswerError) as caught:
            fetch_github_status()

        message = str(caught.exception)
        self.assertIn(GITHUB_STATUS_URL, message)
        self.assertIn("not valid JSON", message)
        self.assertIn("Try again later", message)
        sleep.assert_not_called()
