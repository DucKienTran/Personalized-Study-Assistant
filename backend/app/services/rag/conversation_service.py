# app/services/conversation_service.py

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.conversation_model import Conversation, Message

logger = logging.getLogger(__name__)


class ConversationService:
    def create_conversation(
        self,
        db: Session,
        user_id: int,
        title: str,
        notebook_id: int,
    ) -> Conversation:
        conv = Conversation(
            user_id=user_id,
            notebook_id=notebook_id,
            title=title[:255],
        )

        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv

    def get_conversation(
        self,
        db: Session,
        user_id: int,
        conversation_id: int,
    ) -> Conversation | None:
        return (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .first()
        )

    def list_conversations(
        self,
        db: Session,
        user_id: int,
        notebook_id: int | None = None,
    ) -> list[Conversation]:
        query = db.query(Conversation).filter(
            Conversation.user_id == user_id,
        )

        if notebook_id is not None:
            query = query.filter(
                Conversation.notebook_id == notebook_id,
            )

        return query.order_by(
            Conversation.updated_at.desc(),
            Conversation.id.desc(),
        ).all()

    def get_messages(
        self,
        db: Session,
        conversation_id: int,
    ) -> list[Message]:
        return (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
            )
            .order_by(
                Message.created_at.asc(),
                Message.id.asc(),
            )
            .all()
        )

    def add_message(
        self,
        db: Session,
        conversation_id: int,
        sender: str,
        content: str,
        sources_json: str | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            sender=sender,
            content=content,
            sources_json=sources_json,
        )

        db.add(msg)

        conv = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
            )
            .first()
        )

        if conv:
            conv.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(msg)

        return msg

    def rename_conversation(
        self,
        db: Session,
        user_id: int,
        conversation_id: int,
        title: str,
    ) -> Conversation | None:
        conv = self.get_conversation(
            db,
            user_id,
            conversation_id,
        )

        if not conv:
            return None

        conv.title = title[:255]

        db.commit()
        db.refresh(conv)

        return conv

    def delete_conversation(
        self,
        db: Session,
        user_id: int,
        conversation_id: int,
    ) -> bool:
        conv = self.get_conversation(
            db,
            user_id,
            conversation_id,
        )

        if not conv:
            return False

        db.delete(conv)
        db.commit()

        return True
