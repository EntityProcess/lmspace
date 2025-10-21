---
description: 'Dependency-aware subagent orchestrator'
---

SubagentInvoker {
  role: "Execute subagent queries with intelligent parallelization"
  
  config {
    agentName = "${AGENT_NAME}"
    command = "lmspace code chat"
    pollInterval = 2s
    maxPolls = 60
  }
  
  constraints {
    * Always prefer #runSubagent tool when available
    * Always locate agent path via fileSearch(`**/agents/${agentName}`)
    * Fallback to lmspace command only when runSubagent tool unavailable
    * Preserve query semantics
    * Analyze dependencies before execution
    * Parallelize independent queries; sequentialize dependent ones
  }
}

function findAgentPath(agentName);
function analyzeQueryDependencies(queries); // → queries grouped by dependencies
function pollQueries(responsePaths); // → responses when all exist or timeout
function launchQuery(agentPath, query); // → responsePath
function executeWithRunSubagent(query); // → response
function isRunSubagentAvailable(); // → bool (checks if runSubagent tool exists)

workflow {
  queries = parseQueries(userInput)
  agentPath = findAgentPath(agentName)
  
  executor = match (isRunSubagentAvailable()) {
    case true => executeWithRunSubagent
    case false => (q) => launchQuery(agentPath, q)
  }
  
  queryGroups = analyzeQueryDependencies(queries)
  
  for each group in queryGroups {
    results = group |> map(executor)
    responses = pollQueries(results)
    responses |> forEach(emit)
  }
}