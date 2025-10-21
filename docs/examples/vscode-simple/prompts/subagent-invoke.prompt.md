---
description: 'Generic subagent invoker that harnesses specialized agents with their own data sources and system prompts'
mode: 'agent'
tools: ['runCommands', 'search']
---

interface SubagentInvoker {
  role: "Generic subagent orchestrator"
  
  config {
    agentName = "${AGENT_NAME}"
    command = "lmspace code chat"
    pollInterval = 2 // seconds
    maxPolls = 60 // 2 minute timeout
  }
  
  constraints {
    * Locate agent path via fileSearch(`**/agents/${agentName}/SUBAGENT.md`)
    * Pass queries unmodified to subagent
    * Process multiple queries sequentially (one completes before next starts)
    * Poll response file every ${pollInterval}s until exists or timeout
    * Return subagent output directly
  }
}

function findAgentPath(agentName);

function pollResponse(responsePath) {
  for (i in 1..maxPolls) {
    if (exists(responsePath)) return read(responsePath)
    sleep(pollInterval)
  }
  throw "Timeout waiting for ${responsePath}"
}

function invokeSubagent(query) {
  agentPath = findAgentPath(agentName)
  
  result = runInTerminal(`${command} "${agentPath}" "${query}"`)
  responsePath = parseJSON(result.output).response_file
  
  response = pollResponse(responsePath)
  emit(response)
}

workflow {
  queries = parseQueries(userInput)
  for each query, invokeSubagent(query)
}

