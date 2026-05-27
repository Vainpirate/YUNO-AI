# Wireframes - Phase 1

This folder contains low-fidelity wireframe specs to unblock Phase 3.

## Screens
1. Agent Manager
- Left: agent table (name, role, tools, status)
- Right: configuration panel (create/edit)
- Primary actions: New Agent, Save, Archive

2. Workflow Builder
- Left sidebar: draggable agents
- Center: DAG canvas with node/edge editing
- Right drawer: edge conditions + node settings
- Footer: Validate, Save, Execute

3. Message History
- Timeline view grouped by execution
- Filters: workflow, date range, channel, agent
- Detail panel for metadata (tokens, latency, cost)

4. Execution Monitor
- Live log stream (WebSocket)
- Agent status badges
- Token/cost counters + execution progress
- Error surface with retry action

## Interaction Notes
- All screens must support loading, empty, error, and success states.
- Mobile view can simplify canvas controls but must preserve read visibility.
- Execution monitor should auto-scroll with pause/resume toggle.
