from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ExecutionLog

router = APIRouter(prefix="/api/execution", tags=["execution"])


@router.get("/{workflow_id}/logs")
def get_execution_logs(workflow_id: UUID, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ExecutionLog)
        .where(ExecutionLog.workflow_id == workflow_id)
        .order_by(ExecutionLog.created_at.asc())
    )
    return [
        {
            "id": str(row.id),
            "workflow_id": str(row.workflow_id) if row.workflow_id else None,
            "agent_id": str(row.agent_id) if row.agent_id else None,
            "step_name": row.step_name,
            "status": row.status,
            "input": row.input,
            "output": row.output,
            "tokens_used": row.tokens_used,
            "cost": row.cost,
            "error": row.error,
            "created_at": row.created_at,
        }
        for row in rows
    ]
