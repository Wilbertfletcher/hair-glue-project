# {{ProjectName}} TODO List

> **Last updated:** YYYY-MM-DD
> **Philosophy:** Complete each milestone before starting the next. Milestones are separated by explicit gates.
> **Structure:** Numbered milestones with concrete targets, sized tasks, and acceptance criteria.

## Session Navigation

| Document | Purpose |
| -------- | ------- |
| [STATUS.md](STATUS.md) | **Start here each session** — current task, last session summary, completion log |
| [DECISIONS.md](DECISIONS.md) | Resolved design questions with rationale — check before re-asking settled questions |
| [GOTCHAS.md](GOTCHAS.md) | Known pitfalls, deferred items — read before touching unfamiliar code |
| [ROADMAP-M0.md](ROADMAP-M0.md) | Phase plan for Milestone 0 |

> **Completion convention:** When a task's checkbox is ticked, add the date inline:
> `- [x] ~~YYYY-MM-DD~~ Task description`

---

## Milestone 0: Critical Fixes / Initial Setup

**Target:** Before any other milestone work begins
**Status:** Not started
**Gate:** Milestone 1 must not begin until all M0 tasks are complete.

> **GATE:** Complete all M0 tasks before starting Milestone 1.

### 0.1 *(Task title)* *(Size: XS|S|M|L)*

**File:** `path/to/file.py` ~line NNN
**Root cause:** *(what causes this problem or why this needs to change)*
**Fix:** *(one-sentence description of the solution)*

**Acceptance criteria:**

- [ ] *(Observable, testable outcome 1)*
- [ ] *(Observable, testable outcome 2)*

**Pitfall:** *(Known trap to avoid when implementing this. If none, omit this section.)*

---

## Milestone 1: *(Milestone title)*

**Target:** *(Date or condition)*
**Status:** Not started
**Blockers before proceeding:** *(None / list any)*

> **GATE:** Do not start Milestone 2 until all M1 tasks are complete.

### 1.1 *(Task title)* *(Size: XS|S|M|L)*

**File:** `path/to/file.py`
**Description:** *(What needs to be done and why)*

**Acceptance criteria:**

- [ ] *(Observable outcome 1)*
- [ ] *(Observable outcome 2)*

**Pitfall:** *(Optional — known trap)*

---

## Milestone 2: *(Milestone title)* *(Tier B — future)*

**Target:** *(Date or "after M1 complete")*
**Status:** Not started

> *(Add tasks when this milestone becomes active. Keep the spec lightweight until then.)*

---

## Tier B Backlog (future ideas, not scheduled)

> Items that are wanted but not yet prioritized. Promote to a milestone when the time comes.

- *(Idea 1)*
- *(Idea 2)*

---

## Size Reference

| Size | Rough effort | Typical scope |
| ---- | ------------ | ------------- |
| XS | < 30 min | One-liner fix, rename, add a config key |
| S | 30–90 min | Single-function change, small new utility |
| M | 2–4 hours | New module, significant refactor, test suite for a component |
| L | 4–8+ hours | Multi-file feature, complex state changes, new CLI command + tests |
