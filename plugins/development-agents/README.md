# development-agents

Collection of specialized development agents and commands for common workflows.

## Installation

```bash
/plugin install development-agents@werdnum-plugins
```

## Agents

### systematic-debugger

**Model**: Opus | **Color**: Yellow

Use for test failures, unexpected behavior, performance issues, or technical problems requiring methodical investigation and root cause analysis.

**Approach**:
- Hypothesis-driven debugging
- Systematic evidence gathering
- Targeted tests over throwaway scripts
- Research when encountering unfamiliar patterns
- Persistent when making progress, pivot when stuck

**Example uses**:
- Intermittent test failures
- Production bugs that can't be reproduced locally
- Performance degradation
- Complex multi-component issues

### focused-coder

**Model**: Haiku | **Color**: Orange

Use for well-defined, self-contained coding tasks. Works excellently in parallel with other focused-coder instances.

**Responsibilities**:
- Implement specific task within narrow scope
- Fix lint errors in working files
- Run relevant tests and fix test failures
- Stay within assigned scope

**Example uses**:
- Add type hints to a specific file
- Implement a new function in a module
- Fix lint errors in a file
- Update test fixtures
- Refactor a specific module

### mechanical-coder

Use for repetitive changes across many files with ast-grep or similar mechanical tools.

**Example uses**:
- Rename function across codebase
- Update import statements
- Apply consistent pattern changes
- Bulk refactoring with ast-grep

### codebase-researcher

Use for code exploration and understanding - finding files, understanding architecture, mapping dependencies.

**Example uses**:
- "Where are errors handled?"
- "How does the authentication system work?"
- "What files implement the calendar feature?"
- "Map out the API endpoint structure"

### external-research-specialist

Use for web research, documentation lookup, and gathering external information.

**Example uses**:
- "What's the latest best practice for React hooks?"
- "Find examples of FastAPI background tasks"
- "Research this error message"
- "Compare authentication libraries"

### playwright-qa-tester

Use for UI testing with Playwright - manual testing and automated test writing.

**Example uses**:
- "Test the login flow manually"
- "Write Playwright test for the checkout process"
- "Debug why the button click isn't working"
- "Capture screenshots of the dashboard"

### parallel-coder

Use for coordinating parallel development across multiple independent tasks.

**Example uses**:
- "Implement feature X while someone else works on feature Y"
- Coordinating multiple focused-coder agents
- Managing independent workstreams

## Commands

### /bootstrap-plugins

Automatically configures all werdnum-plugins for your project through intelligent auto-detection and minimal user interaction.

```
/bootstrap-plugins
```

**What it does**:
- Auto-detects project characteristics (languages, test commands, pre-commit frameworks, etc.)
- Asks critical configuration questions (branch protection, test verification, code review)
- Generates/updates configuration files for all plugins:
  - `.claude/settings.json` - Marketplace and plugin enablement
  - `.claude/bash-guard.json` - Command safety and timeouts
  - `.claude/format-lint.json` - Formatting and linting
  - `.claude/guardian.json` - Test verification and workflows
- Intelligently merges with existing configurations

**Supported pre-commit frameworks**:
- Python's pre-commit (`.pre-commit-config.yaml`)
- Husky (`.husky/`, `package.json`)
- Lefthook (`lefthook.yml`)
- Manual git hooks

**When to use**: Run once when setting up a new project to bootstrap all plugin configurations.

### /test

Runs tests and sends output to Claude.

```
/test
```

Executes `poe test` and displays results.

## Usage Tips

- Use **systematic-debugger** for tricky bugs, **focused-coder** for clear implementation tasks
- Run multiple **focused-coder** agents in parallel on different files
- Use **codebase-researcher** before starting work to understand the codebase
- **external-research-specialist** is great for looking up unfamiliar APIs or patterns
- **playwright-qa-tester** can both test manually and write automated tests

## Agent Coordination

Agents are stateless - they complete a task and return results. For complex multi-step work:

1. Use main Claude instance to coordinate
2. Launch agents for specific subtasks
3. Gather results and synthesize
4. Iterate as needed

## No Configuration Needed

All agents are prompt-based and work out of the box. No configuration files required.

