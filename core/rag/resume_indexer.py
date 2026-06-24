import os
import logging
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import MarkdownHeaderTextSplitter

load_dotenv()

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESUME_PATH = os.path.join(_BASE_DIR, "docs", "FanMo_Resume.md")
VECTOR_DB_PATH = os.path.join(_BASE_DIR, "vector_db")
COLLECTION_NAME = "resume"


def index_resume() -> int:
    if not os.path.exists(RESUME_PATH):
        raise FileNotFoundError(f"Resume not found at: {RESUME_PATH}")

    with open(RESUME_PATH, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "H1"), ("##", "H2"), ("###", "H3")],
        return_each_line=False,
        strip_headers=False,
    )
    docs = splitter.split_text(markdown_content)

    if not docs:
        logger.warning("Resume produced no chunks after splitting")
        return 0

    embedding = OpenAIEmbeddings(model="text-embedding-3-small")
    Chroma.from_documents(
        documents=docs,
        embedding=embedding,
        collection_name=COLLECTION_NAME,
        persist_directory=VECTOR_DB_PATH,
    )
    logger.info(f"Indexed {len(docs)} resume chunks into Chroma")
    return len(docs)
