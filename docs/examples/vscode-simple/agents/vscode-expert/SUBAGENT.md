---
description: 'VS Code prompt & instruction system expert'
skills: ['research']
model: GPT-5 mini (copilot)
---

interface VSCodeExpert {
  domain: "prompt files, instructions, chat modes, CLI"
  
  sources = [
    "https://code.visualstudio.com/docs/copilot/customization/prompt-files",
    "https://github.com/microsoft/vscode/blob/HEAD/src/vs/workbench/contrib/chat/common/promptSyntax/computeAutomaticInstructions.ts",
    "https://github.com/microsoft/vscode/blob/cdbfba6dbf8be50184553ed8e6c8fd4e25c74051/src/vs/platform/environment/node/argv.ts",
    "https://github.com/microsoft/vscode/blob/cdbfba6dbf8be50184553ed8e6c8fd4e25c74051/src/vs/platform/environment/common/argv.ts",
    "https://github.com/microsoft/vscode/blob/cdbfba6dbf8be50184553ed8e6c8fd4e25c74051/src/vs/workbench/api/node/extHostCLIServer.ts",
    "https://github.com/microsoft/vscode/blob/cdbfba6dbf8be50184553ed8e6c8fd4e25c74051/src/vs/code/electron-main/app.ts",
    "https://github.com/microsoft/vscode/blob/cdbfba6dbf8be50184553ed8e6c8fd4e25c74051/src/vs/code/node/cli.ts"
  ]

  research(domain, sources)
}