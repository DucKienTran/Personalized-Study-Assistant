from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from app.core.dependencies import (
    CurrentUserDep,
    DocumentProcessingServiceDep,
    DocumentServiceDep,
    get_current_user,
)
from app.schemas.document_schema import (
    DocumentContentOut,
    DocumentOut,
    FileUrlOut,
    PastedTextDocumentCreate,
)
from app.schemas.response_schema import BaseResponse

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=BaseResponse[DocumentOut],
)
async def upload_and_process_document(
    background_tasks: BackgroundTasks,
    doc_service: DocumentServiceDep,
    processing_service: DocumentProcessingServiceDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(...),
):
    file_bytes = await file.read()

    new_doc = await doc_service.upload_and_init_document(
        file_bytes=file_bytes, filename=file.filename, user_id=current_user.id
    )

    background_tasks.add_task(
        processing_service.execute_processing_pipeline,
        document_id=new_doc.id,
        mongo_id=new_doc.mongo_id,
        object_name=new_doc.file_path,
    )

    return BaseResponse(
        message="Tài liệu đã được tải lên thành công. Tiến trình phân tích cấu trúc đang được xử lý tự động.",
        data=new_doc,
    )


@router.post(
    "/paste-text",
    status_code=status.HTTP_201_CREATED,
    response_model=BaseResponse[DocumentOut],
)
async def create_document_from_text(
    payload: PastedTextDocumentCreate,
    background_tasks: BackgroundTasks,
    doc_service: DocumentServiceDep,
    processing_service: DocumentProcessingServiceDep,
    current_user: CurrentUserDep,
):
    new_doc = await doc_service.upload_and_init_document(
        file_bytes=payload.content.encode("utf-8"),
        filename="pasted-text.txt",
        user_id=current_user.id,
        title=payload.title,
    )

    background_tasks.add_task(
        processing_service.execute_processing_pipeline,
        document_id=new_doc.id,
        mongo_id=new_doc.mongo_id,
        object_name=new_doc.file_path,
    )

    return BaseResponse(
        message="Văn bản đã được tạo và đang được xử lý.",
        data=new_doc,
    )


@router.get(
    "/", status_code=status.HTTP_200_OK, response_model=BaseResponse[list[DocumentOut]]
)
async def get_documents(
    doc_service: DocumentServiceDep,
    current_user: CurrentUserDep,
    document_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100),
):
    if document_id:
        doc = doc_service.get_document(
            user_id=current_user.id,
            document_id=document_id,
        )

        if doc is None:
            raise HTTPException(404, "Không tìm thấy tài liệu")

        return BaseResponse(data=[doc])

    docs = doc_service.list_documents(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status_filter=status_filter,
        search=search,
    )

    return BaseResponse(data=docs)


@router.get(
    "/{document_id}/content",
    response_model=BaseResponse[DocumentContentOut],
)
async def get_document_raw_content(
    document_id: int,
    current_user: CurrentUserDep,
    document_service: DocumentServiceDep,
):
    content = await document_service.get_document_content(
        document_id=document_id,
        user_id=current_user.id,
    )

    if content is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tài liệu",
        )

    return BaseResponse(data=DocumentContentOut.model_validate(content))


@router.delete(
    "/{document_id}", status_code=status.HTTP_200_OK, response_model=BaseResponse
)
async def delete_document(
    document_id: int,
    doc_service: DocumentServiceDep,
    current_user: CurrentUserDep,
):
    success = await doc_service.delete_document(document_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    return BaseResponse(message="Đã xóa tài liệu")


@router.get(
    "/{document_id}/file-url",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse[FileUrlOut],
)
async def get_document_file_url(
    document_id: int,
    doc_service: DocumentServiceDep,
    current_user: CurrentUserDep,
):
    url = await doc_service.get_document_file_url(
        document_id=document_id,
        user_id=current_user.id,
    )

    if url is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

    return BaseResponse(data=FileUrlOut(url=url))


@router.get(
    "/{document_id}/download-url",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse[FileUrlOut],
)
async def get_document_download_url(
    document_id: int,
    doc_service: DocumentServiceDep,
    current_user: CurrentUserDep,
):
    url = await doc_service.get_document_download_url(
        document_id=document_id,
        user_id=current_user.id,
    )

    if url is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")

    return BaseResponse(data=FileUrlOut(url=url))
