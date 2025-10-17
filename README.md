# LMSpace

**LMSpace** is a Python agent framework for enterprise knowledge persistence and Azure LLM synchronization. Inspired by GitHub Copilot Spaces, it provides flexible, contextualized "spaces" for knowledge and code processing, leveraging DSPy for non-opinionated agent pipelines.

## Features

- **Contextual Knowledge Management**: Persist enterprise knowledge (documents, codebases, business rules) in Azure Cosmos DB, Blob Storage, or Table Storage
- **Dynamic Subagents**: Non-opinionated subagents for codebase research (e.g., finding patterns, summarizing modules) in separate context windows
- **Azure LLM Synchronization**: Real-time or batch sync for model inference and fine-tuning
- **Massive Context Support**: Handle codebases with 10M+ tokens via RLM-inspired recursion
- **Enterprise-Ready**: Built-in security, compliance (GDPR/HIPAA), and scalability

## Prerequisites

- Python 3.12 or higher
- Azure subscription with access to:
  - Azure Cosmos DB
  - Azure Blob Storage
  - Azure OpenAI or Azure ML
- `uv` package manager (recommended) or `pip`

## Installation

### Using uv (Recommended)

```bash
# Install uv if you haven't already
pip install uv

# Install lmspace
uv pip install lmspace
```

### Using pip

```bash
pip install lmspace
```

## Quick Start

### 1. Configuration

Create a `lmspace.yaml` configuration file:

```yaml
azure:
  cosmos_endpoint: "https://your-cosmos-account.documents.azure.com:443/"
  cosmos_key: "your-cosmos-key"
  storage_account: "your-storage-account"
  storage_key: "your-storage-key"
  openai_endpoint: "https://your-openai-resource.openai.azure.com/"
  openai_key: "your-openai-key"
  
enterprise:
  id: "your-enterprise-id"
  region: "eastus"
```

> **Note**: For production, use Azure Key Vault or environment variables for sensitive credentials.

### 2. Basic Usage

```python
from lmspace.agents import KnowledgeAgent
from lmspace.config import load_config

# Load configuration
config = load_config('lmspace.yaml')

# Create an agent
agent = KnowledgeAgent(config)

# Ingest knowledge
agent.ingest({
    'content': 'Policy: Data retention period is 7 years',
    'metadata': {'type': 'policy', 'department': 'legal'}
})

# Query knowledge
response = agent.query('What is the data retention policy?')
print(response)

# Research codebase
codebase = {
    'file1.py': 'def foo():\n    print("hello")',
    'file2.py': 'import os\n\nclass MyClass:\n    pass'
}
results = agent.research('Find all print statements', codebase)
print(results)

# Sync to Azure LLM
agent.sync_to_llm()
```

### 3. Using Subagents

```python
from lmspace.agents import SubAgent

# Create a subagent for focused codebase research
subagent = SubAgent(config)

# Process large codebase in isolated context
codebase = load_large_codebase()  # Your function to load code
analysis = subagent.analyze(
    task='Identify security vulnerabilities',
    codebase=codebase
)
```

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/EntityProcess/lmspace.git
cd lmspace
```

### 2. Create Virtual Environment

```bash
# uv automatically uses Python 3.12+ from .python-version
uv venv
```

### 3. Activate Virtual Environment

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
source .venv/bin/activate
```

### 4. Install in Editable Mode

```bash
# Install with development dependencies
uv pip install -e ".[dev]"
```

### 5. Run Tests

```bash
pytest tests/
```

## Use Cases

- **Knowledge Retrieval**: Build enterprise search systems with semantic understanding
- **AI-Driven Chatbots**: Create context-aware assistants with persistent memory
- **Code Analysis**: Automatically analyze codebases for patterns, bugs, or compliance
- **Automated Decision Support**: Leverage enterprise knowledge for intelligent recommendations
- **Document Management**: Organize and query large document collections

## Architecture

LMSpace follows a layered, modular design:

- **Agent Layer**: Core agents (`KnowledgeAgent`, `SubAgent`) built as DSPy modules
- **Persistence Layer**: Azure Cosmos DB for embeddings/metadata, Blob Storage for raw data
- **Sync Layer**: Bidirectional synchronization with Azure LLMs
- **Integration Layer**: APIs for external tools (e.g., Azure Functions)
- **Security Layer**: Authentication, encryption, and compliance

## Documentation

For detailed technical information, see:
- [Technical Design Document](docs/technical-design.md)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

## Roadmap

- [ ] Multi-LLM support (Hugging Face models)
- [ ] UI dashboard (Streamlit) for knowledge management
- [ ] Multi-agent collaboration patterns
- [ ] Full RLM integration for massive contexts (>10M tokens)

## Support

For issues and questions, please open an issue on the GitHub repository.

---

**Note**: This project is currently in MVP development. Features and APIs may change as development progresses.
