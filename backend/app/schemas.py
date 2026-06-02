from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AgentBase(BaseModel):
    name: str
    role: str | None = None
    system_prompt: str | None = None
    model: str | None = "llama-3.3-70b-versatile"
    tools: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    memory_config: dict = Field(default_factory=dict)
    guardrails: dict = Field(default_factory=dict)
    skills: list[dict] = Field(default_factory=list)
    interaction_rules: dict = Field(default_factory=dict)

    @field_validator("skills", mode="before")
    @classmethod
    def _coerce_skills(cls, v: Any) -> list:
        return v if isinstance(v, list) else []

    @field_validator("interaction_rules", mode="before")
    @classmethod
    def _coerce_interaction_rules(cls, v: Any) -> dict:
        return v if isinstance(v, dict) else {}

    @field_validator("memory_config", "guardrails", mode="before")
    @classmethod
    def _coerce_dict(cls, v: Any) -> dict:
        return v if isinstance(v, dict) else {}

    @field_validator("tools", "channels", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> list:
        return v if isinstance(v, list) else []


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    role: str | None = None
    system_prompt: str | None = None
    model: str | None = "llama-3.3-70b-versatile"
    tools: list[str] | None = None
    channels: list[str] | None = None
    memory_config: dict | None = None
    guardrails: dict | None = None
    skills: list[dict] | None = None
    interaction_rules: dict | None = None


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
    max_iterations: int = Field(default=10, ge=1, le=100)
    template_name: str | None = None

    @field_validator("max_iterations", mode="before")
    @classmethod
    def _coerce_max_iterations(cls, v: Any) -> int:
        return v if isinstance(v, int) and v >= 1 else 10

    @field_validator("agents", mode="before")
    @classmethod
    def _coerce_agents(cls, v: Any) -> list:
        return v if isinstance(v, list) else []

    @field_validator("graph", mode="before")
    @classmethod
    def _coerce_graph(cls, v: Any) -> dict:
        return v if isinstance(v, dict) else {}


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    description: str | None = None
    agents: list[str] | None = None
    graph: dict | None = None
    schedule: str | None = None
    max_iterations: int | None = Field(default=None, ge=1, le=100)
    template_name: str | None = None


class WorkflowRead(WorkflowBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
