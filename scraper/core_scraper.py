import re
import random
import logging
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from scraper import job_storage as JobStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DATA_DIR  = "./data"
JSON_PATH = f"{DATA_DIR}/jobs.json"
CSV_PATH  = f"{DATA_DIR}/jobs.csv"

JOBS_PER_PAGE = 25

class LinkedInScraper:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None

    def initialize(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        self.page.set_extra_http_headers({
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )
        })
        logger.info("Browser initialized successfully")

    def login(self, email: str, password: str):
        logger.info("Starting LinkedIn login...")
        self.page.goto('https://www.linkedin.com/login')
        self.page.wait_for_timeout(2000)
        self.page.fill('input#username', email)
        self.page.fill('input#password', password)
        self.page.click('button[type="submit"]')
        self.page.wait_for_timeout(3000)
        logger.info("Login complete")

    def build_search_url(self, experience_level: str, location: str,
                         keywords: str, start: int = 0) -> str:
        encoded_keywords = quote(keywords)
        url = (
            f"https://www.linkedin.com/jobs/search/?"
            f"f_E={experience_level}"
            f"&geoId={location}"
            f"&keywords={encoded_keywords}"
            f"&start={start}"
        )
        logger.info(f"Search URL (start={start}): {url}")
        return url

    def _human_delay(self, min_ms: int = 3000, max_ms: int = 8000):
        delay = random.randint(min_ms, max_ms)
        self.page.wait_for_timeout(delay)

    def _extract_card_info(self, card) -> dict:
        card_link = card.locator('a').first.get_attribute('href') or ""
        if card_link and not card_link.startswith("http"):
            card_link = "https://www.linkedin.com" + card_link
        card_link = card_link.split("?")[0]

        card_text = card.inner_text()
        lines = [ln.strip() for ln in card_text.split('\n') if ln.strip()]

        title    = lines[0] if len(lines) > 0 else "Unknown"
        company  = lines[2] if len(lines) > 2 else "Unknown"
        location = lines[3] if len(lines) > 3 else "Unknown"

        return {
            "title":    title,
            "company":  company,
            "location": location,
            "url":      card_link,
        }

    def _extract_detail_info(self) -> dict:
        detail = {
            "job_type":         "Unknown",
            "experience_level": "Unknown",
            "posted_time":      "Unknown",
            "applicants_count": "Unknown",
            "description":      "",
        }
        try:
            self.page.wait_for_selector('#job-details', timeout=7000)

            detail["description"] = (
                self.page.locator('#job-details').inner_text().strip()
            )

            try:
                criteria_items = self.page.locator(
                    '.job-details-jobs-unified-top-card__job-insight'
                ).all_inner_texts()
                for item in criteria_items:
                    t = item.strip()
                    if any(x in t for x in ["Full-time", "Part-time", "Contract",
                                             "Temporary", "Internship"]):
                        detail["job_type"] = t
                    if any(x in t for x in ["Entry level", "Mid-Senior",
                                             "Associate", "Director", "Executive"]):
                        detail["experience_level"] = t
            except Exception:
                pass

            try:
                top_card_text = self.page.locator(
                    '.job-details-jobs-unified-top-card__primary-description-container'
                ).inner_text()
                time_match = re.search(
                    r'(\d+\s+(?:minute|hour|day|week|month)s?\s+ago)', top_card_text
                )
                if time_match:
                    detail["posted_time"] = time_match.group(1)

                app_match = re.search(
                    r'((?:Over\s+)?\d+[\+]?\s+applicants?)', top_card_text,
                    re.IGNORECASE
                )
                if app_match:
                    detail["applicants_count"] = app_match.group(1)
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"Failed to load details: {e}")

        return detail

    def scrape_all_jobs(
        self,
        experience_level: str,
        location: str,
        keywords: str,
        target_count: int = 250,
    ) -> list[dict]:
        jobs: list[dict] = JobStorage.load_existing(JSON_PATH)
        seen_urls: set[str] = {j["url"] for j in jobs}
        logger.info(f"Target count: {target_count}, Currently have: {len(jobs)}")

        page_offset = (len(jobs) // JOBS_PER_PAGE) * JOBS_PER_PAGE

        while len(jobs) < target_count:
            url = self.build_search_url(experience_level, location,
                                        keywords, start=page_offset)
            self.page.goto(url)

            try:
                self.page.wait_for_selector('.job-card-container', timeout=15000)
            except Exception:
                logger.warning(f"No job cards found at start={page_offset}, probably reached the last page. Stopping.")
                break

            for _ in range(5):
                try:
                    self.page.locator('.job-card-container').last.scroll_into_view_if_needed(timeout=2000)
                except Exception:
                    pass
                self.page.wait_for_timeout(1000)

            job_cards = self.page.locator('.job-card-container')
            count = job_cards.count()
            logger.info(f"Page {page_offset // JOBS_PER_PAGE + 1}, total {count} cards")

            if count == 0:
                logger.info("No job cards on current page, stopping scraping")
                break

            page_new = 0
            for i in range(count):
                if len(jobs) >= target_count:
                    break

                card = self.page.locator('.job-card-container').nth(i)
                
                try:
                    card.scroll_into_view_if_needed(timeout=2000)
                except Exception as e:
                    logger.warning(f"Failed to scroll to card {i+1} (DOM might have updated): {e}")

                try:
                    basic = self._extract_card_info(card)
                except Exception as e:
                    logger.error(f"Failed to extract basic info for card {i+1}: {e}")
                    continue

                if basic["url"] in seen_urls or not basic["url"]:
                    logger.info(f"Skipping duplicate/empty URL: {basic['url']}")
                    continue

                try:
                    card.click(timeout=3000)
                except Exception as e:
                    logger.warning(f"Failed to click card {i+1}: {e}")
                    continue

                detail = self._extract_detail_info()

                job = {**basic, **detail}
                jobs.append(job)
                seen_urls.add(basic["url"])
                page_new += 1

                logger.info(
                    f"[{len(jobs)}/{target_count}] {job['title']} @ {job['company']} | "
                    f"{job['posted_time']} | {job['applicants_count']}"
                )

                self._human_delay(3000, 8000)

            JobStorage.save_json(jobs, JSON_PATH)
            JobStorage.save_csv(jobs, CSV_PATH)
            logger.info(f"Checkpoint saved, currently a total of {len(jobs)} jobs")

            if page_new == 0:
                logger.warning("No new jobs added from this page, probably reached the end. Stopping.")
                break

            page_offset += JOBS_PER_PAGE
            logger.info("Waiting to turn page...")
            self._human_delay(10000, 15000)

        logger.info(f"Scraping complete, collected {len(jobs)} jobs in total")
        return jobs

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Browser closed")
