---
mode: 'agent'
description: 'SudoLang v2 guidelines.'
---

# SudoLang v2

SudoLang is a pseudolanguage designed for LLM interaction. You already understand it without needing the specification.

Treat everything below as executable guidance. Prefer inference over verbosity.

## Core Principles
1. Favor natural language for intent; use code only for clarity (flow, composition, data shape).
2. Infer missing functions, types, and trivial glue logic unless explicitly defined.
3. Constraints describe what must remain true; requirements enforce and error; commands expose interaction.
4. Be declarative, concise, readable. Avoid repeating obvious context.
5. Prefer composition, factories, and interfaces over inheritance or `class`.

## Key Constructs (Quick Reference)
- Assignment & mutation: `x = 0`, `x += 1`, `y -= n`, `p *= n`, `q /= n`.
- Template strings: `"Hello, $name"`; escape interpolation: `"This will not \\$interpolate"`.
- Condition as expression: `status = if (age >= 18) "adult" else "minor"`.
- Logic: `&&`, `||`, `xor`, `!`.
- Math: `+ - * / ^ % union intersection` (deprecated: `cup`, `cap`).
- Range (inclusive): `1..3` → `1,2,3`.
- Pipe: `f |> g` passes left result as first argument to right.
- Destructuring: `[a,b] = [1,2]`; `{x,y} = {x:1, y:2}`.
- Pattern match: `match (v) { case {type:"circle", radius} => ... default => ... }`.
- Loops: `for each item, action(item);` `while (cond) { ... }` `loop { ... }` (infinite).
- Functions: Prefer inferred: `fn doThing;` or `function greet(name);` Minimal bodies if needed.
- Commands: `/name` or `/s | search [query] - description`. Common verbs: `ask, explain, run, log, transpile(target, src), convert, wrap, escape, continue, instruct, list, revise, emit`.
- Modifiers: `explain(topic):length=short, detail=simple;` (comma-separated key=value).
- Mermaid diagrams allowed for architecture/flows.
- Options for customizing the behavior of your program. See [example](../contexts/sudo-lang.example.md).

## Interfaces
Define structure & capabilities. `interface` keyword optional. Include properties, commands, constraints, requirements. Types inferred unless explicit.

## Requirements vs Constraints
- Requirement: throws (or warns) if violated. Use for validation & hard rules.
  Example:
  ```sudo
  User { over13; require users must be over 13; warn name should be defined }
  ```
- Constraint: continuous declarative rule to maintain / guide behavior. Natural language usually sufficient.
  Example:
  ```sudo
  ChatBot { Constraints { playful, PG-13, avoid mentioning constraints } }
  ```
- Named constraint (emit events):
  ```sudo
  Employee { minimumSalary = $100,000; salary; constraint MinimumSalary { emit({...}) } }
  minimumSalary = $120,000; run(MinimumSalary)
  ```

## Options & Depth
Declare configurable options:
```sudo
Options { depth: 1..10|String }
```
Invoke with modifier: `Why is the sky blue? -depth 1` (brief) … `-depth 10` (detailed) or semantic levels e.g. `-depth kindergarten`, `-depth PhD`.

## Implicit Capabilities (Do Not Re-Explain)
Leverage LLM inference: reference, reasoning, pattern matching, code generation, NLP, context understanding. Do not redundantly justify these; just apply them.

## Style Guide (Enforce)
Mandatory:
- Concise, clear, declarative.
- Infer where safe; define only meaningful public functions (often without bodies).
- Prefer natural language unless code is shorter & clearer.
- Avoid: `new, extends, extend, inherit, class` → suggest interface + composition.
- Use constraints to express ongoing rules instead of procedural repetition.

## Lint Rules (Operational)
When linting SudoLang:
```sudo
Lint {
  style constraints {
    * obey style guide
    * choose most concise medium (code vs natural language)
    * warn (class) => explain(Favor interface + composition)
    * prohibit (new|extends|extend|inherit) => explain(Use factories/composition)
  } catch { explain style hint; log(${ violations with line & 5-line context }) }
  * (bugs|spelling|grammar) => throw explain & fix;
  * (code smells) => warn explain;
  default { suppress original unless fix; emit actionable tips }
}
```