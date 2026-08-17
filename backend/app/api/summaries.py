from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import (
    CurrentUserDep,
    SummaryRecordServiceDep,
    SummaryServiceDep,
    get_current_user,
)
from app.schemas.response_schema import BaseResponse
from app.schemas.summary_schema import (
    GenerateNotebookSummaryRequest,
    NotebookSummaryDetail,
    NotebookSummaryOut,
    OverwriteNotebookSummaryRequest,
    SaveNotebookSummaryRequest,
)

router = APIRouter(
    prefix="/notebooks",
    tags=["Notebooks"],
    dependencies=[Depends(get_current_user)],
)


# ==================================================
# NOTEBOOK SUMMARY
# ==================================================
@router.post(
    "/{notebook_id}/summary",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse,
)
async def generate_notebook_summary(
    notebook_id: int,
    payload: GenerateNotebookSummaryRequest,
    summary_service: SummaryServiceDep,
    current_user: CurrentUserDep,
):
    try:
        summary_text = await summary_service.generate_notebook_summary(
            user_id=current_user.id,
            notebook_id=notebook_id,
            level=payload.level,
            format_type=payload.format,
            instruction=payload.instruction or "",
        )

        return BaseResponse(
            message="Notebook summary generated successfully.",
            data={"summary_text": summary_text},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{notebook_id}/summaries",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse,
)
async def save_notebook_summary(
    notebook_id: int,
    payload: SaveNotebookSummaryRequest,
    summary_record_service: SummaryRecordServiceDep,
    current_user: CurrentUserDep,
):
    config = {
        "level": payload.level,
        "format": payload.format,
        "instruction": payload.instruction,
    }

    result = await summary_record_service.save_summary(
        user_id=current_user.id,
        notebook_id=notebook_id,
        title=payload.title,
        summary_text=payload.summary_text,
        config=config,
    )

    return BaseResponse(
        message=result["message"],
        data=result,
    )


@router.put(
    "/{notebook_id}/summaries/{summary_id}",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse,
)
async def update_notebook_summary(
    notebook_id: int,
    summary_id: int,
    payload: OverwriteNotebookSummaryRequest,
    summary_record_service: SummaryRecordServiceDep,
    current_user: CurrentUserDep,
):
    result = await summary_record_service.update_summary(
        user_id=current_user.id,
        notebook_id=notebook_id,
        summary_id=summary_id,
        summary_text=payload.summary_text,
        title=payload.title,
    )

    return BaseResponse(
        message=result["message"],
        data=result,
    )


@router.get(
    "/{notebook_id}/summaries",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse[list[NotebookSummaryOut]],
)
async def get_notebook_summary_history(
    notebook_id: int,
    summary_record_service: SummaryRecordServiceDep,
    current_user: CurrentUserDep,
):
    history_list = summary_record_service.get_summary_history_list(
        user_id=current_user.id,
        notebook_id=notebook_id,
    )

    return BaseResponse(
        message="Fetched summary history successfully.",
        data=history_list,
    )


@router.get(
    "/{notebook_id}/summaries/{summary_id}",
    status_code=status.HTTP_200_OK,
    response_model=BaseResponse[NotebookSummaryDetail],
)
async def get_notebook_summary_detail(
    notebook_id: int,
    summary_id: int,
    summary_record_service: SummaryRecordServiceDep,
    current_user: CurrentUserDep,
):
    detail = await summary_record_service.get_summary_detail(
        user_id=current_user.id,
        notebook_id=notebook_id,
        summary_id=summary_id,
    )

    return BaseResponse(
        message="Fetched summary detail successfully.",
        data=detail,
    )
