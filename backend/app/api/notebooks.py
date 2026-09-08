from fastapi import APIRouter, Depends, status

from app.core.dependencies import (
    CurrentUserDep,
    MongoDbDep,
    NotebookServiceDep,
    MindmapServiceDep,
    get_current_user,
)
from app.schemas.notebook_schema import (
    AddDocumentsToNotebookRequest,
    NotebookCreate,
    NotebookDetailOut,
    NotebookOut,
    NotebookUpdate,
    ToggleDocumentActiveRequest,
)
from app.schemas.response_schema import BaseResponse
from app.schemas.mindmap_schema import MindmapCreate, MindmapListItem, MindmapOut

router = APIRouter(
    prefix="/notebooks",
    tags=["Notebooks"],
    dependencies=[Depends(get_current_user)],
)


# ==================================================
# NOTEBOOK CRUD
# ==================================================


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=BaseResponse[NotebookOut],
)
async def create_notebook(
    payload: NotebookCreate,
    notebook_service: NotebookServiceDep,
    current_user: CurrentUserDep,
):
    notebook = notebook_service.create_notebook(
        current_user=current_user,
        data=payload,
    )

    notebook_out = NotebookOut.model_validate(notebook)
    notebook_out.document_count = (
        len(notebook.notebook_documents) if notebook.notebook_documents else 0
    )

    return BaseResponse(
        message="Notebook created successfully.",
        data=notebook_out,
    )


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse[list[NotebookOut]],
)
async def get_notebooks(
    notebook_service: NotebookServiceDep,
    current_user: CurrentUserDep,
):
    notebooks = notebook_service.get_notebooks(current_user=current_user)
    return BaseResponse(data=notebooks)


@router.get(
    "/{notebook_id}",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse[NotebookDetailOut],
)
async def get_notebook_detail(
    notebook_id: int,
    notebook_service: NotebookServiceDep,
    current_user: CurrentUserDep,
):
    detail = notebook_service.get_notebook_detail(
        notebook_id=notebook_id,
        current_user=current_user,
    )
    return BaseResponse(data=detail)


@router.put(
    "/{notebook_id}",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse[NotebookOut],
)
async def update_notebook(
    notebook_id: int,
    payload: NotebookUpdate,
    notebook_service: NotebookServiceDep,
    current_user: CurrentUserDep,
):
    updated_notebook = notebook_service.update_notebook(
        notebook_id=notebook_id,
        current_user=current_user,
        data=payload,
    )

    notebook_out = NotebookOut.model_validate(updated_notebook)
    notebook_out.document_count = (
        len(updated_notebook.notebook_documents)
        if updated_notebook.notebook_documents
        else 0
    )

    return BaseResponse(
        message="Notebook updated successfully.",
        data=notebook_out,
    )


@router.delete(
    "/{notebook_id}",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse,
)
async def delete_notebook(
    notebook_id: int,
    notebook_service: NotebookServiceDep,
    current_user: CurrentUserDep,
    mongo_db: MongoDbDep,
):
    result = await notebook_service.delete_notebook(
        notebook_id=notebook_id,
        current_user=current_user,
        mongo_db=mongo_db,
    )
    return BaseResponse(message=result.get("detail", "Notebook deleted successfully."))


# ==================================================
# DUPLICATE NOTEBOOK
# ==================================================


@router.post(
    "/{notebook_id}/duplicate",
    status_code=status.HTTP_201_CREATED,
    response_model=BaseResponse[NotebookOut],
)
async def duplicate_notebook(
    notebook_id: int,
    notebook_service: NotebookServiceDep,
    current_user: CurrentUserDep,
):
    duplicated_notebook = notebook_service.duplicate_notebook(
        notebook_id=notebook_id,
        current_user=current_user,
    )

    notebook_out = NotebookOut.model_validate(duplicated_notebook)
    notebook_out.document_count = (
        len(duplicated_notebook.notebook_documents)
        if duplicated_notebook.notebook_documents
        else 0
    )

    return BaseResponse(
        message="Notebook duplicated successfully.",
        data=notebook_out,
    )


# ==================================================
# DOCUMENT MANAGEMENT
# ==================================================


@router.post(
    "/{notebook_id}/documents",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse,
)
async def add_documents_to_notebook(
    notebook_id: int,
    payload: AddDocumentsToNotebookRequest,
    notebook_service: NotebookServiceDep,
    current_user: CurrentUserDep,
):
    result = notebook_service.add_documents(
        notebook_id=notebook_id,
        current_user=current_user,
        data=payload,
    )
    return BaseResponse(message=result.get("detail"))


@router.delete(
    "/{notebook_id}/documents/{document_id}",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse,
)
async def remove_document_from_notebook(
    notebook_id: int,
    document_id: int,
    notebook_service: NotebookServiceDep,
    current_user: CurrentUserDep,
):
    result = notebook_service.remove_document(
        notebook_id=notebook_id,
        document_id=document_id,
        current_user=current_user,
    )
    return BaseResponse(message=result.get("detail"))


@router.patch(
    "/{notebook_id}/documents/{document_id}/active",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse,
)
async def toggle_document_active(
    notebook_id: int,
    document_id: int,
    payload: ToggleDocumentActiveRequest,
    notebook_service: NotebookServiceDep,
    current_user: CurrentUserDep,
):
    result = notebook_service.toggle_document_active(
        notebook_id=notebook_id,
        document_id=document_id,
        current_user=current_user,
        data=payload,
    )
    return BaseResponse(message=result.get("detail"))


# ==================================================
# MINDMAPS
# ==================================================

@router.get(
    "/{notebook_id}/mindmaps",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse[list[MindmapListItem]],
)
async def list_mindmaps(
    notebook_id: int,
    mindmap_service: MindmapServiceDep,
    current_user: CurrentUserDep,
):
    items = mindmap_service.list_mindmaps(notebook_id, current_user)
    return BaseResponse(data=[MindmapListItem.model_validate(item) for item in items])


@router.post(
    "/{notebook_id}/mindmaps",
    status_code=status.HTTP_201_CREATED,
    response_model=BaseResponse[MindmapOut],
)
async def create_mindmap(
    notebook_id: int,
    payload: MindmapCreate,
    mindmap_service: MindmapServiceDep,
    current_user: CurrentUserDep,
):
    item = await mindmap_service.create_mindmap(notebook_id, payload, current_user)
    return BaseResponse(message="Mindmap created successfully.", data=MindmapOut.model_validate(item))


@router.get(
    "/{notebook_id}/mindmaps/{mindmap_id}",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse[MindmapOut],
)
async def get_mindmap(
    notebook_id: int,
    mindmap_id: int,
    mindmap_service: MindmapServiceDep,
    current_user: CurrentUserDep,
):
    item = mindmap_service.get_mindmap(notebook_id, mindmap_id, current_user)
    return BaseResponse(data=MindmapOut.model_validate(item))


@router.delete(
    "/{notebook_id}/mindmaps/{mindmap_id}",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse,
)
async def delete_mindmap(
    notebook_id: int,
    mindmap_id: int,
    mindmap_service: MindmapServiceDep,
    current_user: CurrentUserDep,
):
    mindmap_service.delete_mindmap(notebook_id, mindmap_id, current_user)
    return BaseResponse(message="Mindmap deleted successfully.")
