---
description: 'Dependency-aware subagent orchestrator'
---

# SubagentRunner

Execute subagent queries with intelligent parallelization.

## Configuration

```
initialWaitInterval = 30  // seconds (first wait)
subsequentWaitInterval = 15  // seconds (subsequent waits)
```

**Import syntax example**:
```
import { convertDocumentToImage } from "docx-skill.md"
```

## Constraints

* Prefer #runSubagent tool when available
* When #runSubagent NOT available, use lmspace CLI executor
* Analyze query dependencies, parallelize independent queries
* Wait for all queries in a group before reading results
* Auto-provision subagents when unavailable
* Emit errors for failed dispatches, continue processing remaining queries

## Execution Strategies

Choose execution strategy based on tool availability.

### Strategy 1: RunSubagent Tool (Preferred)

Use when #runSubagent tool is available. Pass query with file paths; let subagent read contents.

### Strategy 2: Lmspace CLI Executor (Fallback)

Use when #runSubagent NOT available.

**Dispatch pattern**:
```
lmspace code chat "<primary_instruction_path>" "<query>" -a "<import_path_1>" -a "<import_path_2>" ...
```

**Wait pattern**: Synchronous barrier with configurable intervals

**Read pattern**: Retrieve results from response files

---

# Execution Flow

```
// Inferred functions
fn findRelevantPrompt;
fn extractImportPaths;
fn analyzeQueryDependencies;
fn formatAttachmentFlags;
fn provisionSubagent;
fn dispatchQuery;
fn readResult;

// 1. Resolve primary instruction
primaryInstructionPath = findRelevantPrompt(userContext, "**/*.prompt.md")
  |> default(generateDynamicInstructions(userContext))

// 2. Extract imports
importPaths = extractImportPaths(primaryInstructionPath)

// 3. Determine strategy
strategy = if (#runSubagent available) "runSubagent" else "lmspaceCLI"

// 4. Build query groups
queryGroups = parseQueries(userInput) |> analyzeQueryDependencies

// 5. Execute groups with parallelization
isFirstWait = true
for each group in queryGroups {
  
  // Parallel dispatch
  dispatches = for each query in group {
    match (strategy) {
      case "runSubagent" => 
        runSubagent(query, files=importPaths)
      
      case "lmspaceCLI" =>
        dispatchQuery(primaryInstructionPath, query, importPaths)
          |> onError("No unlocked subagents") => {
            provisionSubagent()
            retry(dispatchQuery)
          }
          |> onError => emit("Error: $error") |> continue
    }
  }
  
  // Wait barrier (CLI only)
  if (strategy == "lmspaceCLI") {
    waitInterval = isFirstWait ? initialWaitInterval : subsequentWaitInterval
    wait(waitInterval)
    isFirstWait = false
  }
  
  // Emit results
  for each dispatch in dispatches {
    result = readResult(dispatch, strategy)
    emit(result)
  }
}
```