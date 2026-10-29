"""Command-line entry point."""

from __future__ import annotations

import sys

from status_pulse.polls import GitHubStatusError, fetch_github_status, github_is_up


def main() -> None:
    try:
        payload = fetch_github_status()
    except GitHubStatusError as exc:
        print(exc)
        sys.exit(1)

    if github_is_up(payload):
        print("Good news: GitHub is up right now.")
    else:
        print("Heads up: GitHub is not fully up right now.")


if __name__ == "__main__":
    main()
