"""Command-line entry point."""

from __future__ import annotations

import sys

from status_pulse.polls import GitHubStatusError, fetch_github_status, github_status_message


def main() -> None:
    try:
        payload = fetch_github_status()
    except GitHubStatusError as exc:
        print(exc)
        sys.exit(1)

    print(github_status_message(payload))


if __name__ == "__main__":
    main()
