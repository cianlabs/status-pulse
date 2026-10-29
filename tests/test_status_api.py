"""Tests for the web routes."""

from __future__ import annotations

import socket
from unittest import TestCase
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from status_pulse.api import app
from status_pulse.polls import GITHUB_STATUS_URL


def _request() -> httpx.Request:
    return httpx.Request("GET", GITHUB_STATUS_URL)


def _response(
    status_code: int,
    text: str = "",
    json_body: object | None = None,
) -> httpx.Response:
    if json_body is not None:
        return httpx.Response(status_code, json=json_body, request=_request())
    return httpx.Response(status_code, text=text, request=_request())


def _connect_error_offline() -> httpx.ConnectError:
    error = httpx.ConnectError("Failed to resolve host", request=_request())
    error.__cause__ = socket.gaierror("nodename not known")
    return error


class StatusRouteTests(TestCase):
    def setUp(self) -> None:
        self._client = TestClient(app)
        self.client = self._client.__enter__()

    def tearDown(self) -> None:
        self._client.__exit__(None, None, None)

    def test_health(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    @patch("status_pulse.polls.httpx.get")
    def test_github_up(self, httpx_get: object) -> None:
        httpx_get.return_value = _response(
            200, json_body={"status": {"indicator": "none"}}
        )

        response = self.client.get("/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "github_up": True,
                "message": "Good news: GitHub is up right now.",
            },
        )

    @patch("status_pulse.polls.httpx.get")
    def test_github_not_fully_up(self, httpx_get: object) -> None:
        httpx_get.return_value = _response(
            200, json_body={"status": {"indicator": "major"}}
        )

        response = self.client.get("/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "github_up": False,
                "message": "Heads up: GitHub is not fully up right now.",
            },
        )

    @patch("status_pulse.polls.time.sleep")
    @patch("status_pulse.polls.httpx.get")
    def test_no_internet_returns_offline_error(
        self, httpx_get: object, sleep: object
    ) -> None:
        httpx_get.side_effect = _connect_error_offline()

        response = self.client.get("/status")

        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(set(body), {"error", "message"})
        self.assertEqual(body["error"], "GitHubStatusOfflineError")
        self.assertIn(GITHUB_STATUS_URL, body["message"])
        self.assertIn("offline", body["message"])
        self.assertIn("Wi-Fi or Ethernet", body["message"])

    @patch("status_pulse.polls.time.sleep")
    @patch("status_pulse.polls.httpx.get")
    def test_website_down_returns_website_down_error(
        self, httpx_get: object, sleep: object
    ) -> None:
        httpx_get.return_value = _response(503)

        response = self.client.get("/status")

        self.assertEqual(response.status_code, 502)
        body = response.json()
        self.assertEqual(set(body), {"error", "message"})
        self.assertEqual(body["error"], "GitHubStatusWebsiteDownError")
        self.assertIn(GITHUB_STATUS_URL, body["message"])
        self.assertIn("HTTP 503", body["message"])
        self.assertIn("browser", body["message"])

    @patch("status_pulse.polls.time.sleep")
    @patch("status_pulse.polls.httpx.get")
    def test_slow_reply_returns_timeout_error(
        self, httpx_get: object, sleep: object
    ) -> None:
        httpx_get.side_effect = httpx.TimeoutException("timed out")

        response = self.client.get("/status")

        self.assertEqual(response.status_code, 504)
        body = response.json()
        self.assertEqual(set(body), {"error", "message"})
        self.assertEqual(body["error"], "GitHubStatusTimeoutError")
        self.assertIn(GITHUB_STATUS_URL, body["message"])
        self.assertIn("too slow", body["message"])
        self.assertIn("5 seconds", body["message"])

    @patch("status_pulse.polls.time.sleep")
    @patch("status_pulse.polls.httpx.get")
    def test_bad_answer_returns_bad_answer_error(
        self, httpx_get: object, sleep: object
    ) -> None:
        httpx_get.return_value = _response(200, "<!DOCTYPE html> not json")

        response = self.client.get("/status")

        self.assertEqual(response.status_code, 502)
        body = response.json()
        self.assertEqual(set(body), {"error", "message"})
        self.assertEqual(body["error"], "GitHubStatusBadAnswerError")
        self.assertIn(GITHUB_STATUS_URL, body["message"])
        self.assertIn("not valid JSON", body["message"])
        self.assertIn("Try again later", body["message"])
        sleep.assert_not_called()
