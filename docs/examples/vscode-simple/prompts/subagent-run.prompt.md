---
description: 'Dependency-aware subagent orchestrator'
---

SubagentRunner {
  role: "Execute subagent queries with intelligent parallelization"
  
  config {
    agentName = "${AGENT_NAME}"
    lmspaceCmd = `lmspace code chat "<agent_path>" "<query>" -w`
    skillsCmd = `lmspace code skills "<agent_path>"`
  }
  
  constraints {
    * Prefer #runSubagent ; fallback to lmspace via background terminals
    * Locate agent via fileSearch(`**/agents/${agentName}`)
    * Parallelize independent queries after dependency analysis
    * When using lmspace: `-w` waits indefinitely; run in background terminal
    * When using runSubagent:
      - Resolve skill paths via skillsCmd (returns JSON array)
      - Read SUBAGENT.md from agent directory
      - Pass to subagent: SUBAGENT.md content + skill paths + user query
      - DO NOT read or access skill file contents; only pass paths
      - Subagent will independently fetch and apply skill files
  }
}

function findAgentPath(agentName);
function readSubagentMd(agentPath);  // Read SUBAGENT.md from agent directory
function resolveSkillPaths(agentPath);  // Execute: lmspace code skills <agentPath>
function analyzeQueryDependencies(queries);
function executeWithLmSpace(agentPath, query);  // Handles skill resolution internally
function executeWithRunSubagent(subagentMd, skillPaths, query);  // Pass SUBAGENT.md content + skill paths
function isRunSubagentAvailable();

workflow {
  agentPath = findAgentPath(agentName)
  executor = match (isRunSubagentAvailable()) {
    case true => {
      subagentMd = readSubagentMd(agentPath)
      skillPaths = resolveSkillPaths(agentPath)
      (q) => executeWithRunSubagent(subagentMd, skillPaths, q)
    }
    case false => (q) => executeWithLmSpace(agentPath, q)
  }

  queryGroups = parseQueries(userInput) |> analyzeQueryDependencies
  
  for each group in queryGroups {
    group |> map(q => executor(q) with isBackground=true) 
          |> waitForAll()
          |> forEach(emit)
  }
}