# {{ProjectName}} — Session Status (Handoff Document)

> **Purpose:** This file is the authoritative handoff between sequential working sessions.
> Update it at the END of every session using the Closing Protocol below.
> An agent starting a new session should read this file FIRST.

---

## Last Updated: YYYY-MM-DD (session N — one-line description)

## Current Milestone: M0 — Not started

## Where to Start Next Session

> Replace this section with a precise task, file to open, and command to run.

1. Open `TODO/TODO.md` and pick up at task **0.1**
2. Read this file top-to-bottom, then the relevant ROADMAP file
3. *(add any specific command to run here)*

---

## Session History

> Append new entries at the **top** of this list. Do not delete old entries.

### YYYY-MM-DD — Initial setup (Session 0)

- Created planning documents: STATUS.md, TODO.md, DECISIONS.md, GOTCHAS.md
- Initial milestone structure defined

---

## Milestone Completion Log

> Track task completion across all milestones here. Add rows as new milestones are defined.

### Milestone 0

| Task | Completed | Notes |
| ---- | --------- | ----- |
| 0.1 *(describe task)* | Not started | |

---

## Open Blockers

> List anything that prevents progress. Remove when resolved.

| Blocker | Milestone | Since | Notes |
| ------- | --------- | ----- | ----- |
| *(none)* | — | — | — |

---

## Closing Protocol (run at end of every session)

1. **Session History** — prepend a new `### YYYY-MM-DD — <short description>` entry to this file; keep all prior entries
2. **Last Updated** — change the date and session number at the top
3. **Current Milestone** — update if the milestone changed or completed
4. **Where to Start Next Session** — write the exact next task, file, and command
5. **Milestone Completion Log** — mark completed tasks with `Done: YYYY-MM-DD`; use Notes for deviations
6. **Open Blockers** — add newly discovered blockers; remove resolved ones
7. *(if applicable)* **GOTCHAS.md** — add any new pitfall, edge case, or deliberate deferral (never delete; annotate resolved entries with "RESOLVED: YYYY-MM-DD")
8. *(if applicable)* **DECISIONS.md** — if implementation forced a design revision, append `**Amended (YYYY-MM-DD):** <what changed>` to the relevant DEC entry
9. *(if applicable)* **ROADMAP file** — if your approach differed from the spec, add `**Actual:** <what you actually did>` under the completed task
10. *(if applicable, requires feature-bug-reporting)* **feature-requests.md** — if `## New` has items, route each to the task system and move verbatim to `## Incorporated into TODO`
11. *(if applicable, requires feature-bug-reporting)* **bug-reports.md** — if `## Unresolved` has items not yet logged, add to GOTCHAS.md and/or backlog; move verbatim to `## Incorporated into TODO`; promote to `## Resolved` any bugs confirmed fixed this session

> Keep STATUS.md SHORT. Implementation details belong in ROADMAP files.
