"""
Pydantic models for the Email Triage OpenEnv environment.
Defines Action, Observation, and State types.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ── Action ─────────────────────────────────────────────────────────────────

class EmailTriageAction(BaseModel):
    """Action the agent takes: classify an email."""
    category: Literal["urgent", "normal", "spam", "newsletter", "follow_up"] = Field(
        ...,
        description="Primary category assigned to the email"
    )
    priority: Literal["high", "medium", "low"] = Field(
        ...,
        description="Urgency/priority level of the email"
    )
    summary: str = Field(
        ...,
        max_length=300,
        description="A brief 1-2 sentence summary of the email content"
    )
    suggested_action: str = Field(
        ...,
        max_length=200,
        description="What the user should do with this email (e.g. 'Reply within 24 hours')"
    )


# ── Observation ─────────────────────────────────────────────────────────────

class EmailObservation(BaseModel):
    """What the agent sees each step."""
    email_id: str = Field(..., description="Unique identifier for the current email")
    subject: str = Field(..., description="Email subject line")
    sender: str = Field(..., description="Sender email address")
    body: str = Field(..., description="Full email body text")
    timestamp: str = Field(..., description="ISO-8601 timestamp when email was received")
    thread_length: int = Field(default=1, description="Number of messages in thread")
    has_attachments: bool = Field(default=False, description="Whether email has attachments")
    # Feedback from previous step (empty on first step)
    feedback: Optional[str] = Field(default=None, description="Feedback from previous classification")
    emails_remaining: int = Field(default=0, description="How many emails are left in this task")
    task_id: str = Field(default="easy", description="Current task difficulty level")


# ── State ───────────────────────────────────────────────────────────────────

class EmailTriageState(BaseModel):
    """Internal state of the environment (server-side)."""
    task_id: str = Field(default="easy", description="Task difficulty: easy | medium | hard")
    current_email_index: int = Field(default=0, description="Index of current email in queue")
    total_emails: int = Field(default=0, description="Total emails in this episode")
    correct_classifications: int = Field(default=0, description="Running count of correct calls")
    total_classifications: int = Field(default=0, description="Running count of all classifications")
    cumulative_reward: float = Field(default=0.0, description="Total reward so far")
    done: bool = Field(default=False, description="Whether episode has ended")
    episode_actions: List[dict] = Field(default_factory=list, description="Log of all actions taken")
