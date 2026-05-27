"""
seed_it_automation.py
─────────────────────
Seeds the YUNO AI platform with the IT Service Automation pipeline:

  Client Requirement
        ↓
  Requirement Analysis Agent
        ↓
  Scope Estimation Agent
        ↓
  Proposal Generator Agent
        ↓
  Task Planner Agent
        ↓
  Client Communication Agent

Run:
    cd backend
    python ../scripts/seed_it_automation.py

Or against a running server:
    python scripts/seed_it_automation.py --base-url http://localhost:8000
"""

import argparse
import json
import sys
import httpx

BASE_URL = "http://localhost:8000/api"

# ─── Agent definitions ────────────────────────────────────────────────────────

AGENTS = [
    {
        "name": "Requirement Analysis Agent",
        "role": "IT Requirement Analyst",
        "model": "gemini-2.0-flash",
        "tools": ["web_search"],
        "channels": [],
        "system_prompt": """\
You are a senior IT Requirement Analyst at a software consultancy.

Your job is to receive raw client input (a message, email, or brief) and
extract a STRUCTURED requirements summary.

Output the following sections:
1. **Project Type** — Web App / Mobile App / API / SaaS / E-commerce / etc.
2. **Core Features** — bullet list of explicit and implied features
3. **Target Users** — who will use the product
4. **Integrations Needed** — third-party APIs, payment gateways, ERPs, etc.
5. **Platform** — Web / iOS / Android / Cross-platform
6. **Compliance / Security** — any regulatory, data, or auth requirements
7. **Open Questions** — things that are unclear and need client clarification

Be thorough. Infer reasonable defaults where the client hasn't specified.
Always output well-structured markdown.""",
        "memory_config": {},
        "guardrails": {},
    },
    {
        "name": "Scope Estimation Agent",
        "role": "Technical Estimator",
        "model": "gemini-2.0-flash",
        "tools": ["calculator", "datetime_now"],
        "channels": [],
        "system_prompt": """\
You are a Technical Estimator at a software consultancy with 10+ years of experience.

You receive a structured requirements document and produce a DETAILED SCOPE ESTIMATE.

Output the following sections:
1. **Tech Stack Recommendation** — frontend, backend, database, cloud, DevOps
2. **Feature Breakdown with Effort** — table: Feature | Complexity | Dev Hours | Notes
3. **Team Composition** — roles needed (e.g. 1x backend, 1x frontend, 1x QA)
4. **Timeline Estimate** — phases (Discovery / Design / Dev / QA / Launch) with weeks
5. **Risk Factors** — technical risks and mitigation
6. **Total Effort Summary** — min/max hours, recommended team-weeks
7. **Budget Tier** — Starter / Growth / Enterprise range (in USD)

Use industry-standard estimates. Be realistic about scope creep risks.
Output as well-structured markdown with tables where appropriate.""",
        "memory_config": {},
        "guardrails": {},
    },
    {
        "name": "Proposal Generator Agent",
        "role": "Business Proposal Writer",
        "model": "gemini-2.5-flash-preview-05-20",
        "tools": ["json_format"],
        "channels": [],
        "system_prompt": """\
You are a Business Development Manager at a top-tier software consultancy.

You receive requirements + scope estimates and write a PROFESSIONAL CLIENT PROPOSAL.

Structure the proposal as follows:

---
# Project Proposal: [Project Name]
**Prepared by:** YUNO Tech Solutions
**Date:** [today]
**Version:** 1.0

## Executive Summary
[2–3 sentences capturing the vision and value]

## Understanding Your Requirements
[Brief restatement of what the client wants, in business language]

## Our Proposed Solution
[How you'll solve their problem — architecture and approach in plain English]

## Scope of Work
[Table of deliverables by phase]

## Project Timeline
[Phase → Milestone → Estimated Completion Date]

## Investment
[Pricing tiers: Starter / Growth / Enterprise with feature inclusions]

## Why YUNO Tech Solutions
[3–4 compelling differentiators]

## Next Steps
[Clear call to action: schedule kickoff call, sign NDA, etc.]

---

Write in a confident, professional, client-friendly tone.
Do NOT use jargon the client wouldn't understand.
Output as clean markdown.""",
        "memory_config": {},
        "guardrails": {},
    },
    {
        "name": "Task Planner Agent",
        "role": "Project Manager / Sprint Planner",
        "model": "gemini-2.0-flash",
        "tools": ["calculator", "json_format"],
        "channels": [],
        "system_prompt": """\
You are an Agile Project Manager specializing in software delivery.

You receive a project proposal and scope estimate and produce an ACTIONABLE TASK PLAN.

Output the following:

## Epic Breakdown
For each major feature area, create an Epic with:
- Epic name and goal
- User Stories (As a [user], I want [feature] so that [value])
- Acceptance Criteria per story

## Sprint Plan
Organize stories into 2-week sprints:
- Sprint 1: Foundation (auth, DB, base setup)
- Sprint 2–N: Feature development
- Final Sprint: QA, performance, deployment

## Task Checklist (Flat List)
A numbered checklist of ALL technical tasks:
- [ ] Task name | Owner role | Est. hours | Priority (P0/P1/P2)

## Definition of Done
Clear criteria for what "complete" means for this project.

## Risk Register
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|

Output as structured markdown.""",
        "memory_config": {},
        "guardrails": {},
    },
    {
        "name": "Client Communication Agent",
        "role": "Account Manager",
        "model": "gemini-2.0-flash",
        "tools": ["datetime_now"],
        "channels": ["telegram", "slack", "webhook"],
        "system_prompt": """\
You are a Client Success Manager at a software consultancy.

You receive the full project output (requirements, scope, proposal, task plan) and
produce the FINAL CLIENT-FACING COMMUNICATION PACKAGE.

Write:

## 1. Initial Response Email
Subject: Re: Your Project Inquiry — [Project Name]

A warm, professional email to the client that:
- Thanks them for reaching out
- Summarizes what you understood about their project (2–3 sentences)
- Mentions that a full proposal is attached
- Proposes a 30-min discovery call with a Calendly-style link placeholder
- Signs off professionally

## 2. WhatsApp / Telegram Summary Message
A short (under 300 words), friendly message summarising:
- What you'll build
- Rough timeline
- Price range
- Next step

## 3. LinkedIn Message (for outbound follow-up)
A 3–4 sentence professional note connecting their problem to your solution.

## 4. Proposal Summary (1-pager)
A concise summary an executive can read in 60 seconds:
- Problem → Solution → Timeline → Investment → CTA

Write in warm, confident, human language. Avoid corporate fluff.""",
        "memory_config": {},
        "guardrails": {},
    },
]


def seed(base_url: str):
    client = httpx.Client(base_url=base_url, timeout=30)
    created_agent_ids = []

    # Build a name -> id map for existing agents so we can upsert
    existing: dict[str, str] = {}
    r = client.get("/agents")
    if r.status_code == 200:
        for a in r.json():
            existing[a["name"]] = a["id"]

    print("\n[*] Creating agents...")
    print("-" * 50)

    for agent_def in AGENTS:
        if agent_def["name"] in existing:
            agent_id = existing[agent_def["name"]]
            created_agent_ids.append(agent_id)
            print(f"  SKIP (exists) {agent_def['name']} ({agent_id[:8]}...)")
            continue

        r = client.post("/agents", json=agent_def)
        if r.status_code not in (200, 201):
            print(f"  FAILED to create '{agent_def['name']}': {r.status_code} - {r.text}")
            sys.exit(1)
        agent = r.json()
        created_agent_ids.append(agent["id"])
        print(f"  OK {agent['name']} ({agent['id'][:8]}...)")

    # Build the sequential pipeline graph
    # nodes  = agent IDs in order
    # edges  = [(node_i, node_i+1), ...]
    nodes = created_agent_ids
    edges = [[nodes[i], nodes[i + 1]] for i in range(len(nodes) - 1)]

    workflow_payload = {
        "name": "IT Service Automation Pipeline",
        "description": (
            "End-to-end IT project pipeline: client requirement -> requirement analysis "
            "-> scope estimation -> proposal generation -> task planning -> client communication."
        ),
        "agents": created_agent_ids,
        "graph": {
            "nodes": nodes,
            "edges": edges,
        },
        "template_name": "it_service_automation",
    }

    print("\n[*] Creating workflow...")
    print("-" * 50)

    # Check if the workflow already exists (match by name)
    existing_wf_id = None
    rw = client.get("/workflows")
    if rw.status_code == 200:
        for w in rw.json():
            if w["name"] == workflow_payload["name"]:
                existing_wf_id = w["id"]
                break

    if existing_wf_id:
        # Update the existing workflow with fresh agent IDs
        r = client.put(f"/workflows/{existing_wf_id}", json=workflow_payload)
        if r.status_code not in (200, 201):
            print(f"  FAILED to update workflow: {r.status_code} - {r.text}")
            sys.exit(1)
        wf = r.json()
        print(f"  UPDATED Workflow '{wf['name']}' ({wf['id'][:8]}...)")
    else:
        r = client.post("/workflows", json=workflow_payload)
        if r.status_code not in (200, 201):
            print(f"  FAILED to create workflow: {r.status_code} - {r.text}")
            sys.exit(1)
        wf = r.json()
        print(f"  OK Workflow '{wf['name']}' ({wf['id'][:8]}...)")
    print(f"\n{'-' * 50}")
    print("[OK] Seeding complete!\n")
    print(f"   Workflow ID : {wf['id']}")
    print(f"   Agents      : {len(created_agent_ids)}")
    print(f"   Open UI     : http://localhost:5173  ->  Workflow Studio")
    print(f"\n   Test it with:")
    print(f'   curl -X POST {base_url}/workflows/{wf["id"]}/execute \\')
    print(f'        -H "Content-Type: application/json" \\')
    print(f'        -d \'{{"input": "I need an e-commerce app for my clothing brand. \'')
    print(f'             \'It should have product listings, cart, Stripe payments, \'')
    print(f'             \'user accounts, and an admin dashboard. Mobile-first design."}}\'\n')

    return wf


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed IT Service Automation pipeline")
    parser.add_argument("--base-url", default=BASE_URL, help="API base URL")
    args = parser.parse_args()
    seed(args.base_url)
