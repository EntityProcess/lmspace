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

* **NEVER read import file contents in main agent context** - pass paths only
* Prefer #runSubagent tool when available
* When #runSubagent NOT available, use lmspace CLI executor
* Analyze query dependencies, parallelize independent queries
* Wait for all queries in a group before reading results
* Auto-provision subagents when unavailable
* Emit errors for failed dispatches, continue processing remaining queries

## Execution Strategies

Choose execution strategy based on tool availability.

### Strategy 1: RunSubagent Tool (Preferred)

Use when #runSubagent tool is available.

**CRITICAL**: Pass file PATHS only (do NOT read file contents). The subagent will read files internally.

**What to pass**: Array of absolute path strings (e.g., `["/path/to/skill.md"]`)
**What NOT to do**: Read files, pass file contents, or attach file contents

Example: `runSubagent(query, files=importPaths)` where `importPaths = ["/path/to/skill.md", "/path/to/context.md"]`

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
fn provisionSubagent;
fn dispatchQuery;
fn readResult;

// Resolve instruction & imports (paths only, do NOT read contents)
primaryInstructionPath = findRelevantPrompt(userContext, "**/*.prompt.md")
  |> default(generateDynamicInstructions(userContext))
importPaths = extractImportPaths(primaryInstructionPath)  // Returns array of file paths as strings

// Determine strategy & build query groups
strategy = if (#runSubagent available) "runSubagent" else "lmspaceCLI"
queryGroups = parseQueries(userInput) |> analyzeQueryDependencies

// Execute groups with parallelization
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