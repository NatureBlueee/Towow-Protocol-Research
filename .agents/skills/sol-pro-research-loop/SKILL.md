---
name: sol-pro-research-loop
description: Coordinate GPT-5.6 Sol or Codex with browser-based ChatGPT Pro for difficult Towow research when external frontier reasoning is valuable but the external model cannot access local files, tools, tests, or private state. Use for deep theory, multi-line research, architecture or method comparison, counterexample and experiment design, difficult implementation review, or another task where Codex must prepare a minimal disclosure packet, operate ChatGPT Pro, execute locally, and return evidence. Do not use for routine local edits, lookups, or tests that need no external reasoning.
---

# Sol Pro Research Loop

## Purpose

Use external model intelligence without pretending it has local environment access.

Treat:

- the current Codex/Sol agent as research owner, local executor, and final judge;
- ChatGPT Pro as an external researcher that can reason only from material actually sent;
- every external answer as a candidate until local evidence supports it.

Do not copy the repository constitution into prompts. Read root `AGENTS.md` and
`research/NOW.md`; keep this skill limited to the external-research loop.

## Decide whether to invoke Pro

Invoke Pro when a bounded question would materially benefit from one or more of:

- difficult problem reconstruction or theoretical synthesis;
- comparison of mature, central, general-model, combined, and novel solutions;
- a strong counterexample or competing explanation;
- experiment, simulation, algorithm, or architecture design;
- independent review of a consequential candidate.

Stay local when the next action is mainly file discovery, deterministic checking,
routine editing, test execution, or a fact already available in the workspace.

Do not send material when disclosure is not authorized. Do not use external
consultation merely to obtain agreement or another model vote.

## Run the loop

### 1. Freeze one question

State one research question, why it matters, the current layer of work, and the
observable completion bar. Preserve its lineage to the original V1/V2 problem.

For independent research lines, use separate task IDs and conversations. Do not put
seven mother lines into one prompt.

### 2. Build the minimum sufficient packet

Include only material needed to answer the frozen question:

- exact question and version;
- relevant evidence and source excerpts;
- known positive, negative, and unknown results;
- protected boundaries and forbidden claims;
- required deliverable and acceptance criteria;
- material manifest and hashes when provenance matters.

Prefer a small task packet over a repository ZIP. Add files only when their absence
would change the reasoning. Exclude credentials, browser state, personal data,
unrelated history, and material outside the authorized disclosure scope.

Read [references/prompt-templates.md](references/prompt-templates.md) when preparing
the external task, evidence return, or recovery message.

Read [references/controller-prompt.md](references/controller-prompt.md) when starting
a complete Codex/Sol-to-ChatGPT-Pro research run or when the user asks for the
reusable launcher prompt. Use it as the local controller prompt after filling its
three placeholders. Do not send it wholesale to Pro; send Pro the narrower task
card from `prompt-templates.md`.

### 3. Send an outcome-first task

Load and follow the repository-available browser control skill before operating the
in-app browser. Use the user's existing ChatGPT Pro session only when available.

Tell Pro:

- the result to produce;
- what evidence it may use;
- the hard constraints and permission boundary;
- what would count as success;
- the required output shape;
- when to report missing evidence or stop.

State each instruction once. Do not ask the model to “think harder,” prove Towow is
special, follow a long prescribed chain of thought, or generate a fixed number of
ideas. Leave method choice open unless the task requires a fragile procedure.

### 4. Preserve provenance

Record the conversation URL, task ID, packet version, disclosed files, and relevant
hashes. Save returned reports and attachments in a persistent task-scoped location
when they materially affect the research.

Do not interpret a page timer, animation, or long wait as progress. Avoid duplicate
submissions. On interruption, resume from the last saved checkpoint rather than
silently starting a different run.

If login, CAPTCHA, password, passkey, or two-factor authentication is required, stop
and ask the user to complete it. Never request secrets.

### 5. Convert reasoning into local evidence

Inspect the external result for unsupported assumptions, missing files, invented
execution, and scope drift. Then perform the smallest local action that can
distinguish the candidate from its strongest alternative:

- run a simulation or test;
- apply a candidate patch in scope;
- inspect an authoritative postcondition;
- construct a counterexample;
- compare against an existing or simpler solution.

Keep blind inputs, oracle material, and held-out evaluation separate. A repaired
post-feedback result is development evidence, not a second blind result.

### 6. Return discrepancies, not summaries

When revision is needed, send Pro the actual observation, expected result, exact
evidence, unchanged boundaries, and one precise correction request. Do not resend
the full history or reopen unaffected conclusions.

Repeat only while the next loop can produce new information or solution capability.

## Judge completion

Complete the consultation only when at least one of these is true:

- the candidate passes the defined local acceptance evidence;
- an existing or combined solution is shown to solve the bounded problem;
- a real residual gap is isolated with a discriminating next experiment;
- an external blocker requires user authorization or a material product decision;
- further external turns would only repeat the same mechanism.

Report the solved scope, evidence, remaining unknowns, external model contribution,
local corrections, and current local/commit/deploy status. Never promote model
agreement, polished prose, schema validity, or test count into problem resolution.
