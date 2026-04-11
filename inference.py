#!/usr/bin/env python3
"""
inference.py — Baseline LLM agent for the Email Triage OpenEnv environment.

Environment variables required
-------------------------------
API_BASE_URL   : OpenAI-compatible API base URL
MODEL_NAME     : Model identifier (e.g. "gpt-4o-mini")
HF_TOKEN       : Your API key / Hugging Face token
ENV_BASE_URL   : (optional) URL of the deployed HF Space or local server
                 Defaults to http://localhost:7860

Run
---
    export API_BASE_URL="https://api.openai.com/v1"
    export MODEL_NAME="gpt-4o-mini"
    export HF_TOKEN="sk-..."
    python inference.py

Structured stdout log format (required by hackathon evaluator)
--------------------------------------------------------------
[START] {"task_id": ..., "model": ..., "env_url": ...}
[STEP]  {"task_id": ..., "step": ..., "email_id": ..., "action": {...}, "reward": ..., "done": ...}
[END]   {"task_id": ..., "score": ..., "total_steps": ..., "cumulative_reward": ...}
"""

import json
import os
import sys
import time

import httpx
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "gpt-4o-mini")
HF_TOKEN     = os.environ.get("HF_TOKEN",     os.environ.get("OPENAI_API_KEY", ""))
ENV_BASE_URL = os.environ.get("ENV_BASE_URL",  "http://localhost:7860")

MAX_RETRIES  = 3
TASKS        = ["easy", "medium", "hard"]

# ── OpenAI client ─────────────────────────────────────────────────────────────

client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)

# ── Logging helpers ───────────────────────────────────────────────────────────

def log(tag: str, data: dict):
    """Emit a structured log line in the required [TAG] {json} format."""
    print(f"{tag} {json.dumps(data)}", flush=True)


# ── LLM action generator ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert email triage assistant. You will be given an email and must classify it.

Respond with ONLY valid JSON matching this schema (no markdown, no explanation):
{
  "category": "<one of: urgent | normal | spam | newsletter | follow_up>",
  "priority": "<one of: high | medium | low>",
  "summary": "<1-2 sentence summary of the email, max 300 chars>",
  "suggested_action": "<what the user should do, max 200 chars>"
}

Guidelines:
- urgent   : requires immediate attention (outages, security, deadlines within 24h, angry customers)
- normal   : routine business communication
- spam     : unsolicited/promotional, phishing, irrelevant external emails
- newsletter : subscriptions, digests, automated updates not requiring action
- follow_up : explicit follow-up requests, pending items needing response
- priority high   : acts today
- priority medium : acts this week
- priority low    : can wait or ignore
"""


def classify_email(obs: dict, retries: int = MAX_RETRIES) -> dict:
    """Call the LLM and return a parsed action dict."""
    user_content = (
        f"Subject: {obs['subject']}\n"
        f"From: {obs['sender']}\n"
        f"Date: {obs['timestamp']}\n"
        f"Thread length: {obs['thread_length']}\n"
        f"Has attachments: {obs['has_attachments']}\n\n"
        f"Body:\n{obs['body']}"
    )
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_content},
                ],
                temperature=0.1,
                max_tokens=300,
            )
            raw = response.choices[0].message.content.strip()
            # Strip accidental markdown fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            action = json.loads(raw)
            # Validate required keys
            for key in ("category", "priority", "summary", "suggested_action"):
                assert key in action, f"Missing key: {key}"
            return action
        except Exception as exc:
            if attempt == retries - 1:
                # Fallback safe action
                return {
                    "category": "normal",
                    "priority": "medium",
                    "summary": "Could not parse email.",
                    "suggested_action": "Review manually.",
                }
            time.sleep(1)


# ── Environment helpers ───────────────────────────────────────────────────────

def env_post(path: str, payload: dict | None = None) -> dict:
    url = ENV_BASE_URL.rstrip("/") + path
    if payload is None:
        r = httpx.get(url, timeout=30)
    else:
        r = httpx.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def run_task(task_id: str) -> dict:
    """Run a full episode for one task and return summary metrics."""
    log("[START]", {"task_id": task_id, "model": MODEL_NAME, "env_url": ENV_BASE_URL})

    # Reset
    reset_data = env_post("/reset", {"task_id": task_id})
    obs = reset_data["observation"]

    step_num = 0
    cumulative_reward = 0.0
    done = False

    while not done:
        step_num += 1
        action = classify_email(obs)

        result = env_post("/step", action)
        reward = round(max(0.01, min(0.99, float(result["reward"]))), 4)
        done   = result["done"]
        obs    = result["observation"]
        info   = result["info"]
        cumulative_reward += reward

        log("[STEP]", {
            "task_id":  task_id,
            "step":     step_num,
            "email_id": info.get("email_id", "?"),
            "action":   action,
            "reward":   reward,
            "done":     done,
        })

    # Fetch grader score
    grader = env_post("/run_grader", {})
    final_score = round(max(0.06, min(0.94, float(grader["score"]))), 2)

    log("[END]", {
        "task_id":          task_id,
        "final_score":            final_score,
        "total_steps":      step_num,
        "cumulative_reward": round(cumulative_reward, 4),
    })

    return {
        "task_id":          task_id,
        "score":            final_score,
        "total_steps":      step_num,
        "cumulative_reward": round(cumulative_reward, 4),
    }

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not HF_TOKEN:
        print("ERROR: HF_TOKEN (or OPENAI_API_KEY) environment variable not set.", file=sys.stderr)
        sys.exit(1)

    print(f"=== Email Triage RL Baseline ===")
    print(f"Model    : {MODEL_NAME}")
    print(f"API URL  : {API_BASE_URL}")
    print(f"Env URL  : {ENV_BASE_URL}")
    print()

    results = []
    for task_id in TASKS:
        try:
            result = run_task(task_id)
            results.append(result)
            print(f"  [{task_id:6s}] score={result['score']:.4f}  steps={result['total_steps']}")
        except Exception as exc:
            print(f"  [{task_id:6s}] ERROR: {exc}", file=sys.stderr)
            results.append({"task_id": task_id, "score": 0.05, "error": str(exc)})

    print()
    scores = [r["score"] for r in results]
    avg = sum(scores) / len(scores) if scores else 0.0555
    print(f"=== Summary ===")
    for r in results:
        print(f"  {r['task_id']:6s}  ->  {r.get('score', 0.05):.4f}")
    print(f"  Average score: {avg:.4f}")

    # Machine-readable final summary
    print(json.dumps({"summary": results, "average_score": round(max(0.05, min(0.95, avg)), 4)}))


if __name__ == "__main__":
    main()