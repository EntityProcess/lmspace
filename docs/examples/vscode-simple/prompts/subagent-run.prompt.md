---
description: 'Dependency-aware subagent orchestrator'
---

# SubagentRunner

Execute subagent queries with intelligent parallelization.

## Configuration

```
agentName = "${AGENT_NAME}"
waitInterval = 30  // seconds
```

## Constraints

* Prefer #runSubagent tool when available
* When #runSubagent NOT available, use lmspace CLI executor
* Locate agent directory via fileSearch(`**/agents/${agentName}`)
* Analyze query dependencies, parallelize independent queries
* Wait for all queries in a group before reading results

---

# Execution Strategies

Choose execution strategy based on tool availability.

## Strategy 1: RunSubagent Tool (Preferred)

**When to use**: #runSubagent tool is available in your toolkit

**What to load upfront**:
1. Read `SUBAGENT.md` from agent directory
2. Run `lmspace code skills "<agent_path>"` to get skill paths (returns JSON array)

**How to execute each query**:
* Call #runSubagent tool with:
  - subagentMd content
  - skillPaths array
  - query string
* DO NOT read skill file contents (subagent loads them independently)

---

## Strategy 2: Lmspace CLI Executor (Fallback)

**When to use**: #runSubagent tool is NOT available

**What to load upfront**:
* Nothing - go directly to dispatching queries

**How to execute each query**:

1. **Dispatch** - Run in background terminal:
   ```
   lmspace code chat "<agent_path>" "<query>"
   ```
   * OMIT -w flag (lmspace writes to file automatically)
   * Set isBackground=true
   * Capture JSON response with `response_file` field

2. **Wait** - After dispatching ALL queries in group, run synchronous barrier:
   ```
   Start-Sleep -Seconds {waitInterval}
   ```
   * isBackground=false (blocks until complete)
   * DO NOT poll terminals repeatedly

3. **Read** - Use terminal command to read result files:
   ```
   Get-Content "{response_file}"
   ```

---

# Execution Flow

```
// 1. Find agent
agentPath = findAgentPath(agentName)

// 2. Choose strategy (do NOT execute yet, just choose)
if (#runSubagent available) {
  strategy = "runSubagent"
  subagentMd = read(agentPath + "/SUBAGENT.md")
  skillPaths = run(`lmspace code skills "${agentPath}"`) |> parseJSON
} else {
  strategy = "lmspaceCLI"
  // No upfront loading needed
}

// 3. Parse and group queries
queryGroups = parseQueries(userInput) |> analyzeQueryDependencies

// 4. Execute each group
for each group in queryGroups {
  
  // Dispatch all queries in parallel
  dispatches = for each query in group {
    if (strategy == "runSubagent") {
      call runSubagent(subagentMd, skillPaths, query)
    } else {
      run(`lmspace code chat "${agentPath}" "${query}"`, isBackground=true)
      |> extract(response_file)
    }
  }
  
  // Wait for completion (only for lmspaceCLI strategy)
  if (strategy == "lmspaceCLI") {
    run(`Start-Sleep -Seconds ${waitInterval}`, isBackground=false)
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