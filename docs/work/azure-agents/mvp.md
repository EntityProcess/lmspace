# MVP Implementation Plan for YAML-Configured Custom GPTs

## Overview
Build a Python runner using Microsoft Agent Framework to create custom GPT-like agents from YAML configs in the "lmspace" GitHub repo. Each YAML defines an agent's name, instructions, and URLs to files for its Azure OpenAI-backed knowledge base (KB). The runner parses YAMLs, fetches file content, uploads to Azure OpenAI for retrieval, and creates agents.

**Assumptions**:
- Python-based runner, Azure OpenAI with Assistants API (v2, file_search).
- Public lmspace repo or GitHub token for private access.
- Files are text-based or extractable (e.g., PDFs via PyPDF2).
- KB persistence via Azure OpenAI file uploads.

## YAML Example
```yaml
name: MyCustomGPT
instructions: Expert on [topic]. Use provided knowledge to answer accurately.
urls:
  - https://example.com/file1.pdf
  - https://example.com/file2.txt
```

## Implementation Plan

### 1. Setup (1 day)
- **Install**: `pip install agent-framework --pre requests pygithub openai azure-identity pypdf2`.
- **Azure**: Set up Azure OpenAI, deploy gpt-4o-mini, use `az login`, set env vars (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT_NAME`, `AZURE_OPENAI_API_VERSION`).
- **GitHub**: Use PyGitHub with `GITHUB_TOKEN` for lmspace access.

### 2. Runner Script (2 days)
```python
import os, yaml, requests, asyncio
from github import Github
from azure.identity import AzureCliCredential
from agent_framework.azure import AzureOpenAIResponsesClient
from openai import AzureOpenAI

def get_yaml_files(repo_name='lmspace', token=None):
    g = Github(token)
    repo = g.get_repo(f"{owner}/{repo_name}")  # Replace owner.
    return [yaml.safe_load(requests.get(f.download_url).text) for f in repo.get_contents("") if f.name.endswith('.yaml')]

def fetch_files(urls):
    files = []
    for url in urls:
        file_name = url.split('/')[-1]
        with open(file_name, 'wb') as f:
            f.write(requests.get(url).content)
        files.append(file_name)
    return files

async def create_custom_gpt(config):
    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_ad_token_provider=AzureCliCredential()
    )
    # Upload files
    file_ids = [client.files.create(file=open(f, "rb"), purpose="assistants").id for f in fetch_files(config['urls'])]
    # Create vector store
    vector_store = client.beta.vector_stores.create(name=f"{config['name']}_kb")
    client.beta.vector_stores.files.batch_upload(vector_store_id=vector_store.id, file_ids=file_ids)
    # Create assistant
    assistant = client.beta.assistants.create(
        name=config['name'],
        instructions=config['instructions'],
        model=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
    )
    # Framework agent
    agent = AzureOpenAIResponsesClient(credential=AzureCliCredential()).create_agent(
        name=config['name'], instructions=config['instructions']
    )
    print(f"Created agent {config['name']} with ID {assistant.id}")
    return agent

async def main():
    for config in get_yaml_files():
        await create_custom_gpt(config)

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Knowledge Base Integration (1 day)
- Use Azure OpenAI file_search for KB retrieval.
- If framework lacks direct file support, add custom retrieval tool querying assistant thread.

### 4. Testing (0.5 day)
- Unit tests: Mock YAML parsing, file fetching, uploads.
- E2E: Test 2-3 YAMLs, query agents with KB-based questions.
- Edge cases: Handle invalid URLs, large files (Azure limit: 512 MB).

### 5. Next Steps (0.5 day)
- Add error handling, logging.
- Explore framework's declarative YAML support.
- Plan for .NET support, agent hosting.

## Risks
- Azure file upload limits: Monitor quotas, handle errors.
- Framework gaps: Use custom RAG with FAISS if needed.
- Security: Validate URLs, secure repo access.

**Timeline**: ~5 days for MVP.