import os
import argparse
from dotenv import load_dotenv

load_dotenv()


def run_scraper():
    from scraper.core_scraper import LinkedInScraper

    email    = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")
    
    if not email or not password:
        raise ValueError("Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables in the .env file!")

    scraper = LinkedInScraper(headless=False)
    scraper.initialize()
    scraper.login(email, password)

    scraper.scrape_all_jobs(
        experience_level="1%2C2",  
        location="104444106",      # Hamilton, Ontario, Canada
        keywords="computer science",
        target_count=250,
    )

    scraper.close()


if __name__ == "__main__":
    run_scraper()

