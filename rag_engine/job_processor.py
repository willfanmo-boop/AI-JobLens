import os
import json
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load Env
load_dotenv()

# Read the json file
json_path = "/Users/fanmo/Desktop/AI_Job_Platform/my_project/data/jobs.json"
with open(json_path, "r", encoding="utf-8") as f:
    jobs_data = json.load(f)

print(f"Loaded {len(jobs_data)} jobs.")

documents = []
for job in jobs_data:
    page_content = (
        f"Job Title: {job.get('title', 'Unknown')}\n"
        f"Company: {job.get('company', 'Unknown')}\n"
        f"Description: {job.get('description', '')}"
    )
    
    metadata = {
        "title": job.get('title', 'Unknown'),
        "company": job.get('company', 'Unknown'),
        "url": job.get('url', ''),
        "location": job.get('location', ''),
        "experience": job.get('experience_level', '')
    }
    
    doc = Document(page_content=page_content, metadata=metadata)
    documents.append(doc)

print(f"Generated {len(documents)} complete job documents. Starting embedding...")

embedding = OpenAIEmbeddings(model="text-embedding-3-small")

try:
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embedding,
        collection_name="job",  
        persist_directory="./vector_db"
    )
    print("Job vector store created successfully!")
except Exception as e:
    print(f"Error creating vector store: {e}")
