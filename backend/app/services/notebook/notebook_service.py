import logging
from typing import List
import re


from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.document_model import Document
from app.models.notebook_model import Notebook, NotebookDocument
from app.schemas.notebook_schema import (
    AddDocumentsToNotebookRequest,
    NotebookCreate,
    NotebookDetailOut,
    NotebookDocumentOut,
    NotebookOut,
    NotebookUpdate,
    ToggleDocumentActiveRequest,
)
from app.schemas.user_schema import CurrentUser

logger = logging.getLogger(__name__)


class NotebookService:
    def __init__(self, db: Session):
        self.db = db

    # ==================================================
    # PRIVATE HELPERS
    # ==================================================

    def _get_owned_notebook(self, notebook_id: int, user_id: int) -> Notebook:
        """Fetch a notebook and validate ownership."""
        notebook = self.db.query(Notebook).filter(Notebook.id == notebook_id).first()
        if not notebook:
            logger.warning(f"Notebook {notebook_id} not found.")
            raise HTTPException(status_code=404, detail="Notebook not found.")
        if notebook.user_id != user_id:
            logger.error(
                f"Ownership violation: User {user_id} attempted to access Notebook {notebook_id}."
            )
            raise HTTPException(
                status_code=403, detail="Not authorized to access this notebook."
            )
        return notebook

    def _get_owned_document(self, document_id: int, user_id: int) -> Document:
        """Fetch a document and validate ownership."""
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.warning(f"Document {document_id} not found.")
            raise HTTPException(status_code=404, detail="Document not found.")
        if document.user_id != user_id:
            logger.error(
                f"Ownership violation: User {user_id} attempted to access Document {document_id}."
            )
            raise HTTPException(
                status_code=403, detail="Not authorized to access this document."
            )
        return document
    def _generate_duplicate_title(self, user_id: int, original_title: str) -> str:
        """
        Notebook
        Notebook (1)
        Notebook (2)
        ...
        """

        base_title = re.sub(r"\s\(\d+\)$", "", original_title)

        existing_titles = {
            title
            for (title,) in (
                self.db.query(Notebook.title)
                .filter(
                    Notebook.user_id == user_id,
                    Notebook.title.like(f"{base_title}%"),
                )
                .all()
            )
        }

        if base_title not in existing_titles:
            return base_title

        index = 1
        while True:
            candidate = f"{base_title} ({index})"
            if candidate not in existing_titles:
                return candidate
            index += 1

    def _calculate_notebook_statistics(self, notebook: Notebook) -> dict:
        """Calculate and return standard statistics for a notebook."""
        active_document_count = sum(1 for nd in notebook.notebook_documents if nd.is_active)
        quiz_count = len(notebook.quizzes)
        message_count = sum(len(conv.messages) for conv in notebook.conversations)
        total_size = sum(nd.document.file_size for nd in notebook.notebook_documents if nd.document)

        return {
            "active_document_count": active_document_count,
            "quiz_count": quiz_count,
            "message_count": message_count,
            "total_size": total_size,
        }

    # ==================================================
    # NOTEBOOK CRUD
    # ==================================================

    def create_notebook(self, current_user: CurrentUser, data: NotebookCreate) -> Notebook:
        title = data.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="Notebook title cannot be empty.")

        try:
            notebook = Notebook(
                user_id=current_user.id,
                title=title,
                description=data.description,
                color=data.color,
            )

            self.db.add(notebook)
            self.db.commit()
            self.db.refresh(notebook)

            logger.info(
                f"Notebook created successfully: ID {notebook.id} by User {current_user.id}."
            )
            return notebook
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error during notebook creation: {str(e)}")
            raise HTTPException(
                status_code=500, detail="An error occurred while creating the notebook."
            )

    def get_notebooks(self, current_user: CurrentUser) -> List[NotebookOut]:
        notebooks = (
            self.db.query(Notebook)
            .filter(Notebook.user_id == current_user.id)
            .order_by(Notebook.created_at.desc())
            .all()
        )

        result = []
        for nb in notebooks:
            doc_count = len(nb.notebook_documents)
            nb_out = NotebookOut.model_validate(nb)
            nb_out.document_count = doc_count
            result.append(nb_out)

        return result

    def get_notebook_detail(
        self, notebook_id: int, current_user: CurrentUser
    ) -> NotebookDetailOut:
        notebook = self._get_owned_notebook(notebook_id, current_user.id)

        # Calculate statistics using helper
        stats = self._calculate_notebook_statistics(notebook)

        documents_out = [
            NotebookDocumentOut.model_validate(nd) for nd in notebook.notebook_documents
        ]

        return NotebookDetailOut(
            id=notebook.id,
            title=notebook.title,
            description=notebook.description,
            color=notebook.color,
            documents=documents_out,
            active_document_count=stats["active_document_count"],
            quiz_count=stats["quiz_count"],
            message_count=stats["message_count"],
            total_size=stats["total_size"],
            created_at=notebook.created_at,
            updated_at=notebook.updated_at,
        )

    def update_notebook(
        self, notebook_id: int, current_user: CurrentUser, data: NotebookUpdate
    ) -> Notebook:
        notebook = self._get_owned_notebook(notebook_id, current_user.id)

        if data.title is not None:
            title = data.title.strip()
            if not title:
                raise HTTPException(status_code=400, detail="Notebook title cannot be empty.")
            notebook.title = title

        if data.description is not None:
            notebook.description = data.description

        if data.color is not None:
            notebook.color = data.color

        try:
            self.db.commit()
            self.db.refresh(notebook)
            logger.info(f"Notebook {notebook.id} updated successfully by User {current_user.id}.")
            return notebook
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error during notebook update: {str(e)}")
            raise HTTPException(
                status_code=500, detail="An error occurred while updating the notebook."
            )

    def delete_notebook(self, notebook_id: int, current_user: CurrentUser) -> dict:
        notebook = self._get_owned_notebook(notebook_id, current_user.id)

        try:
            self.db.delete(notebook)
            self.db.commit()
            logger.info(f"Notebook {notebook_id} deleted successfully by User {current_user.id}.")
            return {"detail": "Notebook deleted successfully."}
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error during notebook deletion: {str(e)}")
            raise HTTPException(
                status_code=500, detail="An error occurred while deleting the notebook."
            )

    def duplicate_notebook(self, notebook_id: int, current_user: CurrentUser) -> Notebook:
        original_notebook = self._get_owned_notebook(notebook_id, current_user.id)
        new_title = self._generate_duplicate_title(current_user.id, original_notebook.title)

        try:
            new_notebook = Notebook(
                user_id=current_user.id,
                title=new_title,
                description=original_notebook.description,
                color=original_notebook.color,
            )
            self.db.add(new_notebook)
            self.db.flush()  # To obtain the new_notebook.id for mapping

            new_mappings = []
            for nd in original_notebook.notebook_documents:
                new_mappings.append(
                    NotebookDocument(
                        notebook_id=new_notebook.id,
                        document_id=nd.document_id,
                        is_active=nd.is_active,
                    )
                )
            
            if new_mappings:
                self.db.add_all(new_mappings)

            self.db.commit()
            self.db.refresh(new_notebook)

            logger.info(
                f"Notebook duplicated successfully: Original ID {notebook_id} -> New ID {new_notebook.id} by User {current_user.id}."
            )
            return new_notebook
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error during notebook duplication (ID: {notebook_id}): {str(e)}")
            raise HTTPException(
                status_code=500, detail="An error occurred while duplicating the notebook."
            )

    # ==================================================
    # DOCUMENT MANAGEMENT
    # ==================================================

    def add_documents(
        self,
        notebook_id: int,
        current_user: CurrentUser,
        data: AddDocumentsToNotebookRequest,
    ) -> dict:
        notebook = self._get_owned_notebook(notebook_id, current_user.id)
        
        # Deduplicate incoming ids first to avoid unnecessary queries
        unique_doc_ids = list(set(data.document_ids))
        
        # Avoid duplicated inserts for already existing mappings
        existing_doc_ids = {nd.document_id for nd in notebook.notebook_documents}
        new_mappings = []

        for doc_id in unique_doc_ids:
            if doc_id in existing_doc_ids:
                continue
            
            # Verify document exists and ownership
            self._get_owned_document(doc_id, current_user.id)
            
            new_mappings.append(
                NotebookDocument(notebook_id=notebook.id, document_id=doc_id)
            )

        if new_mappings:
            try:
                self.db.add_all(new_mappings)
                self.db.commit()
                logger.info(
                    f"Added {len(new_mappings)} documents to Notebook {notebook_id} by User {current_user.id}."
                )
            except SQLAlchemyError as e:
                self.db.rollback()
                logger.error(f"Database error while adding documents to notebook: {str(e)}")
                raise HTTPException(
                    status_code=500, detail="An error occurred while adding documents."
                )

        return {"detail": f"{len(new_mappings)} new documents added successfully."}

    def remove_document(self, notebook_id: int, document_id: int, current_user: CurrentUser) -> dict:
        notebook = self._get_owned_notebook(notebook_id, current_user.id)

        mapping = (
            self.db.query(NotebookDocument)
            .filter_by(notebook_id=notebook.id, document_id=document_id)
            .first()
        )

        if not mapping:
            raise HTTPException(status_code=404, detail="Document not found in this notebook.")

        try:
            self.db.delete(mapping)
            self.db.commit()
            logger.info(
                f"Removed Document {document_id} from Notebook {notebook_id} by User {current_user.id}."
            )
            return {"detail": "Document removed from notebook successfully."}
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error while removing document from notebook: {str(e)}")
            raise HTTPException(
                status_code=500, detail="An error occurred while removing the document."
            )

    def toggle_document_active(
        self,
        notebook_id: int,
        document_id: int,
        current_user: CurrentUser,
        data: ToggleDocumentActiveRequest,
    ) -> dict:
        notebook = self._get_owned_notebook(notebook_id, current_user.id)

        mapping = (
            self.db.query(NotebookDocument)
            .filter_by(notebook_id=notebook.id, document_id=document_id)
            .first()
        )

        if not mapping:
            raise HTTPException(status_code=404, detail="Document not found in this notebook.")

        try:
            mapping.is_active = data.is_active
            self.db.commit()
            
            status = "activated" if data.is_active else "deactivated"
            logger.info(
                f"Document {document_id} {status} in Notebook {notebook_id} by User {current_user.id}."
            )
            return {"detail": f"Document successfully {status}."}
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error while toggling document status: {str(e)}")
            raise HTTPException(
                status_code=500, detail="An error occurred while updating document status."
            )