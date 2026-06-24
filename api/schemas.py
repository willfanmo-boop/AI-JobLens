from pydantic import BaseModel
from typing import Optional
from datetime import date


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


class MessageRecord(BaseModel):
    role: str      # "human" or "ai"
    content: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageRecord]


# ── Sessions ──────────────────────────────────────────────────────────────────────
class SessionRecord(BaseModel):
    session_id: str



# ── Jobs ──────────────────────────────────────────────────────────────────────

class JobFetchRequest(BaseModel):
    search_term: str = "software engineer"
    location: str = "Canada"
    site_names: list[str] = ["linkedin", "indeed"]
    results_wanted: int = 50


class JobFetchResponse(BaseModel):
    inserted: int
    message: str


class JobRecord(BaseModel):
    id: int
    source: str
    job_url: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    is_remote: Optional[bool] = None
    job_type: Optional[str] = None
    job_level: Optional[str] = None
    date_posted: Optional[date] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: Optional[str] = None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    total: int
    jobs: list[JobRecord]
