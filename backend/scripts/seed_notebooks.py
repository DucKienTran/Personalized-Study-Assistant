# scripts/seed_notebooks.py
"""
Seed dữ liệu test cho tính năng Notebook (multi-document).

Yêu cầu: chạy `python -m scripts.seed_users` TRƯỚC để có sẵn user client@example.com.
Chạy: python -m scripts.seed_notebooks
"""

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.document_model import Document
from app.models.notebook_model import Notebook, NotebookDocument
from app.models.user_model import User

# User này được seed sẵn bởi scripts/seed_users.py — không tạo lại ở đây
CLIENT_EMAIL = "client@example.com"

DOCUMENTS = [
    {"title": "Lecture 1.pdf", "file_type": "pdf"},
    {"title": "Lecture 2.pdf", "file_type": "pdf"},
    {"title": "OS Textbook.pdf", "file_type": "pdf"},
    {"title": "ML Slides.pdf", "file_type": "pdf"},
    {"title": "ML Assignment.pdf", "file_type": "pdf"},
]

NOTEBOOKS = [
    {
        "title": "Operating Systems",
        "description": "Bài giảng và textbook môn Hệ điều hành",
        "document_titles": ["Lecture 1.pdf", "Lecture 2.pdf", "OS Textbook.pdf"],
    },
    {
        "title": "Machine Learning",
        "description": "Slides và assignment môn Machine Learning",
        # document cuối để inactive=True để test toggle UI
        "document_titles": ["ML Slides.pdf"],
        "inactive_document_titles": ["ML Assignment.pdf"],
    },
]


def get_client_user(db: Session) -> User:
    user = db.query(User).filter_by(email=CLIENT_EMAIL).first()
    if user is None:
        raise RuntimeError(
            f"Chưa tìm thấy user '{CLIENT_EMAIL}'. "
            "Chạy `python -m scripts.seed_users` trước khi seed notebooks."
        )
    return user


def seed_documents(db: Session, user: User) -> dict[str, Document]:
    print("Seeding documents...")

    documents = {}
    for doc_data in DOCUMENTS:
        doc = (
            db.query(Document)
            .filter_by(user_id=user.id, title=doc_data["title"])
            .first()
        )
        if doc is None:
            doc = Document(
                user_id=user.id,
                title=doc_data["title"],
                file_path=f"uploads/{user.id}/{doc_data['title']}",
                file_type=doc_data["file_type"],
                status="completed",
                total_pages=10,
                total_chunks=20,
                total_characters=5000,
                estimated_tokens=1200,
            )
            db.add(doc)
            db.flush()
            print(f"  [+] Document: {doc.title}")
        else:
            print(f"  [=] Document đã tồn tại: {doc.title}")

        documents[doc_data["title"]] = doc

    return documents


def seed_notebooks(db: Session, user: User, documents: dict[str, Document]):
    print("Seeding notebooks...")

    for nb_data in NOTEBOOKS:
        notebook = (
            db.query(Notebook)
            .filter_by(user_id=user.id, title=nb_data["title"])
            .first()
        )
        if notebook is None:
            notebook = Notebook(
                user_id=user.id,
                title=nb_data["title"],
                description=nb_data["description"],
            )
            db.add(notebook)
            db.flush()
            print(f"  [+] Notebook: {notebook.title}")
        else:
            print(f"  [=] Notebook đã tồn tại: {notebook.title}")

        for title in nb_data.get("document_titles", []):
            _link_document(db, notebook, documents[title], is_active=True)

        for title in nb_data.get("inactive_document_titles", []):
            _link_document(db, notebook, documents[title], is_active=False)


def _link_document(db: Session, notebook: Notebook, document: Document, is_active: bool):
    link = (
        db.query(NotebookDocument)
        .filter_by(notebook_id=notebook.id, document_id=document.id)
        .first()
    )
    if link is None:
        db.add(
            NotebookDocument(
                notebook_id=notebook.id,
                document_id=document.id,
                is_active=is_active,
            )
        )
        print(f"      [+] Linked {document.title} (active={is_active})")


def main():
    db = SessionLocal()

    try:
        user = get_client_user(db)

        documents = seed_documents(db, user)
        db.flush()

        seed_notebooks(db, user, documents)

        db.commit()

        print("\n===================================")
        print("Seed completed successfully.")
        print(f"Notebooks seeded for: {user.email}")
        print("===================================")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()