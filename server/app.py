"""
FastAPI server exposing the OpenEnv HTTP interface for Email Triage.

Endpoints
---------
GET  /health           — liveness probe
POST /reset            — start new episode
POST /step             — take action
GET  /state            — current state snapshot
GET  /tasks            — list available tasks with grader scores
POST /run_grader       — run grader on completed episode and return score
"""
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ── fix imports whether running from repo root or from server/ ───────────────
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from models import EmailTriageAction, EmailObservation, EmailTriageState
from server.environment import EmailTriageEnvironment


# ── Request/Response schemas ─────────────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: Optional[str] = "easy"


class StepResponse(BaseModel):
    observation: EmailObservation
    reward: float
    done: bool
    info: Dict[str, Any]


class ResetResponse(BaseModel):
    observation: EmailObservation
    info: Dict[str, Any]


class GraderResponse(BaseModel):
    task_id: str
    score: float          # normalised 0.0 – 1.0
    correct: int
    total: int
    cumulative_reward: float
    message: str


# ── App & environment singleton ───────────────────────────────────────────────

env: EmailTriageEnvironment = EmailTriageEnvironment()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise with a default easy episode so /health never fails
    env.reset(task_id="easy")
    yield


app = FastAPI(
    title="Email Triage OpenEnv",
    description=(
        "An OpenEnv-compatible RL environment where an agent learns to "
        "triage emails by category and priority."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "environment": "email-triage-env", "version": "1.0.0"}


@app.post("/reset", response_model=ResetResponse)
async def reset(request: ResetRequest = ResetRequest()):
    """Start a new episode. task_id ∈ {easy, medium, hard}."""
    obs, info = env.reset(task_id=request.task_id or "easy")
    return ResetResponse(observation=obs, info=info)


@app.post("/step", response_model=StepResponse)
async def step(action: EmailTriageAction):
    """Submit a classification for the current email."""
    try:
        obs, reward, done, info = env.step(action)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return StepResponse(observation=obs, reward=reward, done=done, info=info)


@app.get("/state")
async def state():
    """Return the current internal state."""
    return env.state()


@app.get("/tasks")
async def list_tasks():
    """Return metadata for all available tasks."""
    return {
        "tasks": [
            {
                "id": "easy",
                "description": "5 emails — clear-cut categories, straightforward signals",
                "num_emails": 5,
                "max_steps": 5,
            },
            {
                "id": "medium",
                "description": "8 emails — ambiguous senders, mixed signals, partial-credit scoring",
                "num_emails": 8,
                "max_steps": 8,
            },
            {
                "id": "hard",
                "description": "12 emails — nuanced priorities, strict grading, no partial credit for priority",
                "num_emails": 12,
                "max_steps": 12,
            },
        ]
    }


@app.post("/run_grader", response_model=GraderResponse)
async def run_grader():
    """
    Run the programmatic grader on the current (completed) episode.
    Returns a normalised score in [0.0, 1.0].
    """
    s = env.state()
    score = env.get_task_score()
    return GraderResponse(
        task_id=s.task_id,
        score=score,
        correct=s.correct_classifications,
        total=s.total_classifications,
        cumulative_reward=s.cumulative_reward,
        message=(
            f"Episode {'complete' if s.done else 'in progress'}. "
            f"Score: {score:.4f}"
        ),
    )
