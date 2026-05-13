# Part 3: Building the Digital Banking Chatbot Workflow

## Overview

In this part you build a **four-agent sequential pipeline** that powers an AI-assisted digital banking support service. Unlike the conversational workflow in Part 2, this is a **pipeline** — each agent runs in sequence, passing its output to the next.

The defining capability is **cross-session intelligence**: when the same customer contacts support days apart, the pipeline recognises them as a continuing case. Patterns that span sessions are surfaced automatically, enabling earlier escalation and more coherent support.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                  BANKING CHATBOT — FOUR-AGENT SEQUENTIAL PIPELINE                │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   User message {input}                                                           │
│          │                                                                       │
│          ▼                                                                       │
│  ┌──────────────────┐                                                            │
│  │   AGENT 1        │  ← LightMem: retrieve_memory                              │
│  │   Memory Scout   │    Classify intent · extract identifiers                  │
│  └────────┬─────────┘    Summarise prior context from memory                    │
│           │                                                                      │
│           ▼                                                                      │
│  ┌──────────────────┐                                                            │
│  │   AGENT 2        │  ← iceberg-mcp-server (live Impala queries)               │
│  │   Data Analyst   │    Accounts · transactions · cards · loans · cases        │
│  └────────┬─────────┘                                                            │
│           │                                                                      │
│           ▼                                                                      │
│  ┌──────────────────┐                                                            │
│  │   AGENT 3        │    Pure LLM reasoning over Agent 1 + Agent 2 outputs      │
│  │   Risk Analyst   │    Detect cross-session patterns · assign risk tier       │
│  └────────┬─────────┘    Determine escalation path · define response strategy   │
│           │                                                                      │
│           ▼                                                                      │
│  ┌──────────────────┐                                                            │
│  │   AGENT 4        │  ← LightMem: get_timestamp + add_memory                  │
│  │   Support Advisor│    Compose customer response · store memory note          │
│  └──────────────────┘                                                            │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Why Cross-Session Memory Matters

| Without Memory | With Memory |
|----------------|-------------|
| Session 2 is handled as a standalone scam report | Session 2 triggers a CRITICAL coordinated attack escalation |
| Agent sees no prior context | Agent connects two events 7 days apart — card compromise followed by impersonation call |
| New case logged in isolation | Fraud team receives a linked note identifying a two-stage attack pattern |

> **Experiment:** Use your **own ChromaDB URL and a unique `LIGHTMEM_COLLECTION_NAME`** (empty) to see the workflow with no memory, then switch to the shared ChromaDB (with existing data) to see cross-session retrieval in action.

---

## Prerequisites

- Parts 1 completed: LightMem MCP (`lightmem-chroma`) and Iceberg MCP (`iceberg-mcp-server`) are registered in Agent Studio
- OpenAI API key (provided by instructor)

### MCP Connection Details

#### LightMem MCP — lightmem-chroma

| Parameter | Value |
|-----------|-------|
| **OPENAI_API_KEY** | Provided by instructor |
| **CHROMA_HOST** | Use your own ChromaDB URL from Part 1 **or** the shared URL: `https://chroma-db-1-dwaf-ayqo-3gwk-oaei.ml-e0565700-5cc.datalake.bdqdgc.c0.cloudera.site/` |
| **LIGHTMEM_COLLECTION_NAME** | Choose your own name (e.g. `banking_test`) to start with empty memory, or use `banking_chatbot_memory` to access shared pre-loaded memories |

> **Tip:** Starting with your own empty collection lets you observe how the pipeline behaves with **no prior memory**. After testing, switch `CHROMA_HOST` to the shared URL with an existing collection to experience **cross-session retrieval**.

#### Iceberg MCP — iceberg-mcp-server

| Parameter | Value |
|-----------|-------|
| **IMPALA_HOST** | `hue-impala-gateway.datalake.bdqdgc.c0.cloudera.site` |
| **IMPALA_PORT** | `443` |
| **IMPALA_USER** | `qishuai` |
| **IMPALA_PASSWORD** | Provided by instructor |
| **IMPALA_DATABASE** | `banking_chatbot_db` |

---

## Step 1: Create the Workflow

In Agent Studio, click **Agentic Workflows** > **Create Workflow**. Select **New Workflow**, then enter:

- **Workflow Name**: `Digital Banking Chatbot`

Click **Create Workflow**.

---

## Step 2: Configure Workflow Settings

In the **Add Agents** editor, configure the two toggles:

| Toggle | Setting | Why |
|--------|---------|-----|
| **Is Conversational** | **OFF** | Each customer message is a self-contained pipeline run |
| **Manager Agent** | **OFF** | Sequential pipeline — no routing manager needed |

Leave **Switch to Legacy** off.

---

## Step 3: Add All Four Agents

Click **+ Add Your First Agent** (or **Create or Edit Agents**) to open the agent panel. Create all four agents one by one using the definitions below.

> After filling in each agent's details, click **Create Agent**, then use the agent panel to create the next one before saving. Tools and MCP servers are attached in the same panel — scroll down to **Add Tools** and **Add MCP Servers** after entering each agent's details.

---

### Agent 1 — Memory Scout

| Field | Value |
|-------|-------|
| **Name** | `Memory Scout` |
| **Role** | `Prior Context Retrieval & Intent Classification Specialist` |
| **LLM Model** | `gpt-4o (Default)` |

**Backstory:**
```
You are the first point of contact in the support pipeline. Your job is to look back before anyone looks forward. You retrieve everything the bank knows about this customer from prior interactions, classify what they need now, and hand a fully contextualised brief to the agents that follow. You never compose responses — your only output is structured context.
```

**Goal:**
```
1. Retrieve prior customer memory via MCP (retrieve_memory) before anything else.
2. Classify the message intent.
3. Extract identifiers from the message or infer them from memory.
4. Produce a structured context brief for downstream agents.
```

**MCP to add:** `lightmem-chroma` — select only the **`retrieve_memory`** function.

---

### Agent 2 — Data Analyst

| Field | Value |
|-------|-------|
| **Name** | `Data Analyst` |
| **Role** | `Live Banking Database Query Specialist` |
| **LLM Model** | `gpt-4o (Default)` |

**Backstory:**
```
You translate the Memory Scout's structured brief into precise database lookups. You know the schema and write efficient SQL. You do not analyse or interpret — you retrieve the freshest live data and hand it on.
```

**Goal:**
```
1. Use Agent 1's intent and extracted_identifiers to execute the right queries.
2. Retrieve complete, current records for all relevant entities.
3. Return structured query results for downstream analysis.
```

**MCP to add:** `iceberg-mcp-server` — add all available functions.

**Database tables available:**

| Table | Key Columns |
|-------|-------------|
| `customers` | `customer_id`, `full_name`, `email`, `phone`, `kyc_status` |
| `accounts` | `account_id`, `customer_id`, `account_type`, `account_number_masked`, `current_balance`, `available_balance`, `status`, `lock_reason` |
| `transactions` | `transaction_id`, `account_id`, `customer_id`, `amount`, `status`, `initiated_at`, `failure_reason`, `notes` |
| `loans` | `loan_id`, `customer_id`, `loan_type`, `outstanding_balance`, `monthly_payment`, `next_payment_date`, `payments_overdue`, `status` |
| `cards` | `card_id`, `account_id`, `customer_id`, `card_type`, `card_number_masked`, `status`, `block_reason`, `credit_limit` |
| `support_cases` | `case_id`, `customer_id`, `case_type`, `status`, `priority`, `account_id`, `created_at` |

---

### Agent 3 — Risk Analyst

| Field | Value |
|-------|-------|
| **Name** | `Risk Analyst` |
| **Role** | `Cross-Session Pattern Detection & Escalation Strategy Specialist` |
| **LLM Model** | `gpt-4o (Default)` |

**Backstory:**
```
You see what individual sessions cannot. By combining live data from the database with the customer's prior interaction history from memory, you detect whether the current issue is a new, isolated problem — or part of a larger pattern that has been building across sessions. Your risk assessments drive escalation decisions and shape how the Support Advisor responds.
```

**Goal:**
```
1. Synthesise Agent 1 (prior memory) with Agent 2 (live data) to detect cross-session patterns.
2. Assign a risk tier and identify the escalation path.
3. Produce a response strategy brief for the Support Advisor.
```

**Tools / MCP:** None — this agent uses pure LLM reasoning over the outputs of Agents 1 and 2.

---

### Agent 4 — Support Advisor

| Field | Value |
|-------|-------|
| **Name** | `Support Advisor` |
| **Role** | `Customer Response Composition & Memory Persistence Specialist` |
| **LLM Model** | `gpt-4o (Default)` |

**Backstory:**
```
You are the voice of the bank. You take everything the pipeline has uncovered — prior history, live data, risk analysis — and turn it into a clear, empathetic, actionable response that protects the customer. You are also the pipeline's memory keeper: the last thing you do in every interaction is store a structured memory note so the next session starts with full context.
```

**Goal:**
```
1. Compose a customer response that integrates prior context, live data, and risk analysis.
2. Acknowledge prior interactions explicitly — the customer should feel remembered.
3. If a cross-session pattern was detected, surface it clearly and empathetically.
4. Store a structured memory note via MCP add_memory after every interaction.
```

**MCP to add:** `lightmem-chroma` — select **`get_timestamp`** and **`add_memory`** functions.

---

## Step 4: Add All Four Tasks

Click **Save & Next** to advance to **Step 2: Add Tasks**.

Since this is a **sequential (non-conversational) workflow**, each agent needs a task that defines what it does. Create one task per agent using the definitions below.

> Click **+ Add Task** for each task. Assign each task to its corresponding agent using the **Agent** dropdown.

---

### Task 1 — Memory Retrieval & Intent Classification
**Assigned to:** Memory Scout

```
Given the customer's message {input}, first extract the customer's identifying
information (name, customer ID, phone number, or email) from the message.

Call retrieve_memory using ONLY that identity information as the query — never
include issue descriptions or situation keywords (e.g. "account locked",
"card declined"). Always pass the customer's name or ID as a filters argument
to scope retrieval to this customer only.

  Correct:  retrieve_memory(query="Sarah Williams",
                            filters=customer_name:"Sarah Williams", limit=5)
  Wrong:    retrieve_memory(query="Sarah Williams account locked card declined")

Review prior notes to summarise past sessions, flagging any open or unresolved
cases. Classify the message into one of the five intent categories:
  - ACCOUNT_STATUS
  - TRANSACTION_INQUIRY
  - LOAN_INQUIRY
  - CARD_INQUIRY
  - FRAUD_REPORT

Extract all available identifiers from the message text; if absent, infer from
prior memory. Produce a structured context brief for the next agent.
```

**Expected output format:**
```json
{
  "intent": "FRAUD_REPORT",
  "extracted_identifiers": {
    "customer_id": "CUST-B003",
    "full_name": "Maria Garcia"
  },
  "prior_sessions": [
    {
      "session_date": "2026-03-12",
      "query_type": "ACCOUNT_STATUS",
      "summary": "Account locked due to FRAUD_ALERT. CASE-2026-0001 OPEN HIGH.",
      "case_ref": "CASE-2026-0001",
      "resolved": false
    }
  ],
  "open_unresolved_cases": ["CASE-2026-0001"],
  "prior_context_flag": "ACTIVE_FRAUD_CASE"
}
```

---

### Task 2 — Database Query
**Assigned to:** Data Analyst

```
Using the intent and identifiers from Agent 1, execute the appropriate queries
against iceberg-mcp-server (database: banking_chatbot_db):

  - ACCOUNT_STATUS:     query accounts + open support_cases
  - TRANSACTION_INQUIRY: retrieve the transaction(s) plus failure/dispute details
  - FRAUD_REPORT:       retrieve last 20 transactions + open fraud cases + account status
  - CARD_INQUIRY:       join cards with accounts
  - LOAN_INQUIRY:       retrieve loan records; compute arrears as
                        monthly_payment × payments_overdue

Return all results as structured data for downstream agents.
```

---

### Task 3 — Pattern Analysis & Risk Assessment
**Assigned to:** Risk Analyst

```
Synthesise Agent 1's prior session history with Agent 2's live data to detect
cross-session patterns — such as a prior fraud case followed by a social
engineering contact, or a prior account lock followed by a password-reset request.

Assign a risk tier: LOW, MEDIUM, HIGH, or CRITICAL.
Determine the appropriate escalation path.

Produce a response strategy brief for the Support Advisor specifying:
  - what facts to lead with
  - which prior context to reference explicitly
  - how to frame any cross-session connection
  - tone adjustments
  - any critical safety instructions the customer must receive
```

**Expected output format:**
```json
{
  "risk_tier": "CRITICAL",
  "cross_session_pattern_detected": true,
  "pattern_type": "COORDINATED_ATTACK",
  "pattern_description": "...",
  "escalation_path": "FRAUD_SPECIALIST_URGENT",
  "response_strategy": {
    "lead_with": "...",
    "reference_prior_context": "...",
    "tone": "Calm, urgent, protective."
  }
}
```

---

### Task 4 — Respond, Report & Store Memory
**Assigned to:** Support Advisor

```
Using all prior agent outputs, compose a warm, direct, and actionable
customer-facing response:
  - Lead with explicit safety instructions for any fraud or scam scenario
  - Reference prior case numbers and session dates when memory exists —
    the customer should never feel like they are starting from zero
  - Surface cross-session connections empathetically when Agent 3
    detected a pattern
  - Proactively offer escalation for any CRITICAL, HIGH, or fraud-related
    risk tier

After composing the response, call get_timestamp then add_memory to persist
a structured memory note. The assistant_reply stored must be the structured
memory note — NOT the customer response text.

Set force_extract: true for any FRAUD_REPORT, CRITICAL or HIGH risk tier,
or any session where a cross-session link was detected.
Populate SUPERSEDES to chain back to the prior note on follow-up sessions.

Memory note format:
  CUSTOMER: <name> (<customer_id>)
  SESSION: <date>
  QUERY TYPE: <intent>
  ACCOUNT: <account details>
  ISSUE: <what happened>
  CROSS-SESSION LINK: <pattern description or None>
  RISK TIER: <tier>
  ACTION TAKEN: <what was done>
  ESCALATED: <yes/no and team>
  CASE REF: <case id>
  SUPERSEDES: <prior note reference if applicable>
```

---

## Step 5: Configure MCP Parameters

Click **Save & Next** to advance to **Step 3: Configure**.

### LightMem MCP — lightmem-chroma (Agents 1 and 4)

Fill in the same values for both agents that use this MCP:

| Parameter | Value |
|-----------|-------|
| **OPENAI_API_KEY** | Provided by instructor |
| **CHROMA_HOST** | Your own ChromaDB URL from Part 1 (for empty-memory testing) **or** the shared URL for pre-loaded memories |
| **LIGHTMEM_COLLECTION_NAME** | Your chosen collection name (e.g. `banking_test`) — use a unique name to start fresh, or `banking_chatbot_memory` for existing data |

> **Testing cross-session memory:**
> - **No memory (your own ChromaDB):** The pipeline completes but Agent 1 finds no prior context. All sessions are treated as first-contact.
> - **With memory (shared ChromaDB + `banking_chatbot_memory`):** Agent 1 retrieves prior notes, Agent 3 detects patterns across sessions, and the Support Advisor's response references previous interactions.

### Iceberg MCP — iceberg-mcp-server (Agent 2)

| Parameter | Value |
|-----------|-------|
| **IMPALA_HOST** | `hue-impala-gateway.datalake.bdqdgc.c0.cloudera.site` |
| **IMPALA_PORT** | `443` |
| **IMPALA_USER** | `qishuai` |
| **IMPALA_PASSWORD** | Provided by instructor |
| **IMPALA_DATABASE** | `banking_chatbot_db` |

Click **Save & Next** to proceed to **Test**.

---

## Step 6: Test the Workflow

### Test Scenario A — First Contact (No Prior Memory)

Use this message to simulate a customer's first contact:

```
Hi, I'm Maria Garcia. My debit card just got declined at the supermarket
and I can't see my checking account balance in the app. What's happening?
```

**Expected behaviour:**
- Agent 1 retrieves no prior memory (returns empty or no results)
- Agent 2 queries the database and finds `ACC-100006` locked due to `FRAUD_ALERT`, with two suspicious transactions
- Agent 3 assigns risk tier `HIGH` (no cross-session pattern — first contact)
- Agent 4 explains the account lock, names the suspicious transactions, provides a case reference, and stores a memory note

---

### Test Scenario B — Cross-Session Follow-up (With Prior Memory)

To experience cross-session detection, **first switch to the shared ChromaDB** (with pre-loaded memories), then use this follow-up message from the same customer:

```
Hi, I just got a call from someone saying they're from the bank's fraud department.
They said my account is still under investigation and they need me to transfer $500
to a "safe account" to protect my money. It felt weird. Should I do it?
```

**Expected behaviour:**
- Agent 1 retrieves the prior note for Maria Garcia (from Session A — FRAUD_ALERT, CASE-2026-0001)
- Agent 2 confirms the account is still locked and the prior case is `IN_PROGRESS`
- Agent 3 detects a **`COORDINATED_ATTACK`** pattern — card compromise followed 7 days later by impersonation call — and assigns `CRITICAL` risk tier
- Agent 4 leads with immediate safety instructions, explicitly references CASE-2026-0001, explains the two-event pattern, escalates urgently, and stores a new memory note with `SUPERSEDES` linking back to Session A

---

### Test Scenario C — Account Locked After Failed Logins

```
Hi, my name is Sarah Williams. I've been trying to log into my account
for the past hour and it keeps saying my password is wrong. Now I'm getting
a message that my account is locked. My debit card is also being declined.
I haven't done anything suspicious — I just forgot my password and kept retrying.
```

---

## Step 7: Deploy the Workflow

Once testing is satisfactory, click **Save & Next** > **Deploy** to publish the workflow as a live agent application.

---

## Workflow Summary

| Agent | Responsibility | Tools / MCP |
|-------|---------------|-------------|
| **Memory Scout** | Retrieve prior context, classify intent, extract identifiers | `lightmem-chroma` → `retrieve_memory` |
| **Data Analyst** | Execute live database queries | `iceberg-mcp-server` |
| **Risk Analyst** | Cross-session pattern detection, risk tier, escalation strategy | None (LLM reasoning) |
| **Support Advisor** | Compose response, store memory note | `lightmem-chroma` → `get_timestamp`, `add_memory` |

---

## Key Takeaways

1. **Sequential vs Hierarchical**: This workflow is a pipeline — no manager agent routes requests; each agent runs in order and passes output to the next
2. **Memory bookends the pipeline**: Agent 1 reads from memory before any data query; Agent 4 writes to memory after every interaction
3. **Identity-only retrieval**: Agent 1 must query memory with customer identity only — mixing situation keywords causes semantic leakage, returning other customers' records
4. **Cross-session intelligence**: The same `LIGHTMEM_COLLECTION_NAME` across sessions is what enables pattern detection — a different collection name starts fresh
5. **Force extract**: For FRAUD, CRITICAL, or HIGH risk, `force_extract: true` ensures the memory note is stored even if LightMem's summarisation threshold is not met

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Agent 1 returns no memory | Expected if using your own empty ChromaDB — switch to shared URL with pre-loaded collection to test retrieval |
| Agent 2 query fails | Verify `IMPALA_HOST`, `IMPALA_USER`, and `IMPALA_PASSWORD` are correct; check `IMPALA_DATABASE` is `banking_chatbot_db` |
| Memory retrieved for wrong customer | Agent 1 task must pass identity info as `filters` argument — remove situation keywords from the query |
| Agent 4 does not store memory | Check `OPENAI_API_KEY` and `CHROMA_HOST` are set for Agent 4's MCP configuration |
| Cross-session pattern not detected | Ensure both sessions use the same `CHROMA_HOST` and `LIGHTMEM_COLLECTION_NAME` |
