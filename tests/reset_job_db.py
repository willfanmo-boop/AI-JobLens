import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()

embedding = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = Chroma(
    persist_directory="./vector_db",
    collection_name="job",
    embedding_function=embedding
)

try:
    print(f"Deleting Vectordb....")
    vectorstore.delete_collection()
    print("Vectordb Deleted! ")
except Exception as e:
    print(f"{e}")
