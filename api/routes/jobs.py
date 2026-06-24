import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import JobFetchRequest, JobFetchResponse, JobListResponse, JobRecord
from core.job_fetcher import fetch_and_store_jobs
from db.session import get_db
from db.crud import list_jobs, count_jobs

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/fetch", response_model=JobFetchResponse)
async def fetch_jobs(request: JobFetchRequest):
    """Trigger JobSpy scrape → save to MySQL → re-index into Chroma."""
    try:
        inserted = await fetch_and_store_jobs(
            search_term=request.search_term,
            location=request.location,
            site_names=request.site_names,
            results_wanted=request.results_wanted,
            reindex=True,
        )
        return JobFetchResponse(
            inserted=inserted,
            message=f"Fetched and indexed {inserted} new jobs successfully.",
        )
    except Exception as e:
        logger.error(f"Job fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=JobListResponse)
async def list_jobs_endpoint(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List jobs stored in MySQL with pagination."""
    total = await count_jobs(db)
    jobs = await list_jobs(db, limit=limit, offset=offset)
    return JobListResponse(
        total=total,
        jobs=[JobRecord.model_validate(j) for j in jobs],
    )
