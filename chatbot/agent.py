import os
import pandas as pd
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.agents import create_agent

load_dotenv()

chat_model = ChatOpenAI(model="gpt-4o-mini")
embedding = OpenAIEmbeddings(model="text-embedding-3-small")

resume_vectorstore = Chroma(
    collection_name="resume",
    embedding_function=embedding,
    persist_directory="./vector_db",
)

job_vectorstore = Chroma(
    collection_name="job",
    embedding_function=embedding,
    persist_directory="./vector_db",
)

jobs_json_path = "./data/jobs.json"
df = pd.read_json(jobs_json_path) if os.path.exists(jobs_json_path) else pd.DataFrame()

pandas_agent = create_pandas_dataframe_agent(
    ChatOpenAI(temperature=0, model="gpt-4o-mini"),
    df,
    verbose=False,
    agent_type="openai-tools",
    allow_dangerous_code=True,
)

@tool
def resume_retriever(query: str, k_results: int = 3) -> str:
    """
    Look up the user's personal background, skills, and work experience from their resume.
    Args:
        query: The search query.
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
    Args:
        query: The search query describing the job or skills.
        k_results: Number of jobs to retrieve. Increase if user asks for more options.
    """
    docs = job_vectorstore.similarity_search(query, k=k_results)
    return "\n\n".join(
        f"Source: {d.metadata}\nContent: {d.page_content}" for d in docs
    )


@tool
def pandas_job_retriever(query: str) -> str:
    """
    Use for statistical, analytical, or quantitative queries about the overall job market.
    E.g., counting jobs, calculating averages, or finding the most common skills.
    Args:
        query: The analytical question to ask the data analyst.
    """
    if df.empty:
        return "No job data available."
    response = pandas_agent.invoke(query)
    return response["output"]


SYSTEM_PROMPT = (
    "You are a professional AI Career Assistant. Your goal is to help users analyze the job market, "
    "match candidates to roles, and answer career-related questions accurately.\n\n"
    "You have access to three distinct tools. Route questions to the correct tool:\n"
    "1. `resume_retriever`: Use ONLY to look up the user's personal background, skills, and work experience.\n"
    "2. `chroma_job_retriever`: Use ONLY when searching for specific job descriptions, or finding jobs that "
    "semantically match a resume. Use `k_results` to control how many results to fetch.\n"
    "3. `pandas_job_retriever`: Use ONLY for statistical or quantitative queries about the overall job market "
    "(e.g., 'How many remote jobs are there?', 'What are the most common skills?').\n\n"
    "If the query involves aggregations, counts, or trends — use `pandas_job_retriever`. "
    "If it involves semantic search or finding matching jobs — use `chroma_job_retriever`. "
    "If it is about the user's background — use `resume_retriever`."
)

tools = [resume_retriever, chroma_job_retriever, pandas_job_retriever]

agent = create_agent(
    chat_model,
    tools,
    system_prompt = SYSTEM_PROMPT
)
