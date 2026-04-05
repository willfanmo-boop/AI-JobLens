import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
import pandas as pd


load_dotenv()

# Chat model
from langchain_openai import ChatOpenAI
model = ChatOpenAI(model="gpt-3.5-turbo")

# Embedding model
from langchain_openai import OpenAIEmbeddings
embedding = OpenAIEmbeddings(model="text-embedding-3-small")

# Resume Vector store
from langchain_chroma import Chroma
resume_vectorstore = Chroma(
    collection_name="resume",
    embedding_function=embedding,
    persist_directory="./vector_db"
)

# Job Vector store
job_vectorstore = Chroma(
    collection_name="job",
    embedding_function=embedding,
    persist_directory="./vector_db"
)


# Retriever tools
@tool
def resume_retriever(query: str, k_results: int = 3) -> str:
    """
    Look up the user's personal background, skills, and work experience from their resume.
    Args:
        query: The search query.
        k_results: Number of resume snippets to retrieve. Default is 3. Provide a higher number if you need more context.
    """
    retrieved_docs = resume_vectorstore.similarity_search(query, k=k_results)
    #print(retrieved_docs)
    return "\n\n".join(
        f"Source: {doc.metadata}\nContent: {doc.page_content}"
        for doc in retrieved_docs
    )

@tool
def chroma_job_retriever(query: str, k_results: int = 3) -> str:
    """
    Search for specific job descriptions or find jobs that semantically match a resume.
    Args:
        query: The search query describing the job or skills.
        k_results: Number of jobs to retrieve. Default is 3. Pass 5 or 10 if the user asks for 'many' or 'all' options.
    """
    retrieved_docs = job_vectorstore.similarity_search(query, k=k_results)
    #print(retrieved_docs)
    return "\n\n".join(
        f"Source: {doc.metadata}\nContent: {doc.page_content}"
        for doc in retrieved_docs
    )

# Load Json Data for this specific tool
df = pd.read_json("./data/jobs.json")
panda_agent = create_pandas_dataframe_agent(
    ChatOpenAI(temperature=0, model="gpt-4o-mini"),  # model 
    df,  # dataframe 
    verbose=False,  # print the agent's thought process 
    agent_type="openai-tools",  # agent type 
    allow_dangerous_code=True,  # allow dangerous code 
)
    
@tool 
def pandas_job_retriever(query: str) -> str:
    """
    Use this for statistical, analytical, or quantitative queries about the overall job market.
    E.g., counting jobs, calculating averages, or finding the most common skills.
    Args:
        query: The analytical question to ask the data analyst.
    """
    response = panda_agent.invoke(query)
    return response['output']


# Agent 
from langchain.agents import create_agent

tools = [resume_retriever, chroma_job_retriever, pandas_job_retriever]
system_prompt = (
    "You are a professional AI Career Assistant. Your goal is to help users analyze the job market, "
    "match candidates to roles, and answer career-related questions accurately.\n\n"
    "You have access to three distinct tools. It is CRITICAL that you route questions to the correct tool:\n"
    "1. `resume_retriever`: Use this ONLY to look up the user's personal background, skills, and work experience.\n"
    "2. `chroma_job_retriever`: Use this ONLY when searching for specific job descriptions, looking up job details, "
    "or finding jobs that semantically match a resume. You can control how many jobs to fetch using the `k_results` parameter (default 3, increase if user asks for more options).\n"
    "3. `pandas_job_retriever`: Use this ONLY for statistical, analytical, or quantitative queries about the overall job market "
    "(e.g., 'What are the most popular skills overall?', 'How many remote jobs are there?', 'What is the top hiring company?').\n\n"
    "Carefully evaluate the user's query. If it involves aggregations, counts, or overall trends, ALWAYS default to `pandas_job_retriever`. "
    "If it involves finding matching texts or semantic search, use `chroma_job_retriever`. If the information cannot be found, say so."
)

agent = create_agent(
    model, 
    tools, 
    system_prompt=system_prompt
)

from langchain_core.messages import HumanMessage

chat_history = []
print("\n💬 AI Career Assistant is running! (Type 'quit' or 'exit' to stop)")

while True:
    content = input("\nYou: ")
    if content.lower() in ['quit', 'exit']:
        print("Goodbye!")
        break
    
    if content.lower() in ['clear', 'clean']:
        chat_history = []
        print("Chat history cleared.")
    
    if content.lower() in ['chathistory']:
        for item in chat_history:
            print(item.content)
        continue
        
    chat_history.append(HumanMessage(content=content))
    
    try:
        result = agent.invoke({
            "messages": chat_history[-10:]
        })
        
        # Get final response and add it to history to form the memory loop
        ai_response = result["messages"][-1]
        print(f"\nAI: {ai_response.content}")
        
        chat_history.append(ai_response)
        
    except Exception as e:
        print(f"\n[Error during execution]: {e}")
        # If there's an error, pop the last user message so they can try again.
        chat_history.pop()