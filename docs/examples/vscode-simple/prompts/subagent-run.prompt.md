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

---

# Execution Strategies

Choose execution strategy based on tool availability.

## Strategy 1: RunSubagent Tool (Preferred)

**When to use**: #runSubagent tool is available in your toolkit

**What to pass to subagent**:
1. Primary instruction
2. Import file paths
4. DO NOT read file contents yourself

---

## Strategy 2: Lmspace CLI Executor (Fallback)

**When to use**: #runSubagent tool is NOT available

**How to execute each query**:

1. **Dispatch** - Run in background terminal:
   ```
   lmspace code chat "<primary_instruction_path>" "<query>" -a "<import_path_1>" -a "<import_path_2>" ...
   ```
   * Set isBackground=true
   * Add `-a` flag for each import file path
   * Capture JSON response with `response_file` field

2. **Wait** - After dispatching ALL queries in group, run synchronous barrier:
   ```
   Start-Sleep -Seconds {isFirstWait ? initialWaitInterval : subsequentWaitInterval}
   ```
   * isBackground=false (blocks until complete)
   * Use initialWaitInterval for first wait, subsequentWaitInterval after
   * DO NOT poll terminals repeatedly

3. **Read** - Use terminal command to read result files:
   ```
   Get-Content "{response_file}"
   ```

---

# Execution Flow

```
// 1. Identify primary instruction path (not the content, just the path)
// Search for files ending in .prompt.md or .instructions.md
primaryInstructionPath = findFiles("**/*.prompt.md")
  |> selectRelevantPrompt(userContext)

// If no relevant prompt found, dynamically generate instructions
if (primaryInstructionPath == null) {
  primaryInstructionPath = generateDynamicInstructions(userContext)
}

// 2. Extract import paths only
importPaths = extractImportPaths(primaryInstructionPath)
// Only include paths from import statements, not attachments

// 3. Choose strategy (do NOT execute yet, just choose)
if (#runSubagent available) {
  strategy = "runSubagent"
} else {
  strategy = "lmspaceCLI"
}

// 4. Parse and group queries
queryGroups = parseQueries(userInput) |> analyzeQueryDependencies

// 5. Execute each group
isFirstWait = true
for each group in queryGroups {
  
  // Dispatch all queries in parallel
  dispatches = for each query in group {
    // Build file paths list (imports only, primary instruction is first positional arg)
    allFilePaths = [...importPaths]
    
    if (strategy == "runSubagent") {
      // Pass query and let subagent read files
      call runSubagent(query, files=allFilePaths)
    } else {
      // Build CLI command with -a flags for each import
      attachmentFlags = allFilePaths.map(path => `-a "${path}"`).join(" ")
      dispatch = run(`lmspace code chat "${primaryInstructionPath}" "${query}" ${attachmentFlags}`, isBackground=true)
      
      // Check if dispatch failed due to no subagents
      if (dispatch.exitCode != 0 && dispatch.output.contains("No unlocked subagents available")) {
        // Provision a new subagent
        run(`lmspace code provision --subagents 1`, isBackground=false)
        // Retry dispatch
        dispatch = run(`lmspace code chat "${primaryInstructionPath}" "${query}" ${attachmentFlags}`, isBackground=true)
      }
      
      // If still failed, report error and stop
      if (dispatch.exitCode != 0) {
        emit("Error: Subagent dispatch failed - " + dispatch.output)
        continue
      }
      
      dispatch |> extract(response_file)
    }
  }
  
  // Wait for completion (only for lmspaceCLI strategy)
  if (strategy == "lmspaceCLI") {
    currentWait = isFirstWait ? initialWaitInterval : subsequentWaitInterval
    run(`Start-Sleep -Seconds ${currentWait}`, isBackground=false)
    isFirstWait = false
  }
  
  // Read and emit results
  for each dispatch in dispatches {
    if (strategy == "runSubagent") {
      emit(dispatch.result)
    } else {
      result = run(`Get-Content "${dispatch.responseFile}"`)
      emit(result)
    }
  }
}
```