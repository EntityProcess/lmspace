---
description: 'Dependency-aware subagent orchestrator'
---

SubagentRunner {
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
    * Load skills from SUBAGENT.md frontmatter using standard resolution logic
    * Fallback to lmspace command only when runSubagent tool unavailable
    * Preserve query semantics
    * Analyze dependencies before execution
    * Parallelize independent queries; sequentialize dependent ones
  }
}

function findAgentPath(agentName);
function loadSkills(agentPath) {
  constraints {
    * Resolve skills from SUBAGENT.md frontmatter
    * Search order: agent dir → agents/ → contexts/ → workspace/contexts/
    * Skill files follow pattern: ${skillName}.skill.md
  }
}
function analyzeQueryDependencies(queries); // → queries grouped by dependencies
function launchQuery(agentPath, query); // → responsePath (lmspace command)
function executeWithRunSubagent(agentPath, skills, query); // → response (runSubagent tool)
function isRunSubagentAvailable(); // → bool

workflow {
  agentPath = findAgentPath(agentName)
  skills = loadSkills(agentPath)
  
  executor = match (isRunSubagentAvailable()) {
    case true => (q) => executeWithRunSubagent(agentPath, skills, q)
    case false => (q) => launchQuery(agentPath, q)
  }
  
  queryGroups = parseQueries(userInput) |> analyzeQueryDependencies
  
  for each group in queryGroups {
    results = group |> map(executor)
    results |> forEach(emit)
  }
}