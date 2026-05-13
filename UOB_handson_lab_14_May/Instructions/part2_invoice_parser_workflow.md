# Part 2: Building the Invoice Parser Workflow with Memory

## Overview

In this part you build a **conversational hierarchical workflow** that:
1. Accepts invoice image uploads, extracts text via PaddleOCR, and stores results in ChromaDB through LightMem
2. Answers questions about previously processed invoices by retrieving them from memory — even in a new conversation session

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CONVERSATION 1 (Image Upload)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  User: [uploads invrec_00216.png] "Process this invoice"                    │
│                          ↓                                                  │
│  Invoice OCR & Memory Agent                                                 │
│    ├── PaddleOCR Tool → extracts structured text from image                 │
│    └── LightMem add_memory → stores result in ChromaDB                      │
│  Agent: "Invoice processed and stored. Vendor: Yucca de luc, Total: $47..." │
└─────────────────────────────────────────────────────────────────────────────┘

              ═══════ PAGE REFRESH / NEW CONVERSATION ═══════

┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONVERSATION 2 (Memory Retrieval)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  User: "What's the total amount of invoice 216?"                            │
│                          ↓                                                  │
│  Invoice Query Agent                                                        │
│    └── LightMem retrieve_memory → semantic search in ChromaDB               │
│  Agent: "Based on stored data, the total for invrec_00216 was $47.68"       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Workflow Architecture

| Setting | Value |
|---------|-------|
| **Process** | Hierarchical |
| **Conversational** | Yes |
| **Manager Agent** | Custom (Invoice Assistant Manager) |
| **Worker Agents** | Invoice OCR & Memory Agent, Invoice Query Agent |

---

## Prerequisites

- Part 1 completed: ChromaDB application is running and LightMem MCP + PaddleOCR Tool are registered
- Your ChromaDB URL (from Part 1 Section A)
- OpenAI API key (provided by the instructor)
- PaddleOCR endpoint URL and API key (provided below)

**Connection Details for This Lab:**

| Parameter | Value |
|-----------|-------|
| **PaddleOCR endpoint_url** | `https://qzhong-cai-inference.qzhong-1.a465-9q4k.cloudera.site/namespaces/serving-default/endpoints/paddle-ocr/v1/infer` |
| **PaddleOCR api_key** | See expandable section below |
| **CHROMA_HOST** | `https://chroma-db-1-dwaf-ayqo-3gwk-oaei.ml-e0565700-5cc.datalake.bdqdgc.c0.cloudera.site/` (or your own ChromaDB app URL from Part 1) |
| **LIGHTMEM_COLLECTION_NAME** | `invoice` (or any name you choose) |
| **OPENAI_API_KEY** | Provided by instructor |

<details>
<summary>Click to expand PaddleOCR api_key</summary>

```
eyJqa3UiOiJodHRwczovL3F6aG9uZy0xLWF3LWRsLWdhdGV3YXkucXpob25nLTEuYTQ2NS05cTRrLmNsb3VkZXJhLnNpdGUvcXpob25nLTEtYXctZGwvaG9tZXBhZ2Uva25veHRva2VuL2FwaS92Mi9qd2tzLmpzb24iLCJraWQiOiI2SmlETWRBVjVFN2ljenJTRHE2M1lwU1Y4UjQ2aG8tV2l2QjlyMkNFOFBJIiwidHlwIjoiSldUIiwiYWxnIjoiUlMyNTYifQ.eyJzdWIiOiJzcnZfYWlfaW5mZXJlbmNlX3VzZXIiLCJhdWQiOiJjZHAtcHJveHktdG9rZW4iLCJqa3UiOiJodHRwczovL3F6aG9uZy0xLWF3LWRsLWdhdGV3YXkucXpob25nLTEuYTQ2NS05cTRrLmNsb3VkZXJhLnNpdGUvcXpob25nLTEtYXctZGwvaG9tZXBhZ2Uva25veHRva2VuL2FwaS92Mi9qd2tzLmpzb24iLCJraWQiOiI2SmlETWRBVjVFN2ljenJTRHE2M1lwU1Y4UjQ2aG8tV2l2QjlyMkNFOFBJIiwiaXNzIjoiS05PWFNTTyIsImV4cCI6MTc3OTI0NTAwOCwibWFuYWdlZC50b2tlbiI6InRydWUiLCJrbm94LmlkIjoiODQ5MWZkODEtMzEzYS00MjFkLWIxYWItM2U2MGYxNzBmOTQxIn0.igx8Bb9rIZCmLP8OVvk67VqpkthSgb735tQ9nXqZzVZG_6m1icWoMUxXYPWgGJqUUD-PCl7H8ReVcueSqjckzWdEKAsoPhAjx9ggaRr1mhC3JIUHPdleahPv7OEKIvmLC-sW2vlbKJeH_EYqloqfUK66c_thvtUCRyy5PGrJfWqo85aF6eQf9YC8b0eP97Fe03qbAX5h9qvB3YANcwYnCwE2NtJeZ-xrxpKqmgdBn6e0IOC3-danT_x9jfiB7WPYERzb1eZf9vhBuXFFLUqgcIWZi6Ignt9oiiDiVal4G5ifj6QgD1CSRu3GKZx1CMwAtAQNsPFzPyprFVQlAD5dww
```

</details>

---

## Step 1: Create the Workflow

In Agent Studio, click **Agentic Workflows** in the top navigation, then click **Create Workflow** (or the **+** button).

The **Create New Workflow** dialog opens. Select **New Workflow** (build from scratch), then enter the workflow name on the right:

- **Workflow Name**: `Invoice Parser Workflow with Memory`

![Create New Workflow](../images/invoice_parser_workflow/create_invoice_parser_workflow_w_memory.png)

Click **Create Workflow**. You are taken to the **Edit Workflow** editor, starting at Step 1: **Add Agents**.

---

## Step 2: Configure Workflow Settings

The editor shows two toggle options at the top of the canvas:

![Workflow Editor — Add Agents](../images/invoice_parser_workflow/editor_of_the_workflow_and_add_first_agent.png)

Enable both toggles:

| Toggle | Action | Why |
|--------|--------|-----|
| **Is Conversational** | Turn **ON** | Enables back-and-forth chat; no fixed task sequence needed |
| **Manager Agent** | Turn **ON** | Adds a manager agent that routes requests to worker agents |

After enabling both, the **Default Manager** card appears with a **Configure** button:

![Enable Conversational and Manager Agent](../images/invoice_parser_workflow/change_workflow_to_conversation_input_and_configure_manager_agent.png)

Click **Configure** under Default Manager to set up a custom manager agent.

---

## Step 3: Add the Manager Agent

The **Add Manager Agent** panel opens. Fill in the following details:

![Add Manager Agent Configuration](../images/invoice_parser_workflow/add_manager_agent_using_given_configuration.png)

| Field | Value |
|-------|-------|
| **Role** | `Conversational Invoice Workflow Coordinator` |
| **LLM Model** | `gpt-4o (Default)` |

**Backstory** — copy and paste this exactly:
```
You manage an invoice processing system with two specialized agents. You analyze each user message to determine the appropriate action:

1. When the user uploads an image file (check {Attachments}):
   - Delegate to the Invoice OCR & Memory Agent to extract and store the data

2. When the user asks questions about invoices (by name, vendor, amount, date, etc.):
   - Delegate to the Invoice Query Agent to retrieve from memory and answer

3. For general conversation or unclear requests:
   - Ask clarifying questions or provide helpful guidance about the system's capabilities

Always provide clear, helpful responses based on the delegated agent's output.
```

**Goal** — copy and paste this exactly:
```
Coordinate invoice processing by routing image uploads to the OCR agent for extraction and storage, and routing invoice queries to the Query agent for memory retrieval. Ensure users receive accurate, timely responses about their invoices.
```

Click **Add Manager Agent** to save.

---

## Step 4: Create the First Worker Agent — Invoice OCR & Memory Agent

Back in the workflow editor, click **+ Add Your First Agent** (or **Create or Edit Agents**).

The **Create or Edit Agent** panel opens. Click **Create New Agent** and fill in:

![Create Invoice OCR & Memory Agent](../images/invoice_parser_workflow/editing_invoice_ocr_and_memory_agent.png)

| Field | Value |
|-------|-------|
| **Name** | `Invoice OCR & Memory Agent` |
| **Role** | `Invoice Data Extractor with Memory Storage` |
| **LLM Model** | `gpt-4o (Default)` |

**Backstory** — copy and paste this exactly:
```
You specialize in extracting data from invoice images using OCR and storing the results in persistent memory. When a user uploads an image, you extract all relevant information and store it with the image filename as the key identifier for future retrieval.

IMPORTANT - Memory Storage Format:
When storing invoice data using add_memory, you MUST format the data as follows:
- user_input: Set to the image filename (e.g., "invoice_001.jpg")
- assistant_reply: A structured JSON string containing:
  {
    "filename": "<image filename>",
    "extracted_text": "<raw OCR text>",
    "parsed_fields": {
      "vendor": "<vendor name if found>",
      "invoice_number": "<invoice number if found>",
      "date": "<invoice date if found>",
      "total_amount": "<total amount if found>",
      "line_items": [<list of items if found>]
    }
  }

This structured format enables accurate retrieval in future conversations.
```

**Goal** — copy and paste this exactly:
```
Extract invoice data using PaddleOCR, parse the key fields (vendor, invoice number, date, amount, line items), and store it in LightMem memory with the image filename as the identifier. Always use the structured JSON format for storage.
```

Click **Create Agent** (do not save yet — you still need to add tools and MCP).

### Step 4.1: Add PaddleOCR Tool to the First Agent

Scroll down on the agent form to the **Add Tools** section and click **+ Create or Edit Tools**.

In the tools dialog, search for `padd` under **Create Tool From Template**. Select **PaddleOCR Tool**:

![Create PaddleOCR Tool from Template](../images/invoice_parser_workflow/create_paddleocr_tool_from_template.png)

Click **Create Tool from Template**. The tool is added to this agent. You will see it appear under **Add Tools** in the agent form:

![Agent with Tool Added](../images/invoice_parser_workflow/add_tool_to_the_first_agent.png)

### Step 4.2: Add LightMem MCP to the First Agent

In the same agent form, click **+ Add MCP Server to Agent** under **Add MCP Servers**.

The **Add or Edit MCPs** dialog opens. Select **lightmem-chroma** from the list on the left. On the right, fill in the environment variable values:

![Add LightMem MCP to First Agent](../images/invoice_parser_workflow/add_lightmem_mcp_to_agent.png)

| Environment Variable | Value |
|---------------------|-------|
| **OPENAI_API_KEY** | Your OpenAI API key (provided by instructor) |
| **CHROMA_HOST** | `https://chroma-db-1-dwaf-ayqo-3gwk-oaei.ml-e0565700-5cc.datalake.bdqdgc.c0.cloudera.site/` (or your own ChromaDB URL from Part 1) |
| **LIGHTMEM_COLLECTION_NAME** | `invoice` |

Click **Add MCP Server to Agent**.

### Step 4.3: Save the First Agent

The agent now shows both **PaddleOCR Tool** and **lightmem-chroma** attached:

![Save First Agent](../images/invoice_parser_workflow/save_the_created_agent.png)

Click **Save Agent**.

---

## Step 5: Create the Second Worker Agent — Invoice Query Agent

In the **Create or Edit Agent** panel, click **Create New Agent** again and fill in:

![Create Invoice Query Agent](../images/invoice_parser_workflow/add_second_agent_memory_retrieval_specialist.png)

| Field | Value |
|-------|-------|
| **Name** | `Invoice Query Agent` |
| **Role** | `Invoice Memory Retrieval Specialist` |
| **LLM Model** | `gpt-4o (Default)` |

**Backstory** — copy and paste this exactly:
```
You help users query previously processed invoices from memory. When users ask about an invoice by name or content, you retrieve the stored OCR data and provide accurate answers.

IMPORTANT - Retrieved Memory Format:
Retrieved memories contain structured invoice data in this format:
- The memory text contains: "User: <filename>\nAssistant: <JSON data>"
- The JSON data includes: filename, extracted_text, and parsed_fields
- parsed_fields contains: vendor, invoice_number, date, total_amount, line_items

When answering user questions:
1. Parse the retrieved JSON to extract the specific field they're asking about
2. If they ask about "total" or "amount", look in parsed_fields.total_amount
3. If they ask about "vendor" or "company", look in parsed_fields.vendor
4. For general questions, summarize the relevant parsed_fields
```

**Goal** — copy and paste this exactly:
```
Retrieve invoice data from LightMem memory based on user queries (invoice name, vendor, amount, etc.) and provide accurate, helpful responses. Parse the structured JSON in retrieved memories to answer specific questions about invoice contents.
```

Click **Create Agent**.

### Step 5.1: Add LightMem MCP to the Second Agent

Click **+ Add MCP Server to Agent** and select **lightmem-chroma** again. Fill in the same environment variable values as in Step 4.2:

![Add LightMem MCP to Second Agent](../images/invoice_parser_workflow/add_same_memory_mcp_to_second_agent.png)

| Environment Variable | Value |
|---------------------|-------|
| **OPENAI_API_KEY** | Your OpenAI API key |
| **CHROMA_HOST** | Your ChromaDB URL |
| **LIGHTMEM_COLLECTION_NAME** | `invoice` |

Click **Add MCP Server to Agent**.

### Step 5.2: Add Write to Shared PDF Tool

Click **+ Create or Edit Tools**. In the dialog, search for `share` under **Create Tool From Template** and select **Write to Shared PDF**:

![Add Write to Shared PDF Tool](../images/invoice_parser_workflow/second_agent_add_pdf_writing_tool.png)

Click **Create Tool from Template**, then click **Save Agent**.

---

## Step 6: Skip the Add Tasks Step

Click **Save & Next** to advance to **Step 2: Add Tasks**.

Because this is a **conversational workflow**, no explicit task definitions are required — the Manager Agent handles routing dynamically. You will see a default task already present and a visual diagram of your workflow:

![Skip Add Tasks Step](../images/invoice_parser_workflow/skip_task_as_it_is_conversation_based_workflow.png)

The diagram confirms your workflow structure:
- **Conversation** node at the top
- **Invoice Assistant Manager** routing to two workers
- **Invoice OCR & Memory Agent** with PaddleOCR Tool and lightmem-chroma
- **Invoice Query Agent** with Write to Shared PDF and lightmem-chroma

Click **Save & Next** to proceed to **Configure**.

---

## Step 7: Configure Tool and MCP Parameters

In **Step 3: Configure**, you set the runtime values for each tool and MCP server.

![Configure Tool and MCP Parameters](../images/invoice_parser_workflow/add_parameters_for_paddleocr_and_verify_mcp_parameters.png)

### PaddleOCR Tool (Agent: Invoice OCR & Memory Agent)

| Parameter | Value |
|-----------|-------|
| **endpoint_url** | `https://qzhong-cai-inference.qzhong-1.a465-9q4k.cloudera.site/namespaces/serving-default/endpoints/paddle-ocr/v1/infer` |
| **api_key** | The JWT token from the Prerequisites section above |
| **timeout_seconds** | Leave blank (uses default of 60s) |

### LightMem MCP — lightmem-chroma (Both Agents)

You will see the MCP parameters listed for each agent that uses lightmem-chroma. Verify or fill in:

| Parameter | Value |
|-----------|-------|
| **OPENAI_API_KEY** | Your OpenAI API key |
| **CHROMA_HOST** | `https://chroma-db-1-dwaf-ayqo-3gwk-oaei.ml-e0565700-5cc.datalake.bdqdgc.c0.cloudera.site/` (or your own) |
| **LIGHTMEM_COLLECTION_NAME** | `invoice` |

> **Note:** The same collection name must be used by both agents so the OCR agent writes to the same collection the Query agent reads from.

Click **Save & Next** to proceed to **Test**.

---

## Step 8: Test the Workflow

### Step 8.1: Test Invoice Upload and OCR Extraction

In the **Test** tab, you will see a chat interface on the left and a panel with **Flow Diagram**, **Logs**, **Monitoring**, and **Artifact Files** on the right.

1. Click the **attachment icon** (paperclip) in the chat input
2. Upload a sample invoice image (e.g., `invrec_00216.png`)
3. The uploaded file appears in the **Artifact Files** panel on the right
4. Click **Send** (arrow button) without typing a message — or type "Process this invoice"

![Test — Upload Invoice](../images/invoice_parser_workflow/test_workflow_upload_new_invoice.png)

The workflow will:
1. Route the upload to the **Invoice OCR & Memory Agent**
2. Call **PaddleOCR Tool** to extract text from the image
3. Call **LightMem add_memory** to store the structured result in ChromaDB

**Expected result:** The agent displays the invoice image and confirms the data was extracted and stored:

![Testing Result — OCR Success](../images/invoice_parser_workflow/testing_result.png)

The **Artifact Files** panel will show the uploaded image plus `state.json` and `plan.json` files generated during the workflow execution.

### Step 8.2: Test Memory Retrieval (New Conversation)

Now test that the workflow can answer questions from memory **without the image**. 

1. Start a new conversation (click the refresh / new chat icon, or simply continue in the same test session)
2. Type a query referencing the invoice you just processed:

```
what's the total amount of the invoice 216
```

![Test — Memory Retrieval Query](../images/invoice_parser_workflow/test_workflow_of_mem_retrieval.png)

The workflow routes this to the **Invoice Query Agent**, which calls **LightMem retrieve_memory** to semantically search ChromaDB and return the stored data.

### Understanding Test Results

**If the invoice was previously stored**, the Query Agent retrieves and answers accurately.

**If the invoice has not been stored yet** (e.g., you query before uploading), you will see a response like this:

![Testing Result — No Memory Found](../images/invoice_parser_workflow/testing_results_with_no_specific_memory.png)

> *"It seems that we currently do not have any stored data for invoice number 216. Please ensure that this invoice has been processed and stored in the system..."*

This is expected behaviour — it confirms the agent is correctly querying memory rather than hallucinating an answer. Upload the invoice first (Step 8.1), then retry the query.

---

## Step 9: Deploy the Workflow

Once testing is successful, click **Save & Next** to advance to **Step 5: Deploy**.

The Deploy page shows a full summary of your workflow — Manager Agent, worker agents, and their tools:

![Deploy Workflow](../images/invoice_parser_workflow/deploy_the_workflow.png)

Click **Deploy** to publish the workflow. It will be available as a live agent application that any user can access.

> **Save as Template (optional):** Before deploying, click **Save as Template** to export this workflow as a reusable template zip file. This is useful for sharing the workflow with others or restoring it later.

---

## Workflow Summary

| Component | Role | Tools / MCP |
|-----------|------|-------------|
| **Invoice Assistant Manager** | Routes user messages to the right worker | — |
| **Invoice OCR & Memory Agent** | Extracts text from images, stores in ChromaDB | PaddleOCR Tool, lightmem-chroma (`add_memory`, `get_timestamp`) |
| **Invoice Query Agent** | Retrieves stored invoice data to answer queries | lightmem-chroma (`retrieve_memory`), Write to Shared PDF |

---

## Key Takeaways

1. **Conversational + Hierarchical**: Enabling both toggles removes the need for fixed task definitions — the Manager Agent decides what to do based on each message
2. **Cross-Session Memory**: LightMem + ChromaDB stores extracted invoice data outside the session, so it survives page refreshes and new conversations
3. **Structured Storage Format**: The OCR Agent stores results as structured JSON keyed by filename, enabling precise retrieval by the Query Agent
4. **Same Collection Name**: Both agents must use the same `LIGHTMEM_COLLECTION_NAME` — write and read go to the same ChromaDB collection

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| OCR returns empty or garbled text | Check that `endpoint_url` and `api_key` are correct; verify the PaddleOCR service is running |
| Memory not found after upload | Ensure both agents use the same `LIGHTMEM_COLLECTION_NAME` and the same `CHROMA_HOST` |
| MCP fails to start | Verify `OPENAI_API_KEY` is valid and `CHROMA_HOST` URL is reachable |
| Manager routes to wrong agent | Review the Manager Agent backstory — it uses `{Attachments}` to detect image uploads |
| Workflow stuck at "processing" | Check the **Logs** tab in the Test panel for error details |
