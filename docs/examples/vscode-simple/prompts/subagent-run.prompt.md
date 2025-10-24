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

## Constraints

* **Read ONLY the primary instruction file** to extract import paths - the subagent will read all files internally
* **NEVER read imported files** (context.md, skill.md, etc.) - only collect their paths
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
import { resolveAllImports } from #file:import-parser.prompt.md

// Inferred functions
fn findRelevantPrompt;
fn analyzeQueryDependencies;
fn provisionSubagent;
fn dispatchQuery;
fn readResult;

// Find primary instruction file
primaryInstructionPath = findRelevantPrompt(userContext, "**/*.prompt.md")
  |> default(generateDynamicInstructions(userContext))

// Extract import paths from primary instruction (read ONLY this file to parse imports)
// DO NOT read the imported files themselves - only collect their paths
importPaths = resolveAllImports(primaryInstructionPath)

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
      
      case "lmspaceCLI" => {
        // Build lmspace command with ALL import paths as -a arguments
        command = buildLmspaceCommand(primaryInstructionPath, query, importPaths)
        dispatchQuery(command)
          |> onError("No unlocked subagents") => {
            provisionSubagent()
            retry(dispatchQuery(command))
          }
          |> onError => emit("Error: $error") |> continue
      }
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

// Helper function to build lmspace command with all imports
buildLmspaceCommand(instructionPath, query, importPaths) {
  baseCommand = "lmspace code chat \"$instructionPath\" \"$query\""
  attachmentArgs = for each path in importPaths {
    "-a \"$path\""
  } |> join(" ")
  
  return "$baseCommand $attachmentArgs"
}
```
