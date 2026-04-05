import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
#from langchain_community.vectorstores import FAISS
from langchain_chroma import Chroma
from langchain_text_splitters import MarkdownHeaderTextSplitter

# Load env
load_dotenv()

# Read the markdown file
markdown_path = "/Users/fanmo/Desktop/AI_Job_Platform/my_project/Docs/FanMo_Resume.md"
with open(markdown_path, "r", encoding="utf-8") as f:
    markdown_content = f.read()

# Headers to split on (we want to track)
headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]

# Initialize the splitter and split the text
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on,
    return_each_line=False,
    strip_headers=False
)

# Define Embedding Model
embedding = OpenAIEmbeddings(
    model = "text-embedding-3-small"
)

# Split the text into chunks
docs = markdown_splitter.split_text(markdown_content)

try:
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embedding,
        # name of the colletion to create
        collection_name="resume",
        # path to save the vector store
        persist_directory="./vector_db"
    )
    print("resume vector store created successfully!")
except Exception as e:
    print(e)



