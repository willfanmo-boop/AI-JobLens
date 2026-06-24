import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy import select, func

from db.models import Job, Session
from db.session import AsyncSessionLocal



# ── Jobs ──────────────────────────────────────────────────────────────────────
async def upsert_jobs(db: AsyncSession, job_dicts: list[dict]) -> int:
    if not job_dicts:
        return 0
    rows = [_to_row(j) for j in job_dicts if j.get("job_url")]
    if not rows:
        return 0
    stmt = mysql_insert(Job).values(rows).prefix_with("IGNORE")
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


async def list_jobs(db: AsyncSession, limit: int = 100, offset: int = 0) -> list[Job]:
    stmt = select(Job).order_by(Job.date_posted.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_jobs(db: AsyncSession) -> int:
    stmt = select(func.count()).select_from(Job)
    result = await db.execute(stmt)
    return result.scalar()


async def jobs_to_dataframe() -> pd.DataFrame:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Job))
        jobs = result.scalars().all()
    return pd.DataFrame(
        [{col.name: getattr(j, col.name) for col in Job.__table__.columns} for j in jobs]
    )


def _to_row(j: dict) -> dict:
    def _float(val):
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    return {
        "source":      str(j.get("site", "")),
        "job_url":     str(j.get("job_url", "")),
        "title":       str(j.get("title", "")) or "Unknown",
        "company":     str(j.get("company", "")) if j.get("company") else None,
        "location":    str(j.get("location", "")) if j.get("location") else None,
        "is_remote":   bool(j.get("is_remote", False)),
        "job_type":    str(j.get("job_type", "")) if j.get("job_type") else None,
        "job_level":   str(j.get("job_level", "")) if j.get("job_level") else None,
        "date_posted": j.get("date_posted"),
        "min_amount":  _float(j.get("min_amount")),
        "max_amount":  _float(j.get("max_amount")),
        "currency":    str(j.get("currency", "")) if j.get("currency") else None,
        "description": str(j.get("description", "")) if j.get("description") else None,
    }

# ── Session ──────────────────────────────────────────────────────────────────────
async def get_session(db: AsyncSession, session_id: str | None = None):
    query = select(Session).where(Session.id == session_id)
    result = await db.execute(query)
    return result.scalars().one_or_none()
