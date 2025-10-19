# Technical Design Document: LMSpace Framework

## 1. Document Metadata
- **Title**: LMSpace: Azure-Aligned Agent Framework for Enterprise Knowledge Persistence and LLM Synchronization
- **Version**: 1.1
- **Date**: October 17, 2025
- **Purpose**: This document outlines the technical design for **LMSpace**, a Python-based solution (PyPI package: `lmspace`) that persists enterprise knowledge in Azure, synchronizes with Azure Large Language Models (LLMs), and supports dynamic subagents for codebase research. LMSpace is implemented on top of the **Microsoft Agent Framework**, leveraging its next-generation agent and workflow capabilities.

## 2. Overview
### 2.1 Project Description
**LMSpace** is an open-source Python system for building intelligent agents that manage enterprise knowledge (documents, codebases, business rules) and synchronize with Azure LLMs (Azure OpenAI, Azure ML models). Key features include:
- **Contextual Knowledge Management**: Persists knowledge (embeddings, metadata, documents) in Azure Cosmos DB, Blob Storage, or Table Storage, creating a "space" for enterprise data similar to Copilot Spaces.
- **Dynamic Subagents**: Uses Microsoft Agent Framework workflows to spin up specialized agents for codebase research (pattern mining, module summarization) in isolated context windows.
- **Azure LLM Synchronization**: Enables real-time or batch sync for model inference and fine-tuning to keep agents aligned with the latest model capabilities.
- **Enterprise Use Cases**: Knowledge retrieval, AI-driven chatbots, code analysis, automated decision support, and compliance automation.

The Microsoft Agent Framework—successor to Semantic Kernel and AutoGen—provides typed agents, graph-based workflows, observability, and native Azure integrations, reducing custom orchestration work.

### 2.2 Goals
- Provide a Pythonic API backed by Microsoft Agent Framework agents and workflows for knowledge persistence and LLM synchronization.
- Enable dynamic subagents for codebase research with isolated context windows via workflow routing, hand-offs, and checkpointing.
- Ensure secure, scalable integration with Azure services and enterprise-grade observability.
- Support massive contexts (10M+ tokens) through workflow-based fan-out, recursion, and streaming.
- Distribute as a PyPI package (`lmspace`) with a clean developer experience built around `uv`.

### 2.3 Assumptions and Dependencies
- Python 3.12+ (managed via `.python-version`).
- `uv` for modern Python package and environment management.
- Azure SDKs: `azure-identity`, `azure-cosmos`, `azure-storage-blob`, `azure-ai-ml`.
- Microsoft `agent-framework` package (public preview) for agents, workflows, context providers, and telemetry.
- Optional: `sentence-transformers` for embeddings, `langchain-azure` for advanced chaining.
- Access to Azure subscription with Cosmos DB, Blob Storage, Azure OpenAI/ML.

## 3. Architecture
### 3.1 High-Level Architecture
**LMSpace** follows a layered, modular design inspired by contextual workspaces like Copilot Spaces, with Microsoft Agent Framework primitives at its core:
- **Agent Layer**: Core agents (`KnowledgeAgent`, `ResearchAgent`, optional domain-specific agents) implemented with Agent Framework agent threads and context providers.
- **Workflow Layer**: Graph workflows orchestrate subagents, deterministic executors, and tool calls (MCP servers, Python functions) for complex tasks such as large-scale code analysis.
- **Persistence Layer**: Azure storage (Cosmos DB for embeddings/metadata, Blob Storage for raw content) with pointers referenced from agent context providers.
- **Sync Layer**: Bidirectional synchronization with Azure LLMs (fine-tuning datasets, model updates, evaluation results).
- **Integration Layer**: External APIs or Azure Functions that trigger workflows and supply knowledge payloads.
- **Security Layer**: Entra ID, Managed Identity, RBAC, and auditing support across all layers.

**Data Flow**:
1. User submits knowledge (documents, codebase snapshots) via `KnowledgeAgent` endpoints.
2. Agent threads embed and persist data in Azure storage while updating context providers and workflow checkpoints.
3. Workflows branch into research agents or deterministic executors operating in isolated contexts.
4. Sync operations update Azure LLMs or pull down model deltas and evaluation results.
5. Queries leverage persisted knowledge, workflow outputs, and synchronized LLMs to craft responses.

### 3.2 System Components
#### 3.2.1 Core Components
- **KnowledgeAgent (Agent Framework Agent)**:
  - Handles ingestion, querying, research dispatch, and LLM synchronization.
  - Methods (invoked through agent actions or workflow triggers): `ingest(data)`, `query(question)`, `dispatch_research(task, codebase)`, `sync_to_llm()`.
  - Uses Agent Framework context providers for long-lived memory and middleware for policy enforcement, throttling, and logging.
- **ResearchAgent (Agent Framework Agent)**:
  - Specialized agent for codebase research tasks (pattern detection, summarization, dependency mapping).
  - Runs within workflow-managed contexts, processes chunked payloads, and streams intermediate results.
  - Supports fan-out, recursion, and parallel execution via workflow edges and concurrent executors.
- **Workflow Orchestrator**:
  - Agent Framework workflow graph connecting agents, deterministic Python executors, and Azure services.
  - Provides checkpointing, state recovery, and human-in-the-loop decision points when required.
- **PersistenceManager**:
  - Interfaces with Cosmos DB (structured knowledge, embeddings), Blob Storage (raw files), and optionally Table Storage (lightweight metadata).
  - Methods: `persist_knowledge(data) -> ID`, `query_knowledge(embedding) -> List[Dict]`, `record_workflow_checkpoint(state)`.
- **SyncManager**:
  - Exposed as workflow executors reusable by agents.
  - Batch sync: Exports knowledge as datasets to Azure ML for fine-tuning and evaluation.
  - Real-time sync: Uses Azure Event Grid/Service Bus to trigger incremental updates.
- **ConfigManager**:
  - Loads Azure credentials and configs from `lmspace.yaml` or environment variables and hydrates Agent Framework dependency injection containers.

#### 3.2.2 Extensibility
- **Custom Agents**: Inherit from Agent Framework base classes for domain-specific logic (e.g., `PolicyAgent`) while reusing shared middleware and context providers.
- **Plugins**: Hook-based system for extending storage backends, workflow executors, or LLM integrations (`@plugin.register`).
- **Tooling Integration**: Support MCP servers and Python tools registered via Agent Framework middleware for telemetry, guardrails, and tool scheduling.

### 3.3 Data Model
- **Knowledge Entity**: JSON-serializable dict with `id`, `content`, `embeddings` (vector array), `metadata` (tags, timestamps, sensitivity labels), and storage pointers.
- **Codebase Entity**: Dict or paginated list of `{path: content}` stored in Blob Storage; workflow metadata tracks processing progress and checkpoints.
- **Sync Payload**: List of knowledge entities formatted for Azure ML datasets (e.g., `[{"prompt": str, "completion": str}]`) plus evaluation metadata.
- **Storage Schema**:
  - Cosmos DB: Partitioned by `enterprise_id` with vector indexes for semantic search.
  - Blob Storage: Hierarchical containers (e.g., `/enterprise/docs/year/`, `/enterprise/code/repo/`).
  - Table Storage (optional): Lightweight lookup tables for workflow state or audit trails.

## 4. Implementation Details
### 4.1 Technology Stack
- **Language**: Python 3.12+.
- **Package Manager**: `uv` for fast dependency management.
- **Dependencies** (in `pyproject.toml`):
  - `agent-framework==0.1.0b*` (preview) for agents, workflows, telemetry.
  - `azure-identity==1.25.1`
  - `azure-cosmos==4.14.0`
  - `azure-storage-blob==12.27.0`
  - `azure-ai-ml==1.29.0`
  - `opentelemetry-sdk==1.25.0`
  - `sentence-transformers==5.1.1` (for embeddings)
  - Optional: `langchain-azure==0.1.0`
- **Testing**: Pytest for unit/integration tests; use Agent Framework test utilities and mock Azure services for CI.

### 4.2 Key Algorithms and Flows
- **Ingestion Flow**:
  1. Validate input data (document or codebase payload).
  2. Generate embeddings via `sentence-transformers` or Azure OpenAI Embeddings.
  3. Persist structured data to Cosmos DB and raw files to Blob Storage.
  4. Update agent thread context providers and emit workflow checkpoint events.
- **Query Flow**:
  1. Embed query using `sentence-transformers`.
  2. Execute vector search in Cosmos DB (Azure vector index).
  3. Augment retrieved context with Azure OpenAI Responses client executed through Agent Framework.
  4. Return response with OpenTelemetry traces for observability.
- **Codebase Research Flow**:
  1. Workflow invokes `ResearchAgent` with task metadata and chunked codebase payloads.
  2. Agent applies built-in deliberation middleware, calling deterministic tools or MCP servers as needed.
  3. Workflows fan out across chunks, checkpoint results, and support retries on failure.
  4. Aggregated results stream back to `KnowledgeAgent` for summarization and storage.
- **Sync Flow**:
  1. Extract knowledge deltas (new/updated entities) from Change Feed or workflow metadata.
  2. Format as Azure ML dataset artifacts.
  3. Upload via Azure ML SDK, trigger fine-tuning/evaluation job, and persist run IDs.
  4. Poll via workflow executor, update agent configs, and notify stakeholders.

### 4.3 Agent Framework Integration
- **Why Microsoft Agent Framework**: Provides the unified successor to Semantic Kernel and AutoGen with typed messaging, workflow orchestration, OpenTelemetry integration, tool/MCP support, and Azure-first alignment. Public preview status is acceptable for the MVP, with mitigations documented in Risks.
- **Key Components**:
  - `KnowledgeAgent`: Agent with thread-based state, context providers, and middleware for auth/policy enforcement.
  - `ResearchAgent`: Specialized agent registered within workflows for large codebase tasks and streaming outputs.
  - Workflows: Graph definitions connecting agents, deterministic executors, Azure ML sync operations, and optional human approval nodes.
- **Observability**: Built-in OpenTelemetry exporters feed Azure Monitor/Application Insights dashboards for tracing and metrics.

### 4.4 Error Handling and Resilience
- Retry logic for Azure and Agent Framework operations using `tenacity` and workflow retry policies.
- Logging with `logging`, Agent Framework telemetry hooks, and Azure Monitor integration.
- Fallbacks: Local cache (SQLite) when Azure services are unavailable, with workflow checkpoint recovery once services resume.

## 5. Security and Compliance
- **Authentication**: Azure Managed Identity or Entra ID for service-to-service auth; support for delegated tokens via Agent Framework middleware.
- **Data Encryption**: Azure-managed encryption at rest/transit plus optional client-side encryption for high-sensitivity data.
- **Access Control**: RBAC on Azure resources and fine-grained permissions enforced via agent middleware.
- **Compliance**: Supports GDPR/HIPAA with audit logs, retention policies, and Azure region data residency.
- **Secrets Management**: Azure Key Vault for API keys, connection strings, and Agent Framework configuration secrets.

## 6. Performance and Scalability
- **Scalability**: Cosmos DB auto-scales throughput; workflows can run in Azure Functions or Azure Container Apps with horizontal scaling.
- **Performance Targets**: <1s for queries on <10k knowledge items; batch sync <5min for 1k items.
- **Massive Contexts**: Workflows support fan-out, chunking, and recursion to handle codebases >10M tokens, leveraging streaming responses.
- **Monitoring**: Azure Application Insights dashboards for latency, error rates, cost metrics, and workflow health.

## 7. Deployment and Operations
### 7.1 Deployment
- **PyPI Packaging**: Use `uv` and `pyproject.toml` for `lmspace` package.
- **CI/CD**: GitHub Actions or Azure DevOps to lint, test, validate workflows, and publish to PyPI.
- **Repo Structure**:
  ```
  lmspace/
  ├── lmspace/
  │   ├── agent_app.py
  │   ├── workflows.py
  │   ├── persistence.py
  │   ├── sync.py
  │   └── config.py
  ├── tests/
  ├── .python-version
  ├── pyproject.toml
  └── lmspace.yaml (example config)
  ```
- **Installation**: `pip install lmspace` or `uv pip install lmspace`

### 7.2 Operations
- **Configuration**: `lmspace.yaml` with Azure resource IDs (`cosmos_endpoint`, `blob_account`, `openai_key`, `ml_workspace`).
- **Development Setup**:
  1. **Create a virtual environment:**
     ```bash
     # Create the virtual environment (automatically uses Python 3.12+ from .python-version)
     uv venv
     ```
  2. **Activate the virtual environment:**
     ```bash
     # On Linux/macOS
     source .venv/bin/activate

     # On Windows (PowerShell)
     .venv\Scripts\Activate.ps1
     ```
  3. **Perform an editable install with development dependencies:**

     Note: With `uv`, you don't need to activate the virtual environment for `uv` commands, but activation is required to run installed tools directly.

     ```bash
     # Install in editable mode with development dependencies
     uv pip install -e ".[dev]"
     ```
- **Example Usage**:
  ```python
  from agent_framework.agents import Agent
  from agent_framework.clients.openai import AzureOpenAIResponsesClient
  from lmspace.agent_app import create_knowledge_agent
  from lmspace.config import load_config

  config = load_config('lmspace.yaml')
  responses_client = AzureOpenAIResponsesClient.from_env()
  agent: Agent = create_knowledge_agent(config, responses_client)
  # Ingest knowledge
  agent.run("ingest", {"content": "Policy: Data retention 7 years", "metadata": {"type": "policy"}})
  # Query knowledge
  print(agent.run("query", {"question": "What is the data retention policy?"}))
  # Research codebase via workflow hand-off
  codebase = {'file1.py': 'def foo(): print("hello")', 'file2.py': 'import os'}
  print(agent.run("research", {"task": "Find print statements", "codebase": codebase}))
  # Sync to LLM (triggers workflow executor)
  agent.run("sync_to_llm", {})
  ```

## 8. Risks and Mitigations
- **Risk**: Azure service outages → **Mitigation**: Local cache, workflow retries, and checkpoint recovery.
- **Risk**: Data privacy breaches → **Mitigation**: Encryption, RBAC, Key Vault, and middleware-based policy enforcement.
- **Risk**: Sync latency → **Mitigation**: Asynchronous queues (Service Bus), partial dataset updates, workflow timeouts.
- **Risk**: High costs → **Mitigation**: Azure Cost Management dashboards, workload autoscaling, workload throttling in middleware.
- **Risk**: Agent Framework preview instability → **Mitigation**: Pin prerelease versions, run regression tests against nightly builds, isolate risky features behind toggles.

## 9. Future Enhancements
- Multi-LLM support (e.g., Hugging Face models) via additional agent providers.
- UI dashboard (e.g., Streamlit) for knowledge space management and workflow monitoring.
- Multi-agent collaboration templates (e.g., CrewAI-style patterns) using reusable workflow blueprints.
- Deep VS Code / MCP integrations for developer tooling.
- Automatic evaluation workflows to benchmark knowledge freshness and LLM alignment.