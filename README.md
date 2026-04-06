# 📧 Email Triage — OpenEnv RL Environment

An **OpenEnv-compatible reinforcement learning environment** where an AI agent learns to triage emails by category and priority. Built for the **Meta × Hugging Face OpenEnv Hackathon**.

---

## 🎯 What the Agent Does

The agent receives one email at a time and must:

| Output field | Options |
|---|---|
| `category` | `urgent` · `normal` · `spam` · `newsletter` · `follow_up` |
| `priority` | `high` · `medium` · `low` |
| `summary` | ≤ 300 char summary of the email |
| `suggested_action` | ≤ 200 char next step for the user |

---

## 🗂️ Project Structure

```
email-triage-env/
├── models.py            # Pydantic: Action, Observation, State
├── client.py            # Python client (sync + async)
├── inference.py         # ⭐ Baseline LLM agent (required by hackathon)
├── demo.py              # Quick demo — no API key needed
├── openenv.yaml         # OpenEnv spec metadata
├── requirements.txt
├── Dockerfile
└── server/
    ├── __init__.py
    ├── app.py           # FastAPI server
    └── environment.py   # Core environment logic + grader
```

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the server
```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### 3. Run the heuristic demo (no API key needed)
```bash
python demo.py
```

### 4. Run the LLM baseline
```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="sk-..."         # your OpenAI / HF API key
export ENV_BASE_URL="http://localhost:7860"

python inference.py
```

---

## 🐳 Docker

```bash
docker build -t email-triage-env .
docker run -p 7860:7860 email-triage-env
```

---

## 🌐 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | Liveness probe |
| `GET`  | `/tasks`  | List all 3 tasks |
| `POST` | `/reset`  | Start episode (`{"task_id": "easy"}`) |
| `POST` | `/step`   | Submit action (EmailTriageAction JSON) |
| `GET`  | `/state`  | Current episode state |
| `POST` | `/run_grader` | Returns normalised score 0.0–1.0 |

---

## 📊 Tasks

| Task   | Emails | Difficulty | Notes |
|--------|--------|-----------|-------|
| `easy`   | 5  | ⭐         | Clear-cut categories, obvious signals |
| `medium` | 8  | ⭐⭐       | Ambiguous senders, partial credit on priority |
| `hard`   | 12 | ⭐⭐⭐     | Nuanced priorities, no partial credit, all edge cases |

---

## 🏆 Reward Function

Dense rewards are emitted at every step (not just at episode end):

| Condition | Reward |
|-----------|--------|
| Category correct | **+0.6** |
| Priority correct | **+0.3** |
| Summary relevance | **+0.0–0.1** |
| Wrong category | **−0.3** |
| Summary > 300 chars | **−0.1** |
| Episode accuracy ≥ 80% | **+0.5 bonus** |

The grader normalises the cumulative reward to a score in **[0.0, 1.0]**.

---

## 📝 Structured Log Format

`inference.py` emits the required hackathon log format:

```
[START] {"task_id": "easy", "model": "gpt-4o-mini", "env_url": "..."}
[STEP]  {"task_id": "easy", "step": 1, "email_id": "e001", "action": {...}, "reward": 0.9, "done": false}
[END]   {"task_id": "easy", "final_score": 0.8800, "total_steps": 5, "cumulative_reward": 4.05}
```

---

## 🔧 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_BASE_URL` | OpenAI-compatible API endpoint | `https://api.openai.com/v1` |
| `MODEL_NAME` | LLM model identifier | `gpt-4o-mini` |
| `HF_TOKEN` | Your API key | — |
| `ENV_BASE_URL` | Environment server URL | `http://localhost:7860` |

---

## 🤗 Deploy to Hugging Face Spaces

```bash
# Install OpenEnv CLI
pip install openenv-core

# Push to HF Spaces
openenv push --repo-id YOUR_USERNAME/email-triage-env
```

Or manually create a new Space (Docker SDK), push this repo, and set the port to **7860**.

---

## ✅ Pre-submission Checklist

- [x] `openenv.yaml` with spec_version, name, tasks
- [x] Typed `EmailTriageAction`, `EmailObservation`, `EmailTriageState` Pydantic models
- [x] `reset()` → returns initial observation
- [x] `step(action)` → returns observation, reward, done, info
- [x] `state()` → returns current state
- [x] `/health` endpoint returns 200
- [x] 3 tasks (easy / medium / hard) with programmatic graders
- [x] Grader scores strictly in [0.0, 1.0]
- [x] Dense reward (signal at every step, not just terminal)
- [x] `inference.py` in root, uses OpenAI client, reads from env vars
- [x] `[START]` / `[STEP]` / `[END]` structured log format
- [x] `Dockerfile` builds and runs
- [x] `requirements.txt` present

---

## 📄 License
MIT
