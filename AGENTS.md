# AGENTS.md

Guidelines for AI coding agents working in this repository. Merge these instructions with any project-specific guidance.

**Tradeoff:** These guidelines favor caution over speed. Use judgment for trivial tasks.

## 1. Think Before Coding

**Do not assume. Do not hide confusion. Surface tradeoffs.**

Before implementing:

* State assumptions explicitly. If uncertain, ask.
* If multiple interpretations exist, present them instead of choosing silently.
* If a simpler approach exists, say so. Push back when warranted.
* If something is unclear, stop. State what is unclear and ask.

## 2. Simplicity First

**Write the minimum code needed to solve the problem. Avoid speculative work.**

* Do not add features beyond what was requested.
* Do not introduce abstractions for single-use code.
* Do not add "flexibility" or "configurability" that was not requested.
* Do not add error handling for impossible scenarios.
* If an implementation takes 200 lines but could be done in 50, rewrite it.

Ask: "Would a senior engineer consider this overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Change only what is necessary. Clean up only what your changes make unnecessary.**

When editing existing code:

* Do not "improve" adjacent code, comments, or formatting.
* Do not refactor code that is not broken.
* Match the existing style, even if you would normally do it differently.
* If you notice unrelated dead code, mention it but do not delete it.

When your changes create unused code:

* Remove imports, variables, or functions made unused by your changes.
* Do not remove pre-existing dead code unless explicitly asked.

Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria and continue until they are verified.**

Translate tasks into verifiable goals:

* "Add validation" → "Write tests for invalid inputs, then make them pass."
* "Fix the bug" → "Write a test that reproduces it, then make it pass."
* "Refactor X" → "Ensure tests pass before and after."

For multi-step tasks, provide a brief plan:

```text
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria allow independent execution. Weak criteria such as "make it work" require clarification.

---

**These guidelines are working if:** diffs contain fewer unnecessary changes, implementations require fewer rewrites due to overcomplication, and clarification happens before implementation rather than after mistakes.
# AGENTS.md

Guidelines for AI coding agents working in this repository. Merge these instructions with any project-specific guidance.

**Tradeoff:** These guidelines favor caution over speed. Use judgment for trivial tasks.

## 1. Think Before Coding

**Do not assume. Do not hide confusion. Surface tradeoffs.**

Before implementing:

* State assumptions explicitly. If uncertain, ask.
* If multiple interpretations exist, present them instead of choosing silently.
* If a simpler approach exists, say so. Push back when warranted.
* If something is unclear, stop. State what is unclear and ask.

## 2. Simplicity First

**Write the minimum code needed to solve the problem. Avoid speculative work.**

* Do not add features beyond what was requested.
* Do not introduce abstractions for single-use code.
* Do not add "flexibility" or "configurability" that was not requested.
* Do not add error handling for impossible scenarios.
* If an implementation takes 200 lines but could be done in 50, rewrite it.

Ask: "Would a senior engineer consider this overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Change only what is necessary. Clean up only what your changes make unnecessary.**

When editing existing code:

* Do not "improve" adjacent code, comments, or formatting.
* Do not refactor code that is not broken.
* Match the existing style, even if you would normally do it differently.
* If you notice unrelated dead code, mention it but do not delete it.

When your changes create unused code:

* Remove imports, variables, or functions made unused by your changes.
* Do not remove pre-existing dead code unless explicitly asked.

Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria and continue until they are verified.**

Translate tasks into verifiable goals:

* "Add validation" → "Write tests for invalid inputs, then make them pass."
* "Fix the bug" → "Write a test that reproduces it, then make it pass."
* "Refactor X" → "Ensure tests pass before and after."

For multi-step tasks, provide a brief plan:

```text
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria allow independent execution. Weak criteria such as "make it work" require clarification.

---

**These guidelines are working if:** diffs contain fewer unnecessary changes, implementations require fewer rewrites due to overcomplication, and clarification happens before implementation rather than after mistakes.

