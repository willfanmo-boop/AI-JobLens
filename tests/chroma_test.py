import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

# Must use the SAME embedding model as when the collection was created
embedding = OpenAIEmbeddings(model="text-embedding-3-small")

vectorstore = Chroma(
    persist_directory="./vector_db",
    collection_name="resume",
    embedding_function=embedding
)

query = input("Ask a question about the resume:")
number = int(input("How many results do you want to retrieve?"))
results = vectorstore.similarity_search_with_score(query,k=number)
for result,score in results:
    print("==================================================")
    print("Score:"+ str(score))
    print("Page_content:"+str(result.page_content))
    print("Metadata:"+str(result.metadata))