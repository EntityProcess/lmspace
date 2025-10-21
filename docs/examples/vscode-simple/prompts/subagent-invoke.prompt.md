---
description: 'Dependency-aware subagent orchestrator'
mode: 'agent'
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
    * When uncertain about agent relevance, prefer built-in #runSubagent
    * Assess query-agent domain alignment before using custom agents
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
function executeWithRunSubagent(query); // → response
function shouldUseCustomAgent(agentName, queries); // → bool (checks availability, relevance, domain alignment)

workflow {
  queries = parseQueries(userInput)
  
  executor = match (shouldUseCustomAgent(agentName, queries)) {
    case false => executeWithRunSubagent
    case true => (q) => launchQuery(findAgentPath(agentName), q)
  }
  
  queryGroups = analyzeQueryDependencies(queries)
  
  for each group in queryGroups {
    results = group |> map(executor)
    responses = pollQueries(results)
    responses |> forEach(emit)
  }
}