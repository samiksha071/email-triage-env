"""
FastAPI server — Email Triage OpenEnv.
Serves web UI at GET / and the full OpenEnv API.
"""
import os, sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import EmailTriageAction, EmailObservation, EmailTriageState
from server.environment import EmailTriageEnvironment

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
    score: float =0.5
    correct: int
    total: int
    cumulative_reward: float
    message: str

env = EmailTriageEnvironment()
TEMPLATE = Path(__file__).parent.parent / "templates" / "index.html"
if not TEMPLATE.exists():
    TEMPLATE = Path("/app/templates/index.html")

@asynccontextmanager
async def lifespan(app: FastAPI):
    env.reset(task_id="easy")
    yield

app = FastAPI(title="Email Triage OpenEnv", version="1.0.0", lifespan=lifespan)

@app.get("/", response_class=HTMLResponse)
async def frontend():
    if TEMPLATE.exists():
        return HTMLResponse(content=TEMPLATE.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>Email Triage RL Environment running. See /docs</h2>")

@app.get("/health")
async def health():
    return {"status": "ok", "environment": "email-triage-env", "version": "1.0.0"}

@app.post("/reset", response_model=ResetResponse)
async def reset(request: ResetRequest = ResetRequest()):
    obs, info = env.reset(task_id=request.task_id or "easy")
    return ResetResponse(observation=obs, info=info)

@app.post("/step", response_model=StepResponse)
async def step(action: EmailTriageAction):
    try:
        obs, reward, done, info = env.step(action)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return StepResponse(observation=obs, reward=reward, done=done, info=info)

@app.get("/state")
async def state():
    return env.state()

@app.get("/tasks")
async def list_tasks():
    return {"tasks": [
        {"id": "easy",   "description": "5 emails — clear-cut categories", "num_emails": 5},
        {"id": "medium", "description": "8 emails — ambiguous signals",     "num_emails": 8},
        {"id": "hard",   "description": "12 emails — strict grading",       "num_emails": 12},
    ]}

@app.post("/run_grader", response_model=GraderResponse)
async def run_grader():
    s = env.state()
    raw_score = env.get_task_score()
    score = round(max(0.05, min(0.95, float(raw_score))), 4)
    # Extra safety — never return boundary values
    if score <= 0.0 or score >= 1.0:
        score = 0.5
    return GraderResponse(
        task_id=s.task_id,
        score=score,
        correct=s.correct_classifications,
        total=s.total_classifications,
        cumulative_reward=float(s.cumulative_reward),
        message=f"Score: {score:.4f}",
    )

def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__=="__main__":
    main()    