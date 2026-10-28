"""Command-line entry point."""

from __future__ import annotations

from status_pulse.polls import fetch_github_status, github_is_up


def main() -> None:
    payload = fetch_github_status()
    if github_is_up(payload):
        print("Good news: GitHub is up right now.")
    else:
        print("Heads up: GitHub is not fully up right now.")


if __name__ == "__main__":
    main()
