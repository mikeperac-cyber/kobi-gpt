# Helper prompts — use these between phases

Copy-paste these when the agent gets stuck, drifts, or you want to check its work.

## After every phase: verification
```
Before we move on: go through every acceptance criterion of the phase you just finished.
For each one, tell me PASS / FAIL and the exact evidence (test name, endpoint response, or the UI steps you ran).
Do not mark anything PASS that you did not actually run. Then list anything you skipped or simplified.
```

## When something is broken
```
This is broken: <describe what you did, what you expected, what happened; paste the error / screenshot>.
Do not guess. First find the root cause: reproduce it, read the relevant logs and code, and explain the cause to me in 3–5 sentences.
Only then propose the smallest fix, apply it, and show me that the original steps now work. Add a test that would have caught it.
```

## When the agent starts building out-of-scope things
```
Stop. Re-read the "Out of scope" and "Non-negotiable principles" sections of the project context.
List anything you built or are planning that violates them, and remove or revert it.
```

## When the AI invents regulations or facts
```
The output contains a claim that is not in our knowledge base: "<paste the claim>".
Find where it came from. Tighten the prompt template AND add a code-level check so that only knowledge-base records can appear in compliance/incentive output. Add a test with a mocked LLM that returns an invented rule and assert it is dropped.
```

## When the UI language slips into English
```
Scan every producer-facing screen and component for English text (labels, buttons, errors, empty states, toasts).
Move all strings to the Turkish i18n file and give me the list of what you changed.
```

## Code health check (run once after Phase 3 and once after Phase 5)
```
Review the whole codebase as a senior engineer would before a demo:
1) security holes (auth, ownership checks, file uploads, secrets), 2) places where the floor price could leak,
3) LLM calls without timeouts/fallbacks, 4) dead code and duplication, 5) missing tests for critical logic.
Give me a prioritized list (critical / important / nice-to-have). Fix the critical ones, then ask me about the rest.
```

## Context refresh (start of a new session)
```
Re-read AGENTS.md (the project context) and the README. Then summarize: which phases are done, what is in progress,
and what the next concrete step is. Do not write code until I confirm.
```
