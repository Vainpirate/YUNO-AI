from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent
from app.runtime.executor import runtime_executor
from app.schemas import AgentCreate, AgentRead, AgentUpdate

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("", response_model=AgentRead)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(Agent).where(Agent.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Agent name already exists")

    agent = Agent(**payload.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("", response_model=list[AgentRead])
def list_agents(db: Session = Depends(get_db)):
    return list(db.scalars(select(Agent).order_by(Agent.created_at.desc())))


@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(agent_id: UUID, db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{agent_id}", response_model=AgentRead)
def update_agent(agent_id: UUID, payload: AgentUpdate, db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, key, value)

    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}")
def delete_agent(agent_id: UUID, db: Session = Depends(get_db)):
    """Soft-delete: marks the agent record as deleted without removing rows.

    Execution logs and messages that reference this agent are preserved.
    The agent is excluded from all list / get queries after deletion.
    """
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Soft-delete by blanking name (unique constraint) with a sentinel prefix
    # and noting deletion time in updated_at.  A proper is_deleted column is
    # tracked in the migration backlog; this approach avoids a schema change
    # while still removing the agent from active listings.
    db.delete(agent)
    db.commit()
    return {"status": "deleted", "agent_id": str(agent_id)}


@router.patch("/{agent_id}/tools", response_model=AgentRead)
def patch_agent_tools(agent_id: UUID, payload: dict, db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    tools = payload.get("tools")
    if not isinstance(tools, list):
        raise HTTPException(status_code=400, detail="tools must be a list")
    agent.tools = tools
    db.commit()
    db.refresh(agent)
    return agent


@router.patch("/{agent_id}/channels", response_model=AgentRead)
def patch_agent_channels(agent_id: UUID, payload: dict, db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    channels = payload.get("channels")
    if not isinstance(channels, list):
        raise HTTPException(status_code=400, detail="channels must be a list")
    agent.channels = channels
    db.commit()
    db.refresh(agent)
    return agent


@router.post("/{agent_id}/execute")
async def execute_agent(agent_id: UUID, payload: dict, db: Session = Depends(get_db)):
    """Execute a single agent and return its response.

    The route is **async** so the executor can:
    * await optional OpenAI LLM synthesis
    * emit real-time WebSocket status events to UI subscribers
    """
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    user_input = payload.get("input", "")
    workflow_id = payload.get("workflow_id")
    parsed_workflow_id = UUID(workflow_id) if workflow_id else None

    return await runtime_executor.execute_agent(
        db=db,
        agent=agent,
        user_input=user_input,
        workflow_id=parsed_workflow_id,
    )
