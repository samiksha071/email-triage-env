#!/usr/bin/env python3
"""
demo.py — Quick local demo that runs a rule-based agent against all 3 tasks.
Does NOT require an API key. Uses a keyword-based heuristic classifier.

Start the server first:
    uvicorn server.app:app --port 7860

Then run:
    python demo.py
"""
import json
import httpx

ENV_BASE_URL = "http://localhost:7860"


# ── Heuristic classifier (no LLM needed) ─────────────────────────────────────

URGENT_KEYWORDS   = ["urgent", "down", "outage", "cve", "critical", "expire", "suspend", "exhausted", "okr", "review"]
SPAM_KEYWORDS     = ["winner", "prize", "click here", "unsubscribe", "deal", "sale", "off all", "verify", "paypai", "shopnow", "talentbridge"]
NEWSLETTER_WORDS  = ["digest", "newsletter", "weekly", "monthly", "read in browser", "bytebytego", "devopsweekly"]
FOLLOW_UP_WORDS   = ["following up", "follow up", "just wanted", "checking in", "reminder", "pending", "invoice"]


def heuristic_classify(obs: dict) -> dict:
    text = (obs["subject"] + " " + obs["body"]).lower()

    # Category
    if any(k in text for k in SPAM_KEYWORDS):
        cat, pri = "spam", "low"
    elif any(k in text for k in NEWSLETTER_WORDS):
        cat, pri = "newsletter", "low"
    elif any(k in text for k in FOLLOW_UP_WORDS):
        cat, pri = "follow_up", "medium"
    elif any(k in text for k in URGENT_KEYWORDS):
        cat, pri = "urgent", "high"
    else:
        cat, pri = "normal", "medium"

    summary = obs["body"][:200].strip()
    return {
        "category": cat,
        "priority": pri,
        "summary": summary,
        "suggested_action": "Review and act according to category.",
    }


def run_task(task_id: str):
    print(f"\n{'='*50}")
    print(f"Task: {task_id.upper()}")
    print(f"{'='*50}")

    # Reset
    r = httpx.post(f"{ENV_BASE_URL}/reset", json={"task_id": task_id}, timeout=10)
    r.raise_for_status()
    data = r.json()
    obs  = data["observation"]
    print(f"  Total emails: {data['info']['total_emails']}")

    step, total_reward, done = 0, 0.0, False
    while not done:
        step += 1
        action = heuristic_classify(obs)
        r = httpx.post(f"{ENV_BASE_URL}/step", json=action, timeout=10)
        r.raise_for_status()
        result = r.json()
        reward = result["reward"]
        done   = result["done"]
        obs    = result["observation"]
        info   = result["info"]
        total_reward += reward
        print(f"  Step {step:2d} | email={info.get('email_id','?'):5s} | "
              f"cat={action['category']:12s} | pri={action['priority']:6s} | "
              f"reward={reward:+.3f}")

    # Grader
    r = httpx.post(f"{ENV_BASE_URL}/run_grader", json={}, timeout=10)
    r.raise_for_status()
    grader = r.json()
    print(f"\n  Final score : {grader['score']:.4f}")
    print(f"  Correct     : {grader['correct']}/{grader['total']}")
    return grader["score"]


def main():
    print("Email Triage RL Demo — heuristic agent")
    scores = {}
    for task in ["easy", "medium", "hard"]:
        try:
            scores[task] = run_task(task)
        except Exception as e:
            print(f"  ERROR running {task}: {e}")
            scores[task] = 0.0

    print(f"\n{'='*50}")
    print("Summary:")
    for k, v in scores.items():
        print(f"  {k:6s} → {v:.4f}")
    avg = sum(scores.values()) / len(scores)
    print(f"  Average → {avg:.4f}")


if __name__ == "__main__":
    main()
