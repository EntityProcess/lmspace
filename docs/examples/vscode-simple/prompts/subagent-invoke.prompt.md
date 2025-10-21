---
description: 'Dependency-aware subagent orchestrator'
mode: 'agent'
tools: ['runCommands', 'search']
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
    * Locate agent via fileSearch(`**/agents/${agentName}`)
    * Preserve query semantics
    * Analyze dependencies before execution
    * Parallelize independent queries; sequentialize dependent ones
  }
}

function findAgentPath(agentName);
function analyzeQueryDependencies(queries); // → queries grouped by dependencies
function pollQueries(responsePaths); // → responses when all exist or timeout
function launchQuery(agentPath, query); // → responsePath

workflow {
  queries = parseQueries(userInput)
  agentPath = findAgentPath(agentName)
  queryGroups = analyzeQueryDependencies(queries)
  
  allResponses = []
  
  for each queries in queryGroups {
    launchResults = queries |> map(q => launchQuery(agentPath, q))
    responses = pollQueries(launchResults.map(r => r.responsePath))
    allResponses += responses.withOriginalIndices()
  }
  
  allResponses.sortByIndex() |> forEach(emit)
}