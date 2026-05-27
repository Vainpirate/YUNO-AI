BEGIN;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE execution_status AS ENUM ('pending', 'running', 'success', 'error', 'cancelled');
CREATE TYPE message_direction AS ENUM ('inbound', 'outbound');

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL UNIQUE,
    role VARCHAR(120) NOT NULL,
    system_prompt TEXT NOT NULL,
    model VARCHAR(80) NOT NULL,
    tools JSONB NOT NULL DEFAULT '[]'::jsonb,
    channels JSONB NOT NULL DEFAULT '[]'::jsonb,
    memory_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    guardrails JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(160) NOT NULL,
    description TEXT,
    dag JSONB NOT NULL,
    template_name VARCHAR(120),
    version INTEGER NOT NULL DEFAULT 1,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (name, version)
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id),
    execution_id UUID,
    from_agent_id UUID REFERENCES agents(id),
    to_agent_id UUID REFERENCES agents(id),
    channel VARCHAR(32) NOT NULL DEFAULT 'internal',
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE message_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel VARCHAR(32) NOT NULL,
    external_user_id VARCHAR(255) NOT NULL,
    external_chat_id VARCHAR(255),
    agent_id UUID REFERENCES agents(id),
    direction message_direction NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL,
    workflow_id UUID NOT NULL REFERENCES workflows(id),
    agent_id UUID REFERENCES agents(id),
    step_name VARCHAR(160) NOT NULL,
    status execution_status NOT NULL,
    input_payload JSONB,
    output_payload JSONB,
    tokens_used INTEGER NOT NULL DEFAULT 0,
    cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 0,
    latency_ms INTEGER,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agents_active ON agents(is_deleted, status);
CREATE INDEX idx_workflows_active ON workflows(is_deleted, updated_at DESC);
CREATE INDEX idx_messages_workflow_created ON messages(workflow_id, created_at);
CREATE INDEX idx_message_history_user_channel ON message_history(channel, external_user_id, created_at);
CREATE INDEX idx_execution_logs_execution_created ON execution_logs(execution_id, created_at);
CREATE INDEX idx_execution_logs_workflow_created ON execution_logs(workflow_id, created_at);

COMMIT;
