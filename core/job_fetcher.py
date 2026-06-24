import asyncio
import logging
from typing import Optional

from jobspy import scrape_jobs

from db.session import AsyncSessionLocal
from db.crud import upsert_jobs
from core.rag.job_indexer import index_jobs

logger = logging.getLogger(__name__)


async def fetch_and_store_jobs(
    search_term: str = "software engineer",
    location: str = "Toronto,Canada",
    site_names: Optional[list[str]] = None,
    results_wanted: int = 50,
    reindex: bool = True,
) -> int:
    if site_names is None:
        site_names = ["linkedin", "indeed"]

    logger.info(f"Fetching jobs: term='{search_term}', location='{location}', sites={site_names}")

    jobs_df = await asyncio.to_thread(
        scrape_jobs,
        site_name=site_names,
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=72,
        country_indeed="Canada",
        linkedin_fetch_description=True,
    )

    if jobs_df.empty:
        logger.warning("No Job Found")
        return 0

    job_dicts = jobs_df.where(jobs_df.notna(), other=None).to_dict(orient="records")
    logger.info(f"Found {len(job_dicts)} jobs")

    async with AsyncSessionLocal() as db:
        inserted = await upsert_jobs(db, job_dicts)

    logger.info(f"Inserted {inserted} new jobs into MySQL")

    if reindex and inserted > 0:
        logger.info("Triggering Chroma re-indexing...")
        await asyncio.to_thread(index_jobs)

    return inserted
