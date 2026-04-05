import json
import csv
import os
import logging

logger = logging.getLogger(__name__)


def load_existing(json_path: str) -> list[dict]:
    """Load existing scraped jobs from JSON (for resuming interrupted runs)."""
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} existing jobs from {json_path}")
        return data
    return []


def save_json(jobs: list[dict], json_path: str):
    """Overwrite the JSON checkpoint with the full current job list."""
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(jobs)} jobs → {json_path}")


def save_csv(jobs: list[dict], csv_path: str):
    """Write all jobs to a CSV file (overwrites each time for simplicity)."""
    if not jobs:
        return
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    fieldnames = ["title", "company", "location", "job_type",
                  "experience_level", "posted_time", "applicants_count", "url"]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(jobs)
    logger.info(f"Saved {len(jobs)} jobs → {csv_path}")
