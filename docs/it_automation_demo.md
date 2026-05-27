# IT Service Automation — YUNO AI Demo

> **What this shows:** A 5-agent pipeline that takes a raw client brief and
> outputs a structured proposal + task plan + ready-to-send client emails —
> all automatically, in one workflow execution.

---

## The Pipeline

```
Client types a brief
        │
        ▼
┌─────────────────────────────┐
│  Requirement Analysis Agent │  Extracts features, platform, integrations,
│  (IT Requirement Analyst)   │  open questions from raw client text
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│  Scope Estimation Agent     │  Tech stack, effort hours, team size,
│  (Technical Estimator)      │  timeline phases, budget tiers
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│  Proposal Generator Agent   │  Full professional proposal doc with
│  (Business Proposal Writer) │  executive summary, scope, investment
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│  Task Planner Agent         │  Epics → User stories → Sprint plan
│  (Project Manager)          │  → Numbered task checklist → Risk register
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│  Client Communication Agent │  Response email, WhatsApp/Telegram message,
│  (Account Manager)          │  LinkedIn note, 1-page executive summary
└─────────────────────────────┘
        │
        ▼
   Complete Package Delivered
```

---

## Setup (one-time)

```bash
# 1. Start the platform
cd "d:\My Projects\YUNO AI"
docker compose up -d          # OR: start backend + frontend manually

# 2. Seed the pipeline
python scripts/seed_it_automation.py

# 3. Open the UI
# http://localhost:5173  →  Workflow Studio  →  "IT Service Automation Pipeline"
```

---

## Running the Demo

### Option A — UI (recommended for demos)

1. Open **Workflow Studio** → select **IT Service Automation Pipeline**
2. Click **▶ Execute**
3. In the input box, paste the client brief below
4. Click **Run** — watch the **Live Monitor** tab stream each agent's output
5. Switch to **Message History** to read all 5 agent outputs

### Option B — API

```bash
curl -X POST http://localhost:8000/api/workflows/<workflow-id>/execute \
     -H "Content-Type: application/json" \
     -d '{
       "input": "I need an e-commerce app for my clothing brand. It should have
                 product listings, cart, Stripe payments, user accounts, and an
                 admin dashboard. Mobile-first design. Budget is flexible."
     }'
```

---

## Sample Client Briefs (copy & paste)

### Brief 1 — E-commerce Startup
```
I need an e-commerce app for my clothing brand. It should have product
listings, cart, Stripe payments, user accounts, and an admin dashboard.
Mobile-first design. I want to launch in 3 months. Budget is around $15k.
```

### Brief 2 — SaaS Tool
```
We want to build a project management SaaS — something like Trello but for
construction companies. It needs task boards, Gantt charts, file uploads,
team roles, and a client portal. We need iOS and Android apps too. Our team
is 3 people and we have $50k to spend.
```

### Brief 3 — Healthcare Portal
```
I run a chain of 5 clinics. We need a patient portal where patients can
book appointments, view lab results, and chat with doctors. Must be HIPAA
compliant. Integration with our existing lab system (HL7 FHIR). Web only for now.
```

### Brief 4 — Internal Tool
```
Our HR team needs a leave management system. Employees submit leave requests,
managers approve/reject, and it syncs to Google Calendar. Also needs
reporting for HR — monthly leave trends, team availability calendar. 
Simple UI, just needs to work.
```

---

## Expected Output Per Agent

| Agent | What you get |
|---|---|
| Requirement Analysis | Structured breakdown: features, users, integrations, open questions |
| Scope Estimation | Tech stack, effort table, timeline, budget range |
| Proposal Generator | Full markdown proposal ready to export as PDF |
| Task Planner | Sprint plan + numbered task checklist + risk register |
| Client Communication | Email draft + WhatsApp summary + LinkedIn note + 1-pager |

---

## Why This Matters

| Before YUNO AI | After YUNO AI |
|---|---|
| 4–8 hours of manual work per inquiry | < 2 minutes automated |
| Inconsistent proposal quality | Consistent, structured, professional |
| BD team bottleneck | Handles unlimited parallel inquiries |
| Tasks manually entered into Jira/Linear | Task plan generated instantly |
| Client follow-up delayed | Communication package ready immediately |

---

## Extending This Pipeline

- **Add a CRM Integration Agent** — auto-create deal in HubSpot/Pipedrive via webhook
- **Add a Competitor Research Agent** — search web for similar products before estimation
- **Add a Legal Agent** — generate NDA / contract outline based on project type
- **Connect Telegram channel** — client sends brief via Telegram bot, gets summary back in DMs
- **Scheduled follow-ups** — use workflow `schedule` field (cron) to send weekly status digests
