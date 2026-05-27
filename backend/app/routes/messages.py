from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Message

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("/{workflow_id}")
def get_messages(workflow_id: UUID, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Message)
        .where(Message.workflow_id == workflow_id)
        .order_by(Message.created_at.asc())
    )
    return [
        {
            "id": str(row.id),
            "from_agent_id": str(row.from_agent_id) if row.from_agent_id else None,
            "to_agent_id": str(row.to_agent_id) if row.to_agent_id else None,
            "workflow_id": str(row.workflow_id) if row.workflow_id else None,
            "channel": row.channel,
            "content": row.content,
            "metadata": row.metadata_json,
            "created_at": row.created_at,
        }
        for row in rows
    ]
