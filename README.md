# status-pulse

Python project for Status Pulse.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```bash
status-pulse
```

Fetches [GitHub's status JSON](https://www.githubstatus.com/api/v2/status.json) and prints a friendly sentence saying whether GitHub is up.
