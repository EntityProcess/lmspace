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
    * Prefer #runSubagent ; fallback to lmspace with -w flag
    * Locate agent via fileSearch(`**/agents/${agentName}`)
    * Parallelize independent queries after dependency analysis
    * When using lmspace: 
      - Use -w flag for synchronous execution (waits until response ready - queries can take 2+ minutes)
      - Run queries in parallel using background terminals (isBackground=true)
      - Background terminals with -w flag will block until completion; wait for them to finish
      - Queries may take 1-3 minutes to complete;
      - Response will be printed to terminal output when ready; read from console output
      - DO NOT poll or manually read response files; terminal output contains the result
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
function executeWithLmSpace(agentPath, query);
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
    // Execute queries in parallel using background terminals
    results = group |> map(q => run_in_terminal(executor(q), isBackground=true))
    results |> forEach(emit)
  }
}