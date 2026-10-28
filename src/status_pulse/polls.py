"""Status polls for external services."""

from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen

GITHUB_STATUS_URL = "https://www.githubstatus.com/api/v2/status.json"


def fetch_github_status() -> dict[str, Any]:
    request = Request(
        GITHUB_STATUS_URL,
        headers={"User-Agent": "status-pulse", "Accept": "application/json"},
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def github_is_up(payload: dict[str, Any]) -> bool:
    return payload.get("status", {}).get("indicator") == "none"
