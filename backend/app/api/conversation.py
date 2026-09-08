from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import (
    ConversationServiceDep,
    CurrentUserDep,
    DbSession,
    get_current_user,
)
from app.models.notebook_model import Notebook
from app.schemas.conversation_schema import (
    ConversationDetail,
    ConversationSummary,
    CreateConversationRequest,
    RenameConversationRequest,
)
from app.services.rag.conversation_service import DEFAULT_CONVERSATION_TITLE

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    current_user: CurrentUserDep,
    db: DbSession,
    conversation_service: ConversationServiceDep,
    notebook_id: int | None = Query(default=None),
):
    return conversation_service.list_conversations(
        db, current_user.id, notebook_id=notebook_id
    )


@router.post("", response_model=ConversationSummary, status_code=201)
async def create_conversation(
    payload: CreateConversationRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    conversation_service: ConversationServiceDep,
):
    notebook_exists = (
        db.query(Notebook.id)
        .filter(
            Notebook.id == payload.notebook_id,
            Notebook.user_id == current_user.id,
        )
        .first()
    )
    if not notebook_exists:
        raise HTTPException(status_code=404, detail="Notebook not found")

    return conversation_service.create_conversation(
        db,
        user_id=current_user.id,
        title=DEFAULT_CONVERSATION_TITLE,
        notebook_id=payload.notebook_id,
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: int,
    current_user: CurrentUserDep,
    db: DbSession,
    conversation_service: ConversationServiceDep,
):
    conv = conversation_service.get_conversation(db, current_user.id, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = conversation_service.get_messages(db, conversation_id)
    return ConversationDetail(id=conv.id, title=conv.title, messages=messages)


@router.patch("/{conversation_id}", response_model=ConversationSummary)
async def rename_conversation(
    conversation_id: int,
    payload: RenameConversationRequest,
    current_user: CurrentUserDep,
    db: DbSession,
    conversation_service: ConversationServiceDep,
):
    conv = conversation_service.rename_conversation(
        db, current_user.id, conversation_id, payload.title
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: int,
    current_user: CurrentUserDep,
    db: DbSession,
    conversation_service: ConversationServiceDep,
):
    deleted = conversation_service.delete_conversation(
        db, current_user.id, conversation_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
