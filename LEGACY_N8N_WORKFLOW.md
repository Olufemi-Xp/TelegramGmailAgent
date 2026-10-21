# Telegram AI Assistant - Gmail Agentic Workflow

An autonomous, agentic AI workflow deployed inside your local **n8n** instance (`http://localhost:5678`) that listens to instructions via **Telegram**, maintains conversational memory across messages, and sends emails through your authenticated **Gmail** account using high-speed LLM reasoning powered by **Groq**.

---

## 🏗️ Architecture & Flow

```mermaid
flowchart LR
    User([Telegram User]) -->|Sends command| TG[Telegram Trigger Node]
    TG -->|chat.id & message.text| Agent[AI Agent (LangChain)]
    
    subgraph Agent Sub-Components
        LLM[Groq Chat Model] -.->|Reasoning Engine| Agent
        Mem[Window Buffer Memory] <-->|Scoped by Chat ID| Agent
        GmailTool[Gmail Send Tool] <-->|AI Tool Calls| Agent
    end
    
    Agent -->|output response| TGReply[Reply to Telegram Node]
    TGReply -->|Confirmation / Clarification| User
    GmailTool -->|Sends Email| EmailRecipient([Recipient Email])
```

---

## 🧩 Nodes Breakdown

| Node Name | Node Type | Purpose | Configuration / Credentials |
| :--- | :--- | :--- | :--- |
| **Telegram Trigger** | `n8n-nodes-base.telegramTrigger` | Listens for incoming chat messages from Telegram. | Credentials: `Telegram account` (`telegramApi`) |
| **AI Agent** | `@n8n/n8n-nodes-langchain.agent` | Core conversational reasoning loop. Evaluates instructions, manages tools, and decides when to ask for clarification or send an email. | Prompt: `={{ $json.message.text }}` with tailored Executive Assistant System Prompt |
| **Groq Chat Model** | `@n8n/n8n-nodes-langchain.lmChatGroq` | Fast LLM inference engine capable of structured function calling. | Model: `openai/gpt-oss-120b` (or `llama-3.3-70b-versatile`), Credentials: `Groq account` |
| **Window Buffer Memory** | `@n8n/n8n-nodes-langchain.memoryBufferWindow` | Remembers the last 10 messages of the conversation. | Session Key: `={{ $('Telegram Trigger').item.json.message.chat.id }}` (Per-chat isolation) |
| **Send a message in Gmail** | `n8n-nodes-base.gmailTool` | AI tool enabling the agent to send emails. | Credentials: `Gmail account` (`gmailOAuth2`), Dynamic AI parameters (`To`, `Subject`, `Message`) |
| **Reply to Telegram** | `n8n-nodes-base.telegram` | Delivers the agent's answer or email confirmation back to the Telegram chat. | Chat ID: `={{ $('Telegram Trigger').item.json.message.chat.id }}`, Message: `={{ $json.output }}` |

---

## 🚀 Accessing & Activating in n8n

The workflow has been imported into your running n8n instance:

- **Workflow Name:** `Telegram AI Assistant - Gmail Agent`
- **Workflow ID:** `QssrJ4V8SDZkeSGf`
- **Direct Link:** [http://localhost:5678/workflow/QssrJ4V8SDZkeSGf](http://localhost:5678/workflow/QssrJ4V8SDZkeSGf)

### How to Activate:
1. Open [http://localhost:5678/workflow/QssrJ4V8SDZkeSGf](http://localhost:5678/workflow/QssrJ4V8SDZkeSGf) in your browser.
2. Verify all nodes show green checks for their credentials (`Telegram account`, `Groq account`, `Gmail account`).
3. Toggle the **Active** switch in the top right corner to **ON** to register the Telegram webhook.

---

## 🌐 Note on Telegram Webhooks in Local Docker

Telegram's servers send webhook requests to your n8n instance over the public internet with HTTPS:
- If your n8n container is behind a local network/NAT without a public domain, Telegram cannot reach `http://localhost:5678` directly.
- **Solution:** Expose your local n8n instance using a tunnel such as **ngrok** or **Cloudflare Tunnel**:
  ```bash
  ngrok http 5678
  ```
  Then in your n8n Docker environment, configure:
  ```env
  WEBHOOK_URL=https://your-tunnel-subdomain.ngrok-free.app/
  ```
  Or test manually in n8n using **"Test step"** / **"Listen for test event"** inside the workflow editor.

---

## 💬 Example Telegram Instructions

Send any of the following messages to your Telegram bot:

1. **Email instruction:**
   > *"Send an email to john.doe@example.com with the subject 'Q4 Financial Update' saying the report has been finalized and attached."*

2. **Clarification flow (testing memory):**
   > *"I need you to send an email to Sarah."*
   >
   > *Bot:* "Sure, what is Sarah's email address and what should the subject and message be?"
   >
   > *"Her email is sarah@acme.org and tell her our meeting is moved to 3 PM."*
   >
   > *Bot:* [Calls Gmail Tool] -> "The email to sarah@acme.org with the subject 'Meeting Rescheduled' has been sent successfully!"

3. **General assistant queries:**
   > *"What tools do you have access to?"*
