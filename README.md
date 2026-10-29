# status-pulse

A tiny command-line tool that checks GitHub’s public status page and tells you, in one sentence, whether GitHub is up.

## What it does

It asks [GitHub’s status page](https://www.githubstatus.com/api/v2/status.json) for a short status report, using the [httpx](https://www.python-httpx.org/) library. Each try waits at most 5 seconds. If the problem looks flaky (no internet, a slow page, or a page that looks down), it tries up to 3 times, with a half-second pause between tries. A reply that is not usable JSON is not retried. Then it prints one friendly sentence.

You need Python 3.11 or newer.

## Install and run

Clone this repo, open the project folder, then run these three commands. They work in Terminal on macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate && pip install -e .
status-pulse
```

## Example output

When the check works and GitHub looks healthy:

```text
Good news: GitHub is up right now.
```

When this computer looks offline:

```text
Could not reach GitHub's status page at https://www.githubstatus.com/api/v2/status.json because this computer appears to be offline (no internet, or the site name could not be looked up). Check your Wi-Fi or Ethernet, then try again.
```

If the page answers but GitHub is not fully healthy, you get: `Heads up: GitHub is not fully up right now.`

## How it fails

If Status Pulse cannot tell whether GitHub is up, it prints a plain-English message and stops. Each case has its own named error:

- **GitHubStatusOfflineError** — this computer looks offline, or the site name could not be looked up.
- **GitHubStatusWebsiteDownError** — GitHub’s status page looks down (for example it returned HTTP 503).
- **GitHubStatusTimeoutError** — the page took longer than 5 seconds to answer.
- **GitHubStatusBadAnswerError** — the page answered, but the reply was not usable JSON.

## Tests

From the project folder, with the virtual environment active:

```bash
python -m unittest discover -s tests -v
```

There is one test for each of those four failures. The tests fake the web request, so they do not need a real internet connection.

## What I learned

I practiced turning messy network problems into named errors whose messages say what failed, where, and what to try next. I wrote one test per failure by faking the web request. Then I switched the fetch from Python’s built-in urllib to httpx and added a timeout plus retries, without changing those error names.
