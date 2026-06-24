import os
import logging
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from db.session import engine

load_dotenv()

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VECTOR_DB_PATH = os.path.join(_BASE_DIR, "vector_db")
COLLECTION_NAME = "job"


def index_jobs() -> int:
    logger.info("Loading jobs from MySQL for indexing...")
    df = pd.read_sql("SELECT * FROM jobs", engine)

    if df.empty:
        logger.warning("No jobs found in MySQL to index")
        return 0

    documents = []
    for _, row in df.iterrows():
        page_content = (
            f"Job Title: {row.get('title', 'Unknown')}\n"
            f"Company: {row.get('company', 'Unknown')}\n"
            f"Location: {row.get('location', '')}\n"
            f"Job Type: {row.get('job_type', '')}\n"
            f"Level: {row.get('job_level', '')}\n"
            f"Remote: {row.get('is_remote', False)}\n"
            f"Description: {row.get('description', '')}"
        )
        metadata = {
            "title":    str(row.get("title", "")),
            "company":  str(row.get("company", "")),
            "url":      str(row.get("job_url", "")),
            "location": str(row.get("location", "")),
            "level":    str(row.get("job_level", "")),
            "source":   str(row.get("source", "")),
        }
        documents.append(Document(page_content=page_content, metadata=metadata))

    logger.info(f"Embedding {len(documents)} job documents into Chroma...")
    embedding = OpenAIEmbeddings(model="text-embedding-3-small")

    # Delete existing collection and recreate for a clean re-index
    existing = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embedding,
        persist_directory=VECTOR_DB_PATH,
    )
    existing.delete_collection()

    Chroma.from_documents(
        documents=documents,
        embedding=embedding,
        collection_name=COLLECTION_NAME,
        persist_directory=VECTOR_DB_PATH,
    )
    logger.info(f"Successfully indexed {len(documents)} jobs into Chroma")
    return len(documents)
