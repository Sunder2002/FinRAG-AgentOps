# FinRAG AgentOps: Enterprise Financial Audit System

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Async-009688?style=for-the-badge&logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker)
![Redis](https://img.shields.io/badge/Redis-Message_Broker-DC382D?style=for-the-badge&logo=redis)
![Celery](https://img.shields.io/badge/Celery-Distributed_Task_Queue-37814A?style=for-the-badge&logo=celery)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent_State_Machine-orange?style=for-the-badge)

An asynchronous, edge-optimized multi-agent system designed to fetch, embed, and audit live financial documents. Built with production-grade decoupling, this system leverages LangGraph state machines and Google's Gemini reasoning models to automate complex financial analysis without blocking the main web thread.

---

## 🏗️ System Architecture

To ensure high availability and prevent LLM inference bottlenecks, the system is fully containerized and decoupled using an API Gateway and a Background Task Queue.

```text
[Client / User] 
       │
       ▼  (POST /api/v1/audit)
┌──────────────────────┐      Task ID      ┌──────────────────────┐
│   API Gateway        │ ─────────────────►│   Message Broker     │
│   (FastAPI)          │                   │   (Redis)            │
└──────────────────────┘                   └──────────────────────┘
       ▲                                              │
       │ (Polling GET /api/v1/audit/{id})             │ (Consumes Task)
       │                                              ▼
┌──────────────────────┐    Live Data      ┌──────────────────────┐
│   Data Sources       │ ◄──────────────── │   Worker Node        │
│   (SEC / Yahoo Fin)  │                   │   (Celery)           │
└──────────────────────┘                   └──────────────────────┘
                                                      │
                                                      ▼
                                       ┌──────────────────────────────┐
                                       │  LangGraph State Machine     │
                                       │  1. Analyst Node (FAISS RAG) │
                                       │  2. Auditor Node             │
                                       │  3. Compliance Node          │
                                       └──────────────────────────────┘
```

### The "Explain It Like I'm 5" Concept
Imagine a high-end, busy restaurant:
1. The **Waiter (FastAPI)** takes your order (a stock ticker) and hands you a receipt immediately. 
2. The Waiter puts the order ticket on the **Ticket Rail (Redis)**.
3. The **Chef (Celery Worker)** takes the ticket, gathers the raw ingredients (Live Market Data), and cooks the meal (AI Reasoning).
4. You check your receipt later, and your food (The Audit Report) is ready.

By separating the Waiter from the Chef, our restaurant never freezes, no matter how many customers walk in.

---

## 🌟 Core Features

* **Fully Asynchronous Handoff:** LLM inference is heavy. By offloading generation to Celery workers via Redis, the FastAPI endpoints maintain sub-millisecond response times.
* **Dynamic Data Routing:** The system intelligently identifies tickers. US equities are routed to the US Government SEC EDGAR API (with strict rate-limit semaphores), while International/Indian equities (e.g., `.NS`) are routed to global finance endpoints.
* **Multi-Agent Review Process:** LLMs hallucinate. We mitigate this using a LangGraph directed acyclic graph (DAG):
  * 🕵️ **Analyst Agent:** Extracts hard numbers from the vectorized data.
  * 📝 **Auditor Agent:** Drafts a professional financial opinion based *only* on the Analyst's extracted metrics.
  * 🛡️ **Compliance Agent:** Verifies the Auditor's tone, checks for assumptions, and ensures factual accuracy before clearing the report.
* **Dynamic Model Fallback:** Bypasses hardcoded SDK limits by dynamically querying the Google GenAI REST API on startup to select the most advanced available model, gracefully falling back from `1.5-pro` to `1.5-flash` during rate limits.

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Orchestration** | Docker & Docker Compose | Ensures environment parity and seamless deployment. |
| **API Gateway** | FastAPI (Python 3.12+) | High-performance, async REST API routing. |
| **Message Broker** | Redis 7 | In-memory queue linking the API and Workers. |
| **Task Queue** | Celery | Distributed background worker for long-running AI tasks. |
| **Vector Engine** | FAISS | CPU-optimized local vector search for RAG context retrieval. |
| **Embeddings** | HuggingFace Local | `all-MiniLM-L6-v2` for zero-latency, local chunk embedding. |
| **Agent Framework**| LangGraph & LangChain | State machine orchestration for multi-agent workflows. |
| **LLM Engine** | Google Gemini | Core reasoning and text generation. |

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
* Docker and Docker Compose installed.
* A valid Google Gemini API Key.

### 2. Environment Setup
Clone the repository and create a `.env` file in the root directory:
```env
GOOGLE_API_KEY="your_gemini_api_key_here"
SEC_USER_AGENT="YourName/1.0 (your.email@domain.com)"
```

### 3. Boot the Infrastructure
Spin up the entire microservice universe (API, Redis, Celery Worker, Vector DB) with a single command:
```bash
docker-compose up --build
```

### 4. Trigger an Audit
You can test the asynchronous pipeline using the included automated polling script. Open a separate terminal and run:
```bash
python run_client.py
```
*Note: You can modify `run_client.py` to test different tickers like `MSFT` (US SEC Data) or `RELIANCE.NS` (Indian Market Data).*

### 5. API Documentation
Once the containers are running, the interactive Swagger UI is automatically generated and available at:
👉 `http://localhost:8000/docs`


## 📂 Repository Structure
├── src/
│   ├── agents/
│   │   └── audit_graph.py      # LangGraph multi-agent logic
│   ├── api/                    # FastAPI routers and endpoints
│   ├── core/
│   │   └── config.py           # Environment and logging configuration
│   ├── schemas/                # Pydantic data validation models
│   └── services/
│       ├── base.py             # Abstract base classes
│       ├── sec_service.py      # Dynamic SEC/Global data fetching router
│       └── vector_service.py   # FAISS embedding and retrieval logic
├── main.py                     # FastAPI application entry point
├── celery_worker.py            # Celery worker initialization and task logic
├── run_client.py               # Automated testing script for async polling
├── docker-compose.yml          # Container orchestration blueprint
├── Dockerfile                  # Python environment build instructions
└── requirements.txt            # Dependency manifest

## 🛣️ Roadmap
- [x] Phase 1: Local RAG Pipeline setup (FAISS + HuggingFace).
- [x] Phase 2: LangGraph integration for Analyst -> Auditor flow.
- [x] Phase 3: Live SEC EDGAR integration with rate-limiting.
- [x] Phase 4: Containerization and Asynchronous decoupling (FastAPI + Celery + Redis).
- [x] Phase 5: Dynamic Routing for International Equities (Yahoo Finance).
- [ ] Phase 6: Migration from FAISS to Qdrant for persistent, distributed vector storage.
- [ ] Phase 7: Implement WebSockets (Server-Sent Events) for real-time UI token streaming.