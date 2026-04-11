"""
Email Triage Environment — core logic.

Tasks
-----
easy   : 5 emails, clear-cut categories, simple grading
medium : 8 emails, ambiguous senders/subjects, partial-credit scoring
hard   : 12 emails, mixed threads, priority subtleties, strict grading

Reward design
-------------
- +1.0  perfect match (category + priority both correct)
- +0.5  category correct, priority wrong  (or vice versa for hard)
- +0.25 partially relevant summary (checked heuristically)
- -0.3  completely wrong category
- -0.1  step penalty for exceeding token budget (summary > 300 chars)
- Episode bonus: +0.5 if overall accuracy ≥ 80 %
"""
import random
from typing import List, Tuple, Dict, Any, Optional

from models import EmailTriageAction, EmailObservation, EmailTriageState


# ── Email Dataset ────────────────────────────────────────────────────────────

EMAILS: Dict[str, List[Dict]] = {
    "easy": [
        {
            "id": "e001",
            "subject": "URGENT: Server down in production",
            "sender": "ops-alerts@company.com",
            "body": (
                "ALERT: The main production API server went down at 03:12 UTC. "
                "Error rate is 100%. All requests are failing. "
                "On-call engineer please acknowledge immediately."
            ),
            "timestamp": "2024-03-15T03:14:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "urgent",
            "correct_priority": "high",
        },
        {
            "id": "e002",
            "subject": "50% OFF all products this weekend only!!!",
            "sender": "deals@shopnow-promo.biz",
            "body": (
                "Don't miss our MEGA SALE! Click here to claim your discount. "
                "Limited time offer. Unsubscribe link at bottom."
            ),
            "timestamp": "2024-03-15T08:00:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "spam",
            "correct_priority": "low",
        },
        {
            "id": "e003",
            "subject": "Weekly engineering newsletter - March 15",
            "sender": "newsletter@techdigest.io",
            "body": (
                "This week in tech: GPT-5 rumors, Rust adoption metrics, "
                "and our featured article on eBPF observability. "
                "Click to read in browser."
            ),
            "timestamp": "2024-03-15T09:00:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "newsletter",
            "correct_priority": "low",
        },
        {
            "id": "e004",
            "subject": "Re: Q1 budget proposal — need your sign-off",
            "sender": "finance@company.com",
            "body": (
                "Hi, as discussed in yesterday's meeting the Q1 budget is ready for approval. "
                "Please review the attached spreadsheet and reply with your sign-off by EOD Friday. "
                "This blocks the procurement team."
            ),
            "timestamp": "2024-03-15T10:30:00Z",
            "thread_length": 3,
            "has_attachments": True,
            "correct_category": "urgent",
            "correct_priority": "high",
        },
        {
            "id": "e005",
            "subject": "Lunch options for team event",
            "sender": "events@company.com",
            "body": (
                "Hey team! We're organising a team lunch on March 22nd. "
                "Please fill in the Doodle poll to indicate your dietary preferences. "
                "No rush — poll closes March 20th."
            ),
            "timestamp": "2024-03-15T11:00:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "normal",
            "correct_priority": "low",
        },
    ],

    "medium": [
        {
            "id": "m001",
            "subject": "Following up on our conversation",
            "sender": "john.smith@clientcorp.com",
            "body": (
                "Hi, just wanted to follow up on our call last Tuesday. "
                "Did you get a chance to review the proposal? "
                "Happy to jump on another call if needed. Best, John"
            ),
            "timestamp": "2024-03-15T09:00:00Z",
            "thread_length": 2,
            "has_attachments": False,
            "correct_category": "follow_up",
            "correct_priority": "medium",
        },
        {
            "id": "m002",
            "subject": "Security vulnerability disclosed — CVE-2024-1234",
            "sender": "security-scanner@github.com",
            "body": (
                "A new critical CVE has been detected in your dependency lodash@4.17.20. "
                "CVSS score: 9.1 (Critical). Upgrade to 4.17.21 immediately. "
                "Automated PR has been created: #2341."
            ),
            "timestamp": "2024-03-15T07:45:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "urgent",
            "correct_priority": "high",
        },
        {
            "id": "m003",
            "subject": "Your April invoice from AWS",
            "sender": "billing@amazon.com",
            "body": (
                "Your AWS invoice for March 2024 is ready. "
                "Total amount due: $4,312.50. Payment will be charged on April 1st. "
                "View your invoice in the billing console."
            ),
            "timestamp": "2024-03-15T12:00:00Z",
            "thread_length": 1,
            "has_attachments": True,
            "correct_category": "normal",
            "correct_priority": "medium",
        },
        {
            "id": "m004",
            "subject": "Congratulations — you've been selected!",
            "sender": "noreply@prizeclaim-winner.net",
            "body": (
                "You are our lucky winner! Claim your $1,000 Amazon gift card now. "
                "Click here within 24 hours. This is not spam."
            ),
            "timestamp": "2024-03-15T13:00:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "spam",
            "correct_priority": "low",
        },
        {
            "id": "m005",
            "subject": "Product roadmap feedback request",
            "sender": "pm@company.com",
            "body": (
                "Hi, the product team is collecting input for the H2 roadmap. "
                "Please share your top 3 feature priorities by Friday. "
                "Google form attached. Thanks!"
            ),
            "timestamp": "2024-03-15T14:00:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "normal",
            "correct_priority": "medium",
        },
        {
            "id": "m006",
            "subject": "Customer complaint — order #98231",
            "sender": "support@company.com",
            "body": (
                "Customer Maria Garcia is unhappy with order #98231 (wrong item shipped). "
                "She has requested a refund and escalated on Twitter. "
                "Please review and respond within 2 hours per SLA."
            ),
            "timestamp": "2024-03-15T15:00:00Z",
            "thread_length": 4,
            "has_attachments": False,
            "correct_category": "urgent",
            "correct_priority": "high",
        },
        {
            "id": "m007",
            "subject": "DevOps Monthly Digest",
            "sender": "digest@devopsweekly.com",
            "body": (
                "Top stories this month: Kubernetes 1.30 release notes, "
                "Terraform best practices, and a spotlight on eBPF. "
                "View online | Unsubscribe"
            ),
            "timestamp": "2024-03-15T16:00:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "newsletter",
            "correct_priority": "low",
        },
        {
            "id": "m008",
            "subject": "Re: Re: Re: Onboarding docs update",
            "sender": "hr@company.com",
            "body": (
                "Thanks for reviewing. I've addressed all comments. "
                "Can you do a final check and merge when ready? No rush — just before end of sprint. "
                "Cheers"
            ),
            "timestamp": "2024-03-15T17:00:00Z",
            "thread_length": 5,
            "has_attachments": False,
            "correct_category": "follow_up",
            "correct_priority": "low",
        },
    ],

    "hard": [
        {
            "id": "h001",
            "subject": "Re: Deployment — quick question",
            "sender": "dev@partner-org.com",
            "body": (
                "Hey, the new build we discussed has been deployed to staging. "
                "The smoke tests passed, but we saw a 15% increase in p99 latency. "
                "Might be infra noise, but thought you should know before we promote to prod tonight."
            ),
            "timestamp": "2024-03-15T17:55:00Z",
            "thread_length": 6,
            "has_attachments": False,
            "correct_category": "urgent",
            "correct_priority": "high",
        },
        {
            "id": "h002",
            "subject": "Just checking in :)",
            "sender": "recruiter@talentbridge.io",
            "body": (
                "Hi! I came across your profile and think you'd be a great fit for some exciting opportunities. "
                "Would love to connect for a 15-min chat. No pressure!"
            ),
            "timestamp": "2024-03-15T10:00:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "spam",
            "correct_priority": "low",
        },
        {
            "id": "h003",
            "subject": "Q2 OKR alignment — please read",
            "sender": "cto@company.com",
            "body": (
                "Team, as we head into Q2 I want to make sure our OKRs are tight. "
                "I've drafted the engineering OKRs in Notion (link below). "
                "Please review and add comments by Monday EOD — this sets our direction for the quarter."
            ),
            "timestamp": "2024-03-15T08:30:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "urgent",
            "correct_priority": "high",
        },
        {
            "id": "h004",
            "subject": "Invoice reminder",
            "sender": "accounts@vendor-svc.com",
            "body": (
                "This is a reminder that invoice INV-2024-0321 ($890) was due on March 10. "
                "Please arrange payment at your earliest convenience to avoid late fees."
            ),
            "timestamp": "2024-03-15T09:15:00Z",
            "thread_length": 2,
            "has_attachments": True,
            "correct_category": "follow_up",
            "correct_priority": "medium",
        },
        {
            "id": "h005",
            "subject": "Action required: renew SSL certificate",
            "sender": "certbot@letsencrypt.org",
            "body": (
                "Your SSL certificate for api.company.com will expire in 14 days (March 29). "
                "Auto-renewal failed due to DNS validation error. "
                "Manual intervention required."
            ),
            "timestamp": "2024-03-15T06:00:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "urgent",
            "correct_priority": "high",
        },
        {
            "id": "h006",
            "subject": "Great article on system design!",
            "sender": "newsletter@bytebytego.com",
            "body": (
                "This week: how Netflix handles billions of requests, "
                "a deep dive on consistent hashing, and Alex Xu's new book announcement."
            ),
            "timestamp": "2024-03-15T07:00:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "newsletter",
            "correct_priority": "low",
        },
        {
            "id": "h007",
            "subject": "Re: Meeting notes from standup",
            "sender": "scrum-master@company.com",
            "body": (
                "Notes from today: we agreed to move ticket ENG-441 to next sprint. "
                "Please update your JIRA tickets accordingly. Nothing blocking."
            ),
            "timestamp": "2024-03-15T10:45:00Z",
            "thread_length": 3,
            "has_attachments": False,
            "correct_category": "normal",
            "correct_priority": "low",
        },
        {
            "id": "h008",
            "subject": "FINAL NOTICE: Account suspension",
            "sender": "security@paypai-alerts.com",
            "body": (
                "Your account has been suspended. Verify your identity immediately to avoid permanent closure. "
                "Click here: http://paypai-verify.net/login"
            ),
            "timestamp": "2024-03-15T11:30:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "spam",
            "correct_priority": "low",
        },
        {
            "id": "h009",
            "subject": "Heads up: on-call handoff tonight",
            "sender": "alice@company.com",
            "body": (
                "Hey, handing off on-call at 18:00 UTC. Current active incidents: none. "
                "Known flaky: the cron job for report generation. Ping me if anything comes up."
            ),
            "timestamp": "2024-03-15T16:00:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "normal",
            "correct_priority": "medium",
        },
        {
            "id": "h010",
            "subject": "Partnership proposal",
            "sender": "bizdev@newstartup.ai",
            "body": (
                "Hi, I'm the co-founder of NewStartup.ai. "
                "We'd love to explore a strategic partnership. "
                "Would you be open to a 30-minute intro call next week?"
            ),
            "timestamp": "2024-03-15T14:00:00Z",
            "thread_length": 1,
            "has_attachments": True,
            "correct_category": "follow_up",
            "correct_priority": "low",
        },
        {
            "id": "h011",
            "subject": "Re: Performance review — self-assessment due",
            "sender": "hr@company.com",
            "body": (
                "Reminder: your self-assessment for the annual performance review is due by March 20. "
                "The review window opens April 1. This is required for your comp cycle."
            ),
            "timestamp": "2024-03-15T09:00:00Z",
            "thread_length": 2,
            "has_attachments": False,
            "correct_category": "urgent",
            "correct_priority": "medium",
        },
        {
            "id": "h012",
            "subject": "Your GitHub Actions minutes are almost exhausted",
            "sender": "noreply@github.com",
            "body": (
                "You've used 90% of your included Actions minutes for this billing cycle. "
                "Your workflows will stop running when the limit is reached. "
                "Upgrade your plan or add a payment method to continue."
            ),
            "timestamp": "2024-03-15T12:00:00Z",
            "thread_length": 1,
            "has_attachments": False,
            "correct_category": "urgent",
            "correct_priority": "medium",
        },
    ],
}


# ── Reward / Grader ──────────────────────────────────────────────────────────

CATEGORY_WEIGHT = 0.6
PRIORITY_WEIGHT = 0.3
SUMMARY_WEIGHT  = 0.1

PENALTY_WRONG_CATEGORY = -0.3
PENALTY_LONG_SUMMARY   = -0.1
BONUS_HIGH_ACCURACY    =  0.5
ACCURACY_THRESHOLD     =  0.80


def _summary_relevance_score(summary: str, email: dict) -> float:
    """Heuristic: does the summary mention keywords from subject/body?"""
    if not summary.strip():
        return 0.01
    combined = (email["subject"] + " " + email["body"]).lower()
    summary_words = set(summary.lower().split())
    # Pick content words from email (len > 4)
    content_words = {w.strip(".,!?:;") for w in combined.split() if len(w) > 4}
    if not content_words:
        return 0.5
    overlap = summary_words & content_words
    score = min(1.0, len(overlap) / max(1, min(5, len(content_words) // 3)))
    return score


def grade_action(action: EmailTriageAction, email: dict, task_id: str) -> Tuple[float, str]:
    """
    Grade a single classification action.

    Returns
    -------
    reward : float  — step reward in range [-0.3, 1.0]
    feedback : str  — human-readable explanation
    """
    reward = 0.0
    messages = []

    correct_cat = email["correct_category"]
    correct_pri = email["correct_priority"]

    # Category score
    if action.category == correct_cat:
        reward += CATEGORY_WEIGHT
        messages.append(f"✓ Category '{action.category}' correct (+{CATEGORY_WEIGHT})")
    else:
        reward += PENALTY_WRONG_CATEGORY
        messages.append(
            f"✗ Category '{action.category}' wrong (expected '{correct_cat}') ({PENALTY_WRONG_CATEGORY})"
        )

    # Priority score
    if action.priority == correct_pri:
        reward += PRIORITY_WEIGHT
        messages.append(f"✓ Priority '{action.priority}' correct (+{PRIORITY_WEIGHT})")
    else:
        # Hard mode: partial credit only if adjacent
        if task_id != "hard":
            adjacent = {
                "high": ["medium"],
                "medium": ["high", "low"],
                "low": ["medium"],
            }
            if action.priority in adjacent.get(correct_pri, []):
                partial = PRIORITY_WEIGHT * 0.5
                reward += partial
                messages.append(f"~ Priority '{action.priority}' adjacent to '{correct_pri}' (+{partial:.2f})")
            else:
                messages.append(f"✗ Priority '{action.priority}' wrong (expected '{correct_pri}') (+0)")
        else:
            messages.append(f"✗ Priority '{action.priority}' wrong in hard mode (expected '{correct_pri}') (+0)")

    # Summary relevance
    summary_score = _summary_relevance_score(action.summary, email) * SUMMARY_WEIGHT
    reward += summary_score
    messages.append(f"~ Summary relevance: +{summary_score:.2f}")

    # Penalty: summary too long
    if len(action.summary) > 300:
        reward += PENALTY_LONG_SUMMARY
        messages.append(f"✗ Summary too long (>300 chars) ({PENALTY_LONG_SUMMARY})")

    reward = round(max(-0.49, min(0.99, reward)), 4)
    return reward, " | ".join(messages)


# ── Environment class ────────────────────────────────────────────────────────

class EmailTriageEnvironment:
    """Stateful Email Triage environment."""

    def __init__(self):
        self._state = EmailTriageState()
        self._emails: List[dict] = []

    # ── Public API ───────────────────────────────────────────────────────────

    def reset(self, task_id: str = "easy") -> Tuple[EmailObservation, dict]:
        """Reset environment for a new episode."""
        if task_id not in EMAILS:
            task_id = "easy"
        emails = EMAILS[task_id].copy()
        random.shuffle(emails)
        self._emails = emails
        self._state = EmailTriageState(
            task_id=task_id,
            total_emails=len(emails),
            current_email_index=0,
        )
        obs = self._make_observation()
        info = {"task_id": task_id, "total_emails": len(emails)}
        return obs, info

    def step(self, action: EmailTriageAction) -> Tuple[EmailObservation, float, bool, dict]:
        """Process one classification action."""
        if self._state.done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        current_email = self._emails[self._state.current_email_index]
        reward, feedback = grade_action(action, current_email, self._state.task_id)

        # Update state
        self._state.cumulative_reward += reward
        self._state.total_classifications += 1
        if action.category == current_email["correct_category"]:
            self._state.correct_classifications += 1
        self._state.episode_actions.append({
            "email_id": current_email["id"],
            "action": action.model_dump(),
            "reward": reward,
            "feedback": feedback,
        })

        self._state.current_email_index += 1
        done = self._state.current_email_index >= self._state.total_emails

        # Episode bonus
        episode_bonus = 0.0
        if done:
            accuracy = (
                self._state.correct_classifications / self._state.total_classifications
                if self._state.total_classifications > 0 else 0.0
            )
            if accuracy >= ACCURACY_THRESHOLD:
                episode_bonus = BONUS_HIGH_ACCURACY
                self._state.cumulative_reward += episode_bonus
            self._state.done = True

        obs = self._make_observation(feedback=feedback) if not done else self._make_terminal_observation(feedback)
        info = {
            "email_id": current_email["id"],
            "step_feedback": feedback,
            "episode_bonus": episode_bonus,
            "cumulative_reward": self._state.cumulative_reward,
            "correct_so_far": self._state.correct_classifications,
        }
        return obs, reward + episode_bonus, done, info

    def state(self) -> EmailTriageState:
        """Return current environment state."""
        return self._state

    def get_task_score(self) -> float:
        """Compute final normalised score, strictly between 0 and 1."""
        if self._state.total_classifications == 0:
            return 0.05
        max_possible = self._state.total_emails * 1.0 + BONUS_HIGH_ACCURACY
        if max_possible <= 0:
            return 0.05
        raw = self._state.cumulative_reward / max_possible
        # Clamp strictly between 0 and 1 (not 0.0, not 1.0)
        score = max(0.05, min(0.95, raw))
        return round(score, 4)
    
    def _make_observation(self, feedback: Optional[str] = None) -> EmailObservation:
        if self._state.current_email_index >= len(self._emails):
            return self._make_terminal_observation(feedback)
        email = self._emails[self._state.current_email_index]
        return EmailObservation(
            email_id=email["id"],
            subject=email["subject"],
            sender=email["sender"],
            body=email["body"],
            timestamp=email["timestamp"],
            thread_length=email["thread_length"],
            has_attachments=email["has_attachments"],
            feedback=feedback,
            emails_remaining=self._state.total_emails - self._state.current_email_index,
            task_id=self._state.task_id,
        )

    def _make_terminal_observation(self, feedback: Optional[str] = None) -> EmailObservation:
        return EmailObservation(
            email_id="DONE",
            subject="[Episode Complete]",
            sender="system",
            body=(
                f"Episode finished. "
                f"Score: {self._state.correct_classifications}/{self._state.total_classifications} correct. "
                f"Cumulative reward: {self._state.cumulative_reward:.3f}. "
                f"Task score: {self.get_task_score():.4f}"
            ),
            timestamp="",
            thread_length=0,
            has_attachments=False,
            feedback=feedback,
            emails_remaining=0,
            task_id=self._state.task_id,
        )
