# Technical Design Document: LMSpace Framework

## 1. Document Metadata
- **Title**: LMSpace: Python Agent Framework for Enterprise Knowledge Persistence and Azure LLM Synchronization
- **Version**: 1.0
- **Date**: October 17, 2025
- **Purpose**: This document outlines the technical design for **LMSpace**, a Python-based agent framework (PyPI package: `lmspace`) that persists enterprise knowledge in Azure, synchronizes with Azure Large Language Models (LLMs), and supports dynamic subagents for codebase research. Inspired by GitHub Copilot Spaces, it emphasizes flexible, contextualized "spaces" for knowledge and code processing, leveraging DSPy for non-opinionated agent pipelines.

## 2. Overview
### 2.1 Project Description
**LMSpace** is an open-source Python framework for building intelligent agents that manage enterprise knowledge (e.g., documents, codebases, business rules) and synchronize with Azure LLMs (e.g., Azure OpenAI, Azure ML models). Key features include:
- **Contextual Knowledge Management**: Persists knowledge (e.g., embeddings, metadata) in Azure Cosmos DB, Blob Storage, or Table Storage, creating a "space" for enterprise data, akin to Copilot Spaces.
- **Dynamic Subagents**: Supports non-opinionated subagents for codebase research (e.g., finding patterns, summarizing modules) in separate context windows, aligning with your MVP requirements.
- **Azure LLM Synchronization**: Enables real-time or batch sync for model inference and fine-tuning, ensuring agents leverage up-to-date LLMs.
- **Enterprise Use Cases**: Knowledge retrieval, AI-driven chatbots, code analysis, automated decision support.

The framework uses **DSPy** for programmable, optimized agent pipelines, enabling dynamic task handling without predefined workflows, unlike opinionated systems like Claude Code.

### 2.2 Goals
- Provide a Pythonic API for agent creation, knowledge persistence, and LLM synchronization.
- Enable dynamic subagents for codebase research with isolated context windows.
- Ensure secure, scalable integration with Azure services.
- Support massive contexts (e.g., 10M+ tokens) via RLM-inspired recursion or chunking.
- Distribute as a PyPI package (`lmspace`).

### 2.3 Assumptions and Dependencies
- Python 3.12+ (managed via `.python-version` file).
- `uv` for fast, modern Python package and environment management.
- Azure SDKs: `azure-identity`, `azure-cosmos`, `azure-storage-blob`, `azure-ai-ml`.
- DSPy for agent orchestration and optimization.
- Optional: `sentence-transformers` for embeddings, `langchain-azure` for advanced LLM chaining.
- Access to Azure subscription with Cosmos DB, Blob Storage, and Azure OpenAI/ML.

## 3. Architecture
### 3.1 High-Level Architecture
**LMSpace** follows a layered, modular design, inspired by contextual workspaces like Copilot Spaces:
- **Agent Layer**: Core agents (`KnowledgeAgent`, `SubAgent`) for task orchestration, built as DSPy modules.
- **Persistence Layer**: Stores knowledge in Azure (Cosmos DB for embeddings/metadata, Blob Storage for raw data).
- **Sync Layer**: Manages bidirectional synchronization with Azure LLMs (e.g., fine-tuning datasets, model updates).
- **Integration Layer**: APIs for external tools (e.g., Azure Functions for event-driven tasks).
- **Security Layer**: Ensures authentication, encryption, and compliance.

**Data Flow**:
1. User inputs knowledge (e.g., documents, codebase) via `KnowledgeAgent`.
2. Agent embeds and persists data in Azure, creating a contextual "space" for enterprise knowledge.
3. Subagents handle tasks like codebase research in isolated contexts, using DSPy for dynamic processing.
4. Sync mechanisms update Azure LLMs or pull model updates to agents.
5. Queries leverage persisted knowledge and synced LLMs for responses.

### 3.2 System Components
#### 3.2.1 Core Components
- **KnowledgeAgent (DSPy Module)**:
  - Handles tasks: ingestion, querying, codebase research, LLM synchronization.
  - Methods: `ingest(data)`, `query(question)`, `research(task, codebase)`, `sync_to_llm()`.
  - Uses DSPy’s `ChainOfThought` for dynamic reasoning and task adaptation.
- **SubAgent (DSPy Module)**:
  - Dynamic subagent for codebase research (e.g., finding `print` statements, summarizing modules).
  - Operates in a separate context window, processing codebase subsets without bloating the main agent’s context.
  - Supports RLM-inspired recursion for massive codebases (e.g., 10M+ tokens).
- **PersistenceManager**:
  - Interfaces with Azure Cosmos DB (structured knowledge, embeddings), Blob Storage (raw files), and Table Storage (metadata).
  - Methods: `persist_knowledge(data) -> ID`, `query_knowledge(embedding) -> List[Dict]`.
- **SyncManager**:
  - Manages synchronization with Azure LLMs.
  - Batch sync: Exports knowledge as datasets to Azure ML for fine-tuning.
  - Real-time sync: Uses Azure Event Grid for model update triggers.
  - Methods: `sync_to_llm(dataset)`, `pull_llm_updates(model_id)`.
- **ConfigManager**:
  - Loads Azure credentials and configs from `lmspace.yaml` or environment variables.

#### 3.2.2 Extensibility
- **Custom Agents**: Inherit from `BaseAgent` (DSPy module) for domain-specific logic (e.g., `PolicyAgent` for compliance tasks).
- **Plugins**: Hook-based system for adding storage backends or LLM integrations (e.g., `@plugin.register`).

### 3.3 Data Model
- **Knowledge Entity**: JSON-serializable dict with `id`, `content`, `embeddings` (vector array), `metadata` (e.g., tags, timestamps).
- **Codebase Entity**: Dict of `{path: content}` for code files, stored in Blob Storage or as context in Cosmos DB.
- **Sync Payload**: List of knowledge entities formatted for Azure ML datasets (e.g., `[{"prompt": str, "completion": str}]`).
- **Storage Schema**:
  - Cosmos DB: Partitioned by `enterprise_id` for multi-tenant support.
  - Blob Storage: Hierarchical folders (e.g., `/enterprise/docs/year/` or `/enterprise/code/repo/`).

## 4. Implementation Details
### 4.1 Technology Stack
- **Language**: Python 3.12+.
- **Package Manager**: `uv` for fast dependency management.
- **Dependencies** (in `pyproject.toml`):
  - `dspy-ai==3.0.3` (for agent orchestration)
  - `azure-identity==1.25.1`
  - `azure-cosmos==4.14.0`
  - `azure-storage-blob==12.27.0`
  - `azure-ai-ml==1.29.0`
  - `sentence-transformers==5.1.1` (for embeddings)
  - Optional: `langchain-azure==0.1.0`
- **Testing**: Pytest for unit/integration tests; mock Azure services for CI.

### 4.2 Key Algorithms and Flows
- **Ingestion Flow**:
  1. Validate input data (document or codebase).
  2. Generate embeddings using `sentence-transformers` or Azure OpenAI Embeddings.
  3. Persist to Cosmos DB (structured data) and Blob Storage (raw files).
  4. Trigger optional sync to LLM.
- **Query Flow**:
  1. Embed query using `sentence-transformers`.
  2. Vector search in Cosmos DB (using Azure’s vector index).
  3. Augment with Azure OpenAI inference via DSPy.
  4. Return response.
- **Codebase Research Flow**:
  1. Subagent receives task (e.g., “find print statements”) and codebase (`{path: content}`).
  2. Uses DSPy’s `ChainOfThought` to generate reasoning and strategy (e.g., regex, iteration).
  3. Processes subsets (e.g., one file) in a separate context window, with optional recursion for large codebases.
  4. Returns results to main agent.
- **Sync Flow**:
  1. Extract knowledge deltas (new/updated entities).
  2. Format as Azure ML dataset.
  3. Upload via Azure ML SDK and trigger fine-tuning job.
  4. Poll for job completion and update agent configs.

### 4.3 DSPy Integration
- **Why DSPy**: Enables dynamic, non-opinionated subagents that adapt to tasks (e.g., codebase research) without predefined roles, unlike Claude Code. Supports separate context windows and optimizes performance via `BootstrapFewShot`.
- **Key Components**:
  - `KnowledgeAgent`: DSPy module with `KnowledgeSignature` for tasks (ingest, query, research, sync).
  - `SubAgent`: DSPy module for codebase research, using isolated contexts and optional recursion (RLM-inspired for massive codebases).
  - Optimization: Fine-tune prompts with enterprise-specific examples (e.g., codebase queries).

### 4.4 Error Handling and Resilience
- Retry logic for Azure API calls (using `tenacity`).
- Logging with `logging` and Azure Monitor integration.
- Fallbacks: Local cache (e.g., SQLite) if Azure services are unavailable.

## 5. Security and Compliance
- **Authentication**: Azure Managed Identity or Entra ID for service-to-service auth.
- **Data Encryption**: Azure-managed encryption at rest/transit.
- **Access Control**: Role-Based Access Control (RBAC) for Azure resources.
- **Compliance**: Supports GDPR/HIPAA with audit logs and Azure region data residency.
- **Secrets Management**: Azure Key Vault for API keys.

## 6. Performance and Scalability
- **Scalability**: Cosmos DB auto-scales throughput; agents run in Azure Functions for serverless execution.
- **Performance Targets**: <1s for queries on <10k knowledge items; batch sync <5min for 1k items.
- **Massive Contexts**: Subagent uses DSPy recursion (RLM-inspired) for codebases >1M tokens, supporting up to 10M+ tokens (per RLM benchmarks).
- **Monitoring**: Azure Application Insights for metrics (e.g., query latency, sync errors).

## 7. Deployment and Operations
### 7.1 Deployment
- **PyPI Packaging**: Use `uv` and `pyproject.toml` for `lmspace` package.
- **CI/CD**: GitHub Actions or Azure DevOps to build, test, and publish to PyPI.
- **Repo Structure**:
  ```
  lmspace/
  ├── lmspace/
  │   ├── agents.py
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
- **Configuration**: `lmspace.yaml` with Azure resource IDs (e.g., `cosmos_endpoint`, `openai_key`).
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
     
     Note: With `uv`, you don't need to manually activate the virtual environment for `uv` commands. However, activation is required to run the installed tools or Python scripts directly.
     
     ```bash
     # Install in editable mode with development dependencies
     uv pip install -e ".[dev]"
     ```
- **Example Usage**:
  ```python
  from lmspace.agents import KnowledgeAgent
  from lmspace.config import load_config

  config = load_config('lmspace.yaml')
  agent = KnowledgeAgent(config)
  # Ingest knowledge
  agent.ingest({'content': 'Policy: Data retention 7 years', 'metadata': {'type': 'policy'}})
  # Query knowledge
  print(agent.query('What is the data retention policy?'))
  # Research codebase
  codebase = {'file1.py': 'def foo(): print("hello")', 'file2.py': 'import os'}
  print(agent.research('Find print statements', codebase))
  # Sync to LLM
  agent.sync_to_llm()
  ```

## 8. Risks and Mitigations
- **Risk**: Azure service outages → Mitigation: Local cache, retries.
- **Risk**: Data privacy breaches → Mitigation: Encryption, RBAC.
- **Risk**: Sync latency → Mitigation: Asynchronous queues (Azure Service Bus).
- **Risk**: High costs → Mitigation: Azure Cost Management monitoring.

## 9. Future Enhancements
- Multi-LLM support (e.g., Hugging Face models).
- UI dashboard (e.g., Streamlit) for knowledge management.
- Multi-agent collaboration (e.g., CrewAI-inspired patterns).
- Full RLM integration with REPL for massive contexts (>10M tokens).