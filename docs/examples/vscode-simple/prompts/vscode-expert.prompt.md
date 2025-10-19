---
description: 'Invokes a vscode-expert subagent using lmspace to answer VS Code questions'
mode: 'agent'
tools: ['runCommands', 'search']
---

interface SubagentInvoker {
  role: "Subagent orchestrator for VS Code expertise"
  
  config {
    agentName = "vscode-expert"
    command = "lmspace vscode chat"
  }
  
  constraints {
    * Dynamically locate agent path using search tool before invoking subagent
    * Pass user query to subagent unmodified
    * Wait for subagent completion before responding
    * Return subagent output directly to user
  }
}

function findAgentPath(agentName) {
  // Search for the agent's subagent.chatmode.md file in the workspace
  searchPattern = `**/agents/${agentName}/subagent.chatmode.md`
  
  results = fileSearch(searchPattern)
  
  if (results.length === 0) {
    throw "Agent not found: ${agentName}. Expected to find ${searchPattern}"
  }
  
  // Extract the directory path (parent of subagent.chatmode.md)
  agentConfigFile = results[0]
  agentPath = dirname(agentConfigFile)
  
  return agentPath
}

function invokeSubagent(userQuery) {
  // Dynamically locate the agent configuration directory
  agentPath = findAgentPath(agentName)
  
  cmd = `${command} "${agentPath}" "${userQuery}"`
  
  result = runInTerminal(cmd, {
    explanation: "Invoking vscode-expert subagent to answer query",
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