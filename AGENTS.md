# AGENTS.md

## Review Scope Discipline

- Require a concrete, reachable failure before expanding a change. If a proposed remedy adds persistent state, a schema or migration, retries or background work, validation or attestation, a new service, or another subsystem, present it as a scope decision instead of an automatic review fix.
- Do not invent guarantees, coverage claims, or attestations the user did not request. If review shows an unrequested promise cannot be justified, withdraw or narrow the promise before adding machinery to make it true; reviewers should question whether the promise belongs, not only whether it is proven.
- On rereview, distinguish defects in the original change from defects introduced by earlier review fixes. If another fix would add another layer, stop the loop and prefer deletion, narrowing, reuse of an existing chokepoint, or an explicitly accepted bounded residual unless the owner authorizes the expanded design.


Guidance for AI coding agents working in this repository. See `CLAUDE.md` for the full repository overview.

## Version Bumping

**ALWAYS bump the plugin's version when making changes to it.** This applies to any change to a plugin's contents (commands, agents, skills, hooks, scripts, manifests, etc.).

- Update `version` in the plugin's `.claude-plugin/plugin.json`
- Update the matching `version` entry in `.claude-plugin/marketplace.json`
- Use semantic versioning: PATCH for fixes, MINOR for new features, MAJOR for breaking changes
- Both files must stay in sync — installers read versions from `marketplace.json`, but the plugin manifest is the source of truth

## Repository Layout

```
plugins/<plugin-name>/
  .claude-plugin/plugin.json   # Plugin manifest (name, version, description)
  commands/                    # Slash commands (optional)
  agents/                      # Agent definitions (optional)
  skills/                      # Agent Skills (optional)
  hooks/                       # Event handlers (optional)
.claude-plugin/marketplace.json  # Marketplace catalog
```

## Commit Messages

Write descriptive commit messages that explain **what** changed and **why**. See `CLAUDE.md` for the full guidance and example.
