# Code Review Guidelines

This document defines the severity levels and review criteria used by the automated code review
system. When reviewing code changes, issues are categorized by their potential impact.

## Severity Levels

### BREAKS_BUILD

**Exit Code Impact: 2 (blocking)**

Code that will prevent the application from building or starting:

- Syntax errors (missing brackets, incorrect indentation in Python)
- Import/require statements for non-existent modules
- Undefined variables or functions being called
- Type errors that would be caught at compile/startup time
- Missing required configuration or environment variables

Examples:

- `import nonexistent_module`
- `print(undefined_variable)`
- Missing closing parenthesis or bracket
- Incorrect indentation in Python code blocks

### RUNTIME_ERROR

**Exit Code Impact: 2 (blocking)**

Code that will crash or fail during execution:

- Null/None pointer access without checks
- Array index out of bounds
- Unhandled exceptions in critical paths
- Division by zero without guards
- Incorrect type assumptions (e.g., calling string methods on integers)
- Resource leaks (unclosed files, connections)

Examples:

- `user.name` without checking if user is None
- `items[index]` without bounds checking
- Missing try/except around external API calls
- `open()` without corresponding close or context manager

### SECURITY_RISK

**Exit Code Impact: 2 (blocking)**

Vulnerabilities that could be exploited:

- SQL injection vulnerabilities (string concatenation in queries)
- Command injection risks
- Hardcoded secrets, passwords, or API keys
- Unsafe deserialization
- Path traversal vulnerabilities
- Missing authentication/authorization checks
- Exposed sensitive information in logs
- Use of deprecated cryptographic functions

Examples:

- `query = f"SELECT * FROM users WHERE id = {user_input}"`
- `API_KEY = "sk-1234567890"`
- `eval(user_input)`
- Logging passwords or tokens

#### General Security Guidance

Always flag as SECURITY_RISK:

- Missing authentication or authorization checks on sensitive operations
- Hardcoded secrets, credentials, or API keys
- SQL injection, command injection, or other injection vulnerabilities
- Logging sensitive information like passwords, tokens, or personal data
- Unsafe handling of user input or file uploads
- Path traversal vulnerabilities
- Use of known vulnerable dependencies

Consider the project's threat model when evaluating authorization concerns. Some projects may
intentionally have relaxed authorization between authenticated users (e.g., small team tools),
while others require strict isolation (e.g., multi-tenant SaaS). Consult CLAUDE.md or project
documentation for project-specific security requirements.

### LOGIC_ERROR

**Exit Code Impact: 2 (blocking)**

Incorrect program logic that produces wrong results:

- Wrong conditional logic (using AND instead of OR)
- Off-by-one errors in loops
- Incorrect comparison operators
- Missing edge case handling
- Race conditions in concurrent code
- Incorrect state transitions
- Wrong algorithm implementation

Examples:

- `if x > 10 and x < 5:` (impossible condition)
- `for i in range(len(items) + 1):` (will go out of bounds)
- Missing handling for empty lists or None values

### DESIGN_FLAW_MAJOR

**Exit Code Impact: 2 (blocking)**

Significant architectural issues requiring substantial refactoring:

- Circular dependencies between modules
- God objects/functions doing too much
- Tight coupling preventing testability
- Wrong abstraction level
- Synchronous operations that should be async
- Missing critical error handling patterns
- Database queries in loops (N+1 problem)
- Use of mutable global state outside of the application's main entry point
- Instantiation of objects with non-trivial external dependencies deep in the call stack (violates
  Dependency Injection)

Examples:

- Class with 20+ methods handling unrelated concerns
- Direct database access in view/controller layers
- Hardcoded business logic that should be configurable

### DESIGN_FLAW_MINOR

**Exit Code Impact: 1 (warning)**

Local design issues that should be addressed but won't break functionality:

- Functions doing more than one thing
- Poor naming that obscures intent
- Missing appropriate abstractions
- Code duplication that could be refactored
- Inconsistent patterns within a module
- Missing dependency injection

Examples:

- Function named `processData` that also sends emails
- Copy-pasted code blocks with minor variations
- Mixed responsibility in a single class

### SHORTCUT

**Exit Code Impact: 1 (warning)**

This applies when a small part of a task is deliberately left unfinished, as opposed to a larger
feature that is still under development.

Examples:

- A migration to support multiple items finds another area that needs to be updated, but the code is
  updated to just take the first item from a list for now.
- A linter warning is disabled without a good reason, simply to make the linter pass.
- A TODO comment is added for something that should be handled in the current change.

### BEST_PRACTICE

**Exit Code Impact: 1 (warning)**

Deviations from established patterns and conventions:

- Missing docstrings/comments for complex logic
- Not following project naming conventions
- Missing type hints (in typed codebases)
- Not using context managers for resources
- Ignored linter warnings
- Missing error context in exception handling
- Using mutable default arguments

Examples:

- `def calculate_total(items=[]):` # mutable default
- Catching broad exceptions: `except Exception:`
- Magic numbers without constants

### STYLE

**Exit Code Impact: 0 (pass)**

Code formatting and style issues:

- Inconsistent indentation or spacing
- Line length violations
- Import ordering issues
- Trailing whitespace
- Missing blank lines between functions
- Inconsistent quote usage

Examples:

- Mixing tabs and spaces
- Lines longer than project limit
- Unsorted imports

### SUGGESTION

**Exit Code Impact: 0 (pass)**

Improvements for better code quality:

- Performance optimizations
- More idiomatic code patterns
- Alternative approaches worth considering
- Opportunities to use standard library better
- Documentation improvements
- Test coverage suggestions

Examples:

- "Consider using list comprehension instead of loop"
- "This could be simplified using `collections.defaultdict`"
- "Adding unit tests for edge cases would improve coverage"

## Review Process

The review system will:

1. Analyze the git diff for changes
2. Categorize each issue found by severity
3. Exit with the highest severity level found
4. Provide actionable feedback for improvements

## Project-Specific Guidance

Check the project's CLAUDE.md file for project-specific patterns, conventions, and requirements.
Common items to look for:

- Code style preferences
- Testing requirements
- Documentation standards
- Performance expectations
- Security model

## Auto-Formatting and Linting

Many projects use automatic code formatting and linting tools. **The reviewer should NOT suggest
style changes that automated tools would fix.**

Before reviewing, check if the project uses formatters/linters:
- Python: ruff, black, isort, flake8, pylint, mypy, pyright
- JavaScript/TypeScript: prettier, eslint, biome
- Go: gofmt, golangci-lint
- Rust: rustfmt, clippy
- Other languages: check project documentation

### Review Focus

The reviewer should focus on issues that automated tools cannot detect:

1. **Logic errors** and algorithmic correctness
2. **Security vulnerabilities** and safety issues
3. **Design patterns** and architecture decisions
4. **Performance issues** and efficiency concerns
5. **Missing error handling** or edge cases
6. **Documentation completeness** (not formatting)
7. **Test coverage** and quality

**Do NOT flag**:
- Code formatting issues (indentation, spacing, line length)
- Import ordering or organization
- Quote style consistency
- Trailing whitespace
- Other style issues that formatters handle automatically

### Test Quality Requirements

#### Testing Philosophy: Prefer Real/Fake Dependencies Over Mocks

To ensure our tests are realistic and maintainable, we follow a principle of using real or fake
dependencies wherever possible, especially in functional and integration tests. Mocks should be used
sparingly.

- **Real Dependencies**: Use real components like a test database for the most accurate testing.
- **Fake Dependencies**: When a real service is not practical (e.g., it's slow or complex to set
  up), use a high-fidelity "fake" implementation that mimics the real API and behavior.
- **Mocks**: Reserve mocks for isolating a specific unit of code (in unit tests) or for external
  third-party services that are difficult to fake and control.

**Rationale**:

- **Realism**: Tests that use real or fake dependencies provide higher confidence that the system
  works as a whole.
- **Maintainability**: Mocks are often brittle and require updates when the mocked component's API
  changes. Fakes, while requiring initial effort, are generally more robust.
- **Fewer Bugs**: Real integration points are where bugs often hide. Mocks can conceal these
  integration issues.

**Review Guidelines**:

- **Block** changes that introduce mocks for components that already have fake implementations or
  are easily testable with real instances (e.g., mocking the database). This is a
  **DESIGN_FLAW_MAJOR**.
- **Question** the use of new mocks for internal components. Encourage the creation of a fake
  dependency instead.
- **Accept** mocks for external, third-party services where creating a fake is impractical.

#### Time-Based Waits

**CRITICAL: Tests must NEVER use fixed time-based waits.** This is a **LOGIC_ERROR** severity issue.

Tests using `setTimeout`, `sleep`, or fixed delays are flaky and will fail under load or in CI:

❌ **Block these patterns:**

- `await new Promise(resolve => setTimeout(resolve, 2000))`
- `await sleep(500)` (without condition check)
- `time.sleep(1.0)` (without condition check)
- Any arbitrary delay before checking a condition

✅ **Require these patterns:**

- `await waitFor(() => expect(element).toBeEnabled())`
- `await screen.findByText('Success message')`
- `while not condition and time.time() < deadline: await asyncio.sleep(0.1)`
- Condition-based waits with timeouts

**Rationale:**

- Fixed waits are always wrong: too short (flaky) or too long (slow)
- Condition-based waits complete as soon as the condition is met
- Tests must be reliable across different hardware and CI environments

**When reviewing test changes:**

1. Flag any new `setTimeout`, `sleep`, or fixed delays as **LOGIC_ERROR**
2. Suggest condition-based alternatives
3. Accept fixed waits ONLY if modeling actual user behavior timing
4. Ensure test helpers use condition-based waits internally

### General Review Guidelines

- Do NOT correct version numbers, dates and times, etc - remember that your training cutoff may be
  significantly before the present. For example, if a change references a version number that you
  don't know about or that you think is "still in beta", or has the year as 2025, which you believe
  to be in the future, do NOT comment. It's likely that you are wrong.
- Do NOT insist on backwards compatibility if a previous comment has indicated that there is nothing
  to be backwards-compatible with (e.g. changing a hash format where the commit message tells you
  that the hash has never been persisted).
- Do NOT make blocking comments for issues that have been explicitly acknowledged in the commit
  message or where a TODO has been left. Advise, don't block.
- Do NOT correct library usage based on your knowledge - your information might be outdated. Library
  APIs evolve over time and the code may be using newer APIs that you're not aware of. That's what
  type checking and tests are for. Only flag library usage if you can demonstrate it's objectively
  wrong based on the imports and usage patterns within the codebase itself.
