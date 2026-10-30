# T-NNN · Short title

<!-- Copy this file to docs/tasks/T-NNN-<slug>.md and fill it in.
     The manager creates task files. Workers do not create tasks.
     Keep the section order — sessions parse these headings. -->

- status: ready            # ready | in-progress | review | done | blocked
- quest: Qx
- depends: T-0yy, T-0zz   # or: none
- owner: -                 # session label of the worker, e.g. s-20261030-1412
- updated: -               # ISO date of the last change
- files: path/a.py, path/b.tsx

## Goal

One paragraph. What "good" looks like when this task is done.

## Done when

- [ ] `command` → expected result
- [ ] `command` → expected result

Every box must be a **runnable** command from `AGENTS.md` §8 (or a new one added there). If you cannot
write a runnable check, the task is not ready to be worked — tell the manager.

## Notes / gotchas

Anything the next session must not trip over. Put discoveries here as you make them.

## Research notes

Findings cached while working (versions, URLs, quirks, licence facts). Do not re-research these.
If a topic belongs to the whole project, put it in `docs/research/<n>-<topic>.md` and link it here.

## Work log

- 2026-10-30 s-1412: did X, blocked on Y

## Report

### 2026-10-30 · worker s-1412

- changed: files touched, in one line each
- verified: command → actual result (paste the real output line)
- issues: what broke, what's left
- next: suggested next task

## Blocker

<!-- Only when the worker is stuck. See AGENTS.md §12. -->

### 2026-10-30 · worker s-1412

- failed: `command` → the actual error, pasted
- worker diagnosis: what the worker thinks is wrong
- tried: what was attempted
- needs: a decision | a new task | more info

## Manager diagnosis

<!-- Manager only. See AGENTS.md §12. -->

### 2026-10-30 · manager s-1500

- reproduced: yes | no  → `command` → output
- worker said: their diagnosis in one line
- manager found: the manager's own diagnosis
- combined conclusion: where they agree, where they differ, and the truth
- root cause: one paragraph
- fix approach: what the fix is
- new task: T-0xx

## Manager review

### 2026-10-30 · manager s-1500

- verdict: accepted | rework
- checked: what the manager re-ran
- notes: required changes, if any
