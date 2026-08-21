# Prompt templates

Use only the template needed for the current turn. Replace placeholders and delete
irrelevant fields. Keep the task narrow.

## External research task

```text
Task ID: <id>
Packet version: <version or hash>

Question:
<one bounded question>

Why it matters:
<decision, design, or capability this could change>

Evidence you may use:
<attached files and source excerpts>

Current known state:
- Supported: <result and evidence>
- Failed or contradicted: <result and evidence>
- Unknown: <material unknown>

Required result:
<theory, comparison, counterexample, experiment, patch, or review>

Success means:
- <observable criterion>
- <observable criterion>

Hard boundaries:
- Do not assume access to local files, tools, tests, or unlisted history.
- Do not report proposed or authorized action as executed.
- Do not invent measurements, citations, or external acceptance.
- Existing, central, general-model, human, adapter, or combined solutions count
  as success when they solve the question.

Return:
1. Problem reconstruction.
2. Best solution and strongest alternatives.
3. Assumptions and failure conditions.
4. The next local test that best distinguishes them.
5. Missing material only if it would materially change the answer.
```

## Local evidence return

```text
Task ID: <id>
Evidence packet: <version or hash>

Actual local observation:
<verbatim result or concise factual description>

Expected versus actual:
<specific discrepancy>

Evidence:
<log, output, score, file, or authoritative postcondition>

Unaffected boundaries:
<claims not tested or changed by this result>

Revise only:
<one precise correction request>
```

## Interrupted conversation recovery

```text
Resume Task <id> from this checkpoint.

Frozen question: <question>
Packet version: <version or hash>
Last completed result: <result>
Unresolved item: <item>
Next requested output: <output>

Do not redo completed work or assume access to earlier attachments unless they are
still visible in this conversation.
```

## Final local synthesis

```text
Solved scope:
Evidence:
Existing or combined solution coverage:
Residual gap:
External contribution:
Corrections made after local validation:
Not established:
Next highest-value action:
Workspace status: local only | committed | pushed | deployed
```
