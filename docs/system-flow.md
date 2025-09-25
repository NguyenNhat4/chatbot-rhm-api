# Chatbot System Flow Guide

This document visualizes how the chatbot-rhm frontend and backend coordinate to handle chat conversations.

## High-Level Architecture

```mermaid
graph TD
    U[End User] -->|messages & role pick| UI[Next.js UI\n(chatbot-rhm-ui)]
    UI -->|REST calls via chatApi| API[FastAPI backend\n(chatbot-rhm-api)]
    API -->|runs| Flows[PocketFlow pipelines]
    Flows -->|vector search| KB[Role-aware Knowledge Base]
    API -->|persist chat history| DB[(PostgreSQL)]
    API -->|responses| UI
```

- `chatbot-rhm-ui` renders the chat interface and orchestrates API access through `lib/chat-context.tsx` and `lib/chat-api.js`.
- `chatbot-rhm-api` exposes REST routes (`api.py`) that wrap PocketFlow pipelines defined in `flow.py` and `OQA_nodes.py`.
- The backend stores threads/messages in the database and queries role-specific CSV knowledge bases via `utils/kb.py`.

## Frontend Message Lifecycle

```mermaid
sequenceDiagram
    participant U as User
    participant CI as ChatInput
    participant CC as ChatContext
    participant API as chatApi
    participant BE as /api/chat
    participant PF as PocketFlow
    participant DB as Chat DB
    participant KB as Knowledge Base

    U->>CI: Type message & pick role
    CI->>CC: handleSendMessage(content, role)
    CC->>API: sendMessage(content, threadId, role)
    Note right of API: chatApi forces role = "orthodontist"
    API->>BE: POST /api/chat {message, role, session_id}
    BE->>DB: Validate thread ownership
    BE->>PF: Run med_flow or oqa_flow(shared)
    PF->>KB: Retrieve role-aligned context
    PF-->>BE: Explanation + suggestions
    BE->>DB: Insert user & bot ChatMessage records
    BE-->>API: ConversationResponse JSON
    API-->>CC: explanation, suggestions
    CC-->>CI: Update UI state
    CI-->>U: Render response & suggestions
```

Key frontend touchpoints:
- `ChatInput` notifies `Chat` via `onRoleChange`, updating background aesthetics (`chatbot-rhm-ui/app/dashboard/components/chat-input.tsx`, `chatbot-rhm-ui/app/dashboard/components/chat.tsx`).
- `ChatMessages` chooses between dental and endocrine imagery based on the selected role (`chatbot-rhm-ui/app/dashboard/components/chat-messages.tsx`).
- `chatApi` always submits the orthodontist persona to the backend (`chatbot-rhm-ui/lib/chat-api.js`).

## Backend Request Handling

```mermaid
sequenceDiagram
    participant BE as FastAPI /api/chat
    participant DB as SQLAlchemy Session
    participant MED as med_flow
    participant OQA as oqa_flow

    BE->>DB: Fetch ChatThread(thread_id)
    alt orthodontist role
        BE->>OQA: run(shared)
    else other role
        BE->>MED: run(shared)
    end
    BE->>DB: Add ChatMessage(user)
    BE->>DB: Add ChatMessage(bot)
    BE->>DB: Commit transaction
    BE-->>Client: ConversationResponse
```

Highlights from `chatbot-rhm-api/api.py`:
- Incoming requests default to `orthodontist` (`ConversationRequest.role`).
- The handler overrides any client-provided role to `orthodontist` before invoking flows.
- Responses include explanation text, follow-up suggestions, and flags such as `need_clarify`.

## PocketFlow Pipelines

### Medical Agent (general roles)

```mermaid
flowchart LR
    Ingest[IngestQuery]
    Main[MainDecisionAgent]
    Retrieve[RetrieveFromKB]
    Score[ScoreDecisionNode]
    Compose[ComposeAnswer]
    Clarify[ClarifyQuestionNode]
    Greeting[GreetingResponse]
    ChitChat[ChitChatRespond]
    Fallback[FallbackNode]

    Ingest --> Main
    Main -- "retrieve_kb" --> Retrieve
    Main -- "greeting" --> Greeting
    Main -- "chitchat" --> ChitChat
    Main -- "fallback" --> Fallback
    Retrieve --> Score
    Score -- "compose_answer" --> Compose
    Score -- "clarify" --> Clarify
    Compose -- "fallback" --> Fallback
    ChitChat -- "fallback" --> Fallback
```

### Orthodontist OQA Agent

```mermaid
flowchart LR
    OIngest[OQAIngestDefaults]
    OClassify[OQAClassifyEN]
    ORetrieve[OQARetrieve]
    OScore[ScoreDecisionNode]
    OCompose[OQAComposeAnswerVIWithSources]
    OClarify[OQAClarify]
    OChitChat[OQAChitChat]

    OIngest --> OClassify
    OClassify -- "retrieve_kb" --> ORetrieve
    OClassify -- "chitchat" --> OChitChat
    ORetrieve --> OScore
    OScore -- "compose_answer" --> OCompose
    OScore -- "clarify" --> OClarify
```

The OQA flow is optimized for orthodontist knowledge: classification decides between retrieval and chit-chat, and there is no fallback node because the pipeline is streamlined for a single specialty dataset.

## Data Storage Touchpoints

- Threads and messages persist through SQLAlchemy models (`database/models.py`), with each API call inserting both user and bot messages.
- Knowledge base lookups use TF-IDF matrices cached per role (`utils/kb.py`).

Use these diagrams as a starting point when onboarding new contributors or discussing changes to the conversation pipeline.
