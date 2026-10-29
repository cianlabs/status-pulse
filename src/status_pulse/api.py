"""Small web API for the GitHub status check."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from status_pulse.polls import (
    GitHubStatusBadAnswerError,
    GitHubStatusError,
    GitHubStatusOfflineError,
    GitHubStatusTimeoutError,
    GitHubStatusWebsiteDownError,
    fetch_github_status,
    github_is_up,
    github_status_message,
)

app = FastAPI(title="Status Pulse")


class HealthResponse(BaseModel):
    """JSON for a simple liveness check."""

    ok: bool


class StatusResponse(BaseModel):
    """JSON when the check finishes."""

    github_up: bool
    message: str


class StatusErrorResponse(BaseModel):
    """JSON when the check cannot finish."""

    error: str
    message: str


# What the visitor's client should see when the check itself fails.
_STATUS_CODE_FOR = {
    GitHubStatusOfflineError: 503,
    GitHubStatusWebsiteDownError: 502,
    GitHubStatusTimeoutError: 504,
    GitHubStatusBadAnswerError: 502,
}


@app.exception_handler(GitHubStatusError)
def github_status_error(request: Request, exc: GitHubStatusError) -> JSONResponse:
    body = StatusErrorResponse(error=type(exc).__name__, message=str(exc))
    return JSONResponse(
        status_code=_STATUS_CODE_FOR.get(type(exc), 502),
        content=body.model_dump(),
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True)


@app.get(
    "/status",
    response_model=StatusResponse,
    responses={
        502: {"model": StatusErrorResponse},
        503: {"model": StatusErrorResponse},
        504: {"model": StatusErrorResponse},
    },
)
def github_status() -> StatusResponse:
    payload = fetch_github_status()
    return StatusResponse(
        github_up=github_is_up(payload),
        message=github_status_message(payload),
    )
