import asyncio
import os
import logging
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langgraph.prebuilt import create_react_agent

from db.crud import jobs_to_dataframe

load_dotenv()

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VECTOR_DB_PATH = os.path.join(_BASE_DIR, "vector_db")

chat_model = ChatOpenAI(model="gpt-4o-mini")
embedding = OpenAIEmbeddings(model="text-embedding-3-small")

resume_vectorstore = Chroma(
    collection_name="resume",
    embedding_function=embedding,
    persist_directory=VECTOR_DB_PATH,
)

job_vectorstore = Chroma(
    collection_name="job",
    embedding_function=embedding,
    persist_directory=VECTOR_DB_PATH,
)


@tool
def resume_retriever(query: str, k_results: int = 3) -> str:
    """
    Look up the user's personal background, skills, and work experience from their resume.
    k_results: Number of resume snippets to retrieve.
    """
    docs = resume_vectorstore.similarity_search(query, k=k_results)
    return "\n\n".join(
        f"Source: {d.metadata}\nContent: {d.page_content}" for d in docs
    )


@tool
def chroma_job_retriever(query: str, k_results: int = 3) -> str:
    """
    Search for specific job descriptions or find jobs that semantically match a resume.
    k_results: Number of jobs to retrieve. Increase if user asks for more options.
    """
    docs = job_vectorstore.similarity_search(query, k=k_results)
    return "\n\n".join(
        f"Source: {d.metadata}\nContent: {d.page_content}" for d in docs
    )


@tool
async def pandas_job_retriever(query: str) -> str:
    """
    Use for statistical, analytical, or quantitative queries about the overall job market.
    E.g., counting jobs, calculating averages, finding most common skills, or salary ranges.
    query: The analytical question to ask the data analyst.
    """
    try:
        df = await jobs_to_dataframe()
    except Exception as e:
        logger.error(f"Failed to load jobs from MySQL: {e}")
        return f"Error loading job data: {e}"

    if df.empty:
        return "No job data available. Use POST /jobs/fetch to load jobs first."

    pandas_agent = create_pandas_dataframe_agent(
        ChatOpenAI(temperature=0, model="gpt-4o-mini"),
        df,
        verbose=False,
        agent_type="openai-tools",
        allow_dangerous_code=True,
    )
    response = await asyncio.to_thread(pandas_agent.invoke, query)
    return response["output"]


SYSTEM_PROMPT = SystemMessage(content=(
    "You are a professional AI Career Assistant. Your goal is to help users analyze the job market, "
    "match candidates to roles, and answer career-related questions accurately.\n\n"
    "You have access to three distinct tools. Route questions to the correct tool:\n"
    "1. `resume_retriever`: Use ONLY to look up the user's personal background, skills, and work experience.\n"
    "2. `chroma_job_retriever`: Use ONLY when searching for specific job descriptions, or finding jobs that "
    "semantically match a resume. Use `k_results` to control how many results to fetch.\n"
    "3. `pandas_job_retriever`: Use ONLY for statistical or quantitative queries about the overall job market "
    "(e.g., 'How many remote jobs are there?', 'What are the most common skills?', 'What is the salary range?').\n\n"
    "Routing rules:\n"
    "- Skills / trends / market questions → use `pandas_job_retriever` AND `chroma_job_retriever` together.\n"
    "- 'Find me jobs' / 'what matches my resume' → `chroma_job_retriever`.\n"
    "- Anything about the user's own experience → `resume_retriever`.\n\n"
    "If a tool returns no results, say so honestly. Never fabricate job listings."
))

tools = [resume_retriever, chroma_job_retriever, pandas_job_retriever]

agent = create_react_agent(
    model=chat_model,
    tools=tools,
    prompt=SYSTEM_PROMPT,
)
