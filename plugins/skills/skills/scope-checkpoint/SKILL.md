---
name: scope-checkpoint
description: Use when addressing PR review feedback after an earlier remediation, or when a proposed fix adds state, retries, validation, attestation, lifecycle machinery, or an unrequested guarantee. Detects edge cases caused by review machinery and stops scope-creep fix loops.
---

# Scope Checkpoint

Before extending a change to satisfy review, compare the original request, the PR's stated outcome, the current diff, and the review-fix history.

## Classify the finding

Label it as one of:

- a reachable defect in the original change;
- a defect introduced by an earlier review fix;
- justified hardening required by the stated outcome; or
- an attempt to uphold a guarantee, coverage claim, or attestation nobody requested.

Require the concrete trigger, affected boundary, and consequence. Do not turn a hypothetical into a requirement merely because machinery could address it.

## Prefer subtraction

For an unrequested promise, withdraw or narrow the promise first. Do not add an evaluator, ledger, signature, validation layer, or monitoring path merely to make the claim defensible.

For a defect in earlier review machinery, first try deleting that machinery, narrowing its contract, or reusing an existing authoritative chokepoint. A documented bounded residual is valid when the owner accepts it and the stated outcome still holds.

## Stop the fix loop

Pause automatic remediation when the next fix would add persistent state, a schema or migration, retries or background work, another validation or attestation layer, a new service, or another lifecycle boundary. Also pause when review repeatedly finds edge cases in code added solely for prior feedback.

Present the decision owner with the smallest options: subtract or reuse, narrow the claim, accept a bounded residual, split a separately justified change, or explicitly authorize the expanded design. State which option you recommend and why. Do not continue layering fixes without that decision.

If no checkpoint triggers, implement the smallest in-scope remedy and run focused verification for the affected behavior.

