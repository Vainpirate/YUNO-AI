from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Workflow
from app.runtime.executor import runtime_executor
from app.schemas import WorkflowCreate, WorkflowRead, WorkflowUpdate

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

# In-process execution state cache (workflow_id → status string).
# Replaced by execution_logs for persistent history; this is a fast
# in-memory read for the /status endpoint.
_execution_state: dict[str, str] = {}


@router.get("/templates")
def list_workflow_templates():
    return [
        {
            "name": "research_summarize",
            "description": "Two-agent chain: Researcher gathers information, Summarizer condenses it.",
            "graph": {
                "nodes": ["researcher", "summarizer"],
                "edges": [["researcher", "summarizer"]],
            },
        },
        {
            "name": "qa_router",
            "description": "Route an incoming prompt to the most relevant specialist agent.",
            "graph": {
                "nodes": ["router", "specialist"],
                "edges": [["router", "specialist"]],
            },
        },
        {
            "name": "research_summarize_validate",
            "description": "Three-agent pipeline: research → summarize → validate output quality.",
            "graph": {
                "nodes": ["researcher", "summarizer", "validator"],
                "edges": [["researcher", "summarizer"], ["summarizer", "validator"]],
            },
        },
    ]


@router.post("", response_model=WorkflowRead)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    workflow = Workflow(**payload.model_dump())
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("", response_model=list[WorkflowRead])
def list_workflows(db: Session = Depends(get_db)):
    return list(db.scalars(select(Workflow).order_by(Workflow.created_at.desc())))


@router.get("/{workflow_id}", response_model=WorkflowRead)
def get_workflow(workflow_id: UUID, db: Session = Depends(get_db)):
    workflow = db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.put("/{workflow_id}", response_model=WorkflowRead)
def update_workflow(workflow_id: UUID, payload: WorkflowUpdate, db: Session = Depends(get_db)):
    workflow = db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(workflow, key, value)

    db.commit()
    db.refresh(workflow)
    return workflow


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: UUID,
    payload: dict = None,
    db: Session = Depends(get_db),
):
    """Trigger workflow execution.

    Accepts an optional JSON body ``{"input": "your prompt here"}`` that
    seeds the first agent's context.  Defaults to ``"Workflow started"``
    when omitted.

    The route is **async** so the executor can:
    * run the LangGraph StateGraph (await ainvoke)
    * await optional per-step OpenAI LLM calls
    * stream real-time WebSocket log events to UI subscribers
    """
    from fastapi import Body  # local import to avoid circular at module level
    workflow = db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    initial_input = (payload or {}).get("input", "Workflow started")

    _execution_state[str(workflow_id)] = "running"
    result = await runtime_executor.execute_workflow(db, workflow, initial_input=initial_input)
    _execution_state[str(workflow_id)] = result.get("status", "unknown")
    return result


@router.get("/{workflow_id}/status")
def workflow_status(workflow_id: UUID):
    return {
        "workflow_id": str(workflow_id),
        "status": _execution_state.get(str(workflow_id), "unknown"),
    }
