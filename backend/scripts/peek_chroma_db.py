import chromadb

client = chromadb.PersistentClient(path="backend/chroma_storage")

collection = client.get_collection("learning_aid_chunks")

print("Count:", collection.count())

print(collection.peek())
