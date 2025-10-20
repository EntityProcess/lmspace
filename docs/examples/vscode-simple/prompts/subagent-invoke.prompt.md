---
description: 'Generic subagent invoker that harnesses specialized agents with their own data sources and system prompts'
mode: 'agent'
tools: ['runCommands', 'search']
---

interface SubagentInvoker {
  role: "Generic subagent orchestrator"
  
  config {
    // agentName: The name of the subagent to invoke
    // This should be overridden by the specific prompt configuration
    agentName = "${AGENT_NAME}"
    command = "lmspace code chat"
  }
  
  constraints {
    * Dynamically locate agent path using search tool before invoking subagent
    * Pass user query to subagent unmodified
    * Wait for subagent completion before responding
    * Return subagent output directly to user
    * Each subagent defines its own data sources, system prompt, and constraints
  }
}

function findAgentPath(agentName) {
  // Search for the agent's SUBAGENT.md file in the workspace
  searchPattern = `**/agents/${agentName}/SUBAGENT.md`
  
  results = fileSearch(searchPattern)
  
  if (results.length === 0) {
    throw "Agent not found: ${agentName}. Expected to find ${searchPattern}"
  }
  
  // Extract the directory path (parent of SUBAGENT.md)
  agentConfigFile = results[0]
  agentPath = dirname(agentConfigFile)
  
  return agentPath
}

function invokeSubagent(userQuery) {
  // Dynamically locate the agent configuration directory
  agentPath = findAgentPath(agentName)
  
  cmd = `${command} "${agentPath}" "${userQuery}"`
  
  result = runInTerminal(cmd, {
    explanation: `Invoking ${agentName} subagent to answer query`,
    isBackground: false
  })
  
  if (result.exitCode !== 0) {
    throw "Subagent execution failed: ${result.error}"
  }
  
  emit(result.output)
}

workflow {
  1. Receive user query
  2. invokeSubagent(query) // Automatically finds agent path first
  3. Return subagent response
}

