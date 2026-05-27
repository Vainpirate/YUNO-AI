from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentBase(BaseModel):
    name: str
    role: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    tools: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    memory_config: dict = Field(default_factory=dict)
    guardrails: dict = Field(default_factory=dict)


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    role: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    tools: list[str] | None = None
    channels: list[str] | None = None
    memory_config: dict | None = None
    guardrails: dict | None = None


class AgentRead(AgentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowBase(BaseModel):
    name: str
    description: str | None = None
    agents: list[str] = Field(default_factory=list)
    graph: dict = Field(default_factory=dict)
    schedule: str | None = None
    template_name: str | None = None


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    description: str | None = None
    agents: list[str] | None = None
    graph: dict | None = None
    schedule: str | None = None
    template_name: str | None = None


class WorkflowRead(WorkflowBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
