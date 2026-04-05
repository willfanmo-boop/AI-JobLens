import chromadb

client = chromadb.PersistentClient(path="./vector_db")

# client.delete_collection(name="job")
collections = client.list_collections()

for collection in collections:
    print(collection)
    print(collection.count())

