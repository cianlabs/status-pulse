"""Local demo monitor for status-pulse. Not production.

Pings the live Render service every couple of minutes and prints one line per check:
time, HTTP status code, and whether github_up was true.
It runs only while this script is running. Press Ctrl+C to stop.
No cloud scheduler, no extra services, no cost.

Run it:  python monitor.py
"""

import time
from datetime import datetime

import httpx

URL = "https://status-pulse-3wo5.onrender.com/status"
EVERY_SECONDS = 120
# The free host sleeps when idle, so the first check can be slow.
TIMEOUT_SECONDS = 60


def check_once() -> str:
    """Return one human-readable log line. Never crashes; failures are named."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        response = httpx.get(URL, timeout=TIMEOUT_SECONDS)
    except httpx.TimeoutException:
        return f"{now} | TIMEOUT | no answer in {TIMEOUT_SECONDS}s (the free host may be waking up) | github_up=unknown"
    except httpx.TransportError as error:
        return f"{now} | UNREACHABLE | could not connect ({type(error).__name__}); check your internet | github_up=unknown"

    try:
        github_up = response.json().get("github_up")
    except ValueError:
        return f"{now} | BAD_ANSWER | HTTP {response.status_code} but the body was not JSON | github_up=unknown"
    return f"{now} | HTTP {response.status_code} | github_up={github_up}"


def main() -> None:
    print(f"Watching {URL} every {EVERY_SECONDS}s. Press Ctrl+C to stop.")
    try:
        while True:
            print(check_once(), flush=True)
            time.sleep(EVERY_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped. Bye!")


if __name__ == "__main__":
    main()
