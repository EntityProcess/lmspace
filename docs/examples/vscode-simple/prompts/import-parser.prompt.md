# Import Parser

Parse and resolve import statements from prompt files.

```
fn resolveAllImports;

resolveAllImports(instructionPath) {
  parseImportLines(instructionPath)
    |> resolveToAbsolutePaths(baseDir: path.dirname(instructionPath))
    |> filter(fileExists)
}
```

## Constraints

- Parse standard SudoLang import formats: `import { x } from "file.md"`, `import "file.md"`, `import * from "file.md"`
- Resolve relative paths to absolute paths
- Return array of existing file paths

## Usage

```
import { resolveAllImports } from "import-parser.prompt.md"

instructionPath = "/path/to/instruction.prompt.md"
importPaths = resolveAllImports(instructionPath)
// Returns: ["/path/to/context.md", "/path/to/skill.md", ...]
```

## Output

`resolveAllImports` returns an array of absolute file paths only. The subagent or calling context is responsible for reading the files as needed.
