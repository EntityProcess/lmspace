---
description: 'Dependency-aware subagent orchestrator'
---

SubagentRunner {
  role: "Execute subagent queries with intelligent parallelization"
  
  config {
    agentName = "${AGENT_NAME}"
    lmspaceCmd = `lmspace code chat "<agent_path>" "<query>" -w`
  }
  
  constraints {
    * Prefer #runSubagent ; fallback to lmspace via background terminals
    * Locate agent via fileSearch(`**/agents/${agentName}`)
    * Load skills from SUBAGENT.md frontmatter
    * Analyze dependencies; parallelize independent queries
    * Use lmspace `-w` flag to wait indefinitely for response
    * Read terminal output when process completes
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
function analyzeQueryDependencies(queries);
function executeWithLmSpace(agentPath, query); // Blocking call, waits for completion
function executeWithRunSubagent(agentPath, skills, query);
function isRunSubagentAvailable();

workflow {
  agentPath = findAgentPath(agentName)
  skills = loadSkills(agentPath)
  executor = match (isRunSubagentAvailable()) {
    case true => (q) => executeWithRunSubagent(agentPath, skills, q)
    case false => (q) => executeWithLmSpace(agentPath, q)
  }

  queryGroups = parseQueries(userInput) |> analyzeQueryDependencies
  
  for each group in queryGroups {
    // Execute independent queries in parallel (background terminals)
    // Each terminal blocks with `-w` flag until response complete
    // Retrieve results via get_terminal_output when each completes
    group |> map(q => executor(q) with isBackground=true) 
          |> waitForAll()
          |> forEach(emit)
  }
}