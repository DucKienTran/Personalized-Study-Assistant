import chromadb
from pymongo import MongoClient
from redis import Redis

from app.core.database import SessionLocal
from app.models.document_model import Document
from app.models.notebook_model import Notebook
from app.models.user_model import Permission, Role, User


def inspect_mysql():
    print("=" * 60)
    print("MYSQL")
    print("=" * 60)

    db = SessionLocal()

    try:
        print(f"Users       : {db.query(User).count()}")
        print(f"Roles       : {db.query(Role).count()}")
        print(f"Permissions : {db.query(Permission).count()}")
        print(f"Documents   : {db.query(Document).count()}")
        print(f"Notebooks   : {db.query(Notebook).count()}")

    finally:
        db.close()


def inspect_redis():
    print("\n" + "=" * 60)
    print("REDIS")
    print("=" * 60)

    try:
        client = Redis(host="redis", port=6379, decode_responses=True)

        print(f"Keys: {client.dbsize()}")

        keys = client.keys("*")[:20]

        if keys:
            print("Sample keys:")
            for k in keys:
                print(f"  - {k}")
        else:
            print("No keys.")

    except Exception as e:
        print(e)


def inspect_mongodb():
    print("\n" + "=" * 60)
    print("MONGODB")
    print("=" * 60)

    try:
        client = MongoClient("mongodb://mongodb:27017")

        db = client["learning_aid"]

        collections = db.list_collection_names()

        if not collections:
            print("No collections.")
            return

        for c in collections:
            print(f"{c}: {db[c].count_documents({})}")

    except Exception as e:
        print(e)


def inspect_chroma():
    print("\n" + "=" * 60)
    print("CHROMADB")
    print("=" * 60)

    try:
        client = chromadb.PersistentClient(path="/app/chroma_data")

        collections = client.list_collections()

        if not collections:
            print("No collections.")
            return

        for c in collections:
            print(f"{c.name}: {c.count()} vectors")

    except Exception as e:
        print(e)


if __name__ == "__main__":
    inspect_mysql()
    inspect_redis()
    inspect_mongodb()
    inspect_chroma()
