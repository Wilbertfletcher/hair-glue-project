# AI Session Planning Framework

A documentation framework for long-running software projects developed across many
sequential AI agent sessions. Solves the core problem that AI assistants are stateless:
each new session would otherwise require re-reading the codebase, re-settling the same
design questions, and re-discovering the same pitfalls.

---

## The Core Problem

> "Every new AI session is a clean slate. But your project isn't."

When a project spans weeks and twenty-plus sessions, the accumulated knowledge in a human
developer's head — the current task, the decisions made last Tuesday, the weird edge case
discovered on Friday — is completely invisible to the next AI session. Without an
intentional structure, you end up:

- Re-explaining the same architectural context every session
- Re-litigating design decisions that were already settled
- Rediscovering the same pitfalls you hit three sessions ago
- Spending the first 10 minutes of every session just getting the AI back up to speed
- Getting contradictory suggestions that conflict with decisions already made

This framework externalizes that knowledge into a small set of focused documents that
an AI can read in two minutes and be fully productive.

---

## Principles

### 1. One authoritative handoff document

`STATUS.md` is the single file an agent reads first, every session, no exceptions. It
contains only what's needed to resume: the current task, a brief log of what just
happened, and where to start. It is updated at the end of every session via a formal
**Closing Protocol** — a checklist that makes the handoff update a habit, not an
afterthought.

**Why it works:** The agent never has to wonder "am I reading stale info?" — STATUS.md
is always fresh because the Closing Protocol runs before the session ends.

---

### 2. Decision permanence

`DECISIONS.md` is an append-only log of resolved design questions. Once a question is
answered, the entry stays forever with its rationale and date. Entries are never deleted.

**Why it works:** Prevents "we already decided this" moments. When an AI (or a human)
proposes something that was already considered and rejected, the log says so with
the reasoning. This is especially powerful for decisions that seemed arbitrary at
the time but had non-obvious reasons.

Structured format:

```text
## DEC-NNN: Short title
**Question:** What was the open question?
**Decision (YYYY-MM-DD):** What was decided and why.
**Consequences:** What changes as a result.
**Source:** Where the question came from.
```

---

### 3. Pitfall accumulation

`GOTCHAS.md` is a growing list of known pitfalls, non-obvious behaviors, undocumented
quirks, and deliberate deferrals. Entries are never deleted — when a pitfall is
resolved, it is annotated with ✅ and a date.

**Why it works:** The same pitfall never costs you twice. An AI reading GOTCHAS.md
before touching a new area of code is warned about the exact traps ahead. The "never
delete" rule is important: a resolved gotcha is still useful historical context.

---

### 4. Milestone gates, not open-ended backlogs

`TODO.md` organizes work into numbered milestones (M0, M1, M2, …), each with a
concrete completion target and an explicit **gate**: Milestone N must be complete before
Milestone N+1 begins. Tasks within milestones have:

- An explicit **size** (XS / S / M / L)
- **Acceptance criteria** — what "done" means precisely
- **Pitfall callouts** — warnings directly adjacent to the task

**Why it works:** Prevents the failure mode of half-finishing many features. The gate
forces honest completion assessment before expanding scope. Acceptance criteria make
"done" unambiguous to both humans and AI agents.

---

### 5. Per-milestone roadmap files with Agent Primers

Each milestone gets its own `ROADMAP-<name>.md` file with full implementation specs.
The `TODO.md` master list just tracks status; the roadmap has the details. Each
roadmap opens with an **Agent Primer** section: an ordered reading list of exactly
which files an agent needs to read before touching this milestone.

**Why it works:** Separates "what are we doing?" (TODO.md) from "how do we do it?"
(ROADMAP files). The Agent Primer is a time-saver: instead of the AI searching
the codebase to understand context, the primer says "read these 4 files first, in
this order."

---

### 6. Formal closing protocol

At the end of every session, a structured checklist (defined in STATUS.md itself)
specifies exactly which documents to update and how. The protocol includes:

1. Prepend a session entry to STATUS.md history
2. Update the "current milestone" and "where to start next session" fields
3. Mark completed tasks in TODO.md with ✅ and date
4. Add any new pitfalls to GOTCHAS.md
5. Amend any changed decisions in DECISIONS.md
6. Update the relevant ROADMAP file if implementation deviated from spec

**Why it works:** Documentation debt is paid per-session instead of accumulating. The
protocol is short enough (5–9 items) that it doesn't feel expensive, but it keeps every
document current.

---

### 7. Codebase context file for AI assistants

`copilot-instructions.md` (or `.github/copilot-instructions.md` for GitHub Copilot)
provides persistent AI context: architecture diagrams, key file locations, naming
conventions, and constraints. Unlike STATUS.md (which changes every session), this
file is relatively stable and describes what the project *is*, not where it currently
*stands*.

**Why it works:** Many AI editors (GitHub Copilot, Cursor) automatically inject this
context into every session. Even without automatic injection, it's the right file to
attach when starting a session.

---

## Document Map

```text
project-root/
├── copilot-instructions.md    ← Stable project context for AI; read once per project
└── TODO/
    ├── STATUS.md              ← READ FIRST every session; updated every session
    ├── TODO.md                ← Master milestone list; updated when tasks complete
    ├── DECISIONS.md           ← Append-only design decision log
    ├── GOTCHAS.md             ← Growing pitfall list; never delete entries
    └── ROADMAP-<name>.md      ← One per milestone; full specs + Agent Primer
```

---

## Recommended Session Flow

**Starting a session:**

1. Read `TODO/STATUS.md` — get current task and last session summary
2. Read `TODO/GOTCHAS.md` if entering an area of code you haven't touched recently
3. Check `TODO/DECISIONS.md` for any relevant settled questions
4. Read the relevant `ROADMAP-<name>.md` Agent Primer section
5. Do the work

**Ending a session:**
Run the Closing Protocol from STATUS.md — update all documents, prepend session log. If you are using the companion [feature-bug-reporting](../feature-bug-reporting/) framework, run the triage steps (steps 10–11) as part of your closing.

---

## Templates

See [templates/](templates/) for ready-to-use starting points:

| File | Purpose |
| ---- | ------- |
| [templates/TODO/STATUS.md](templates/TODO/STATUS.md) | Session handoff document |
| [templates/TODO/TODO.md](templates/TODO/TODO.md) | Master milestone tracker |
| [templates/TODO/DECISIONS.md](templates/TODO/DECISIONS.md) | Design decision log |
| [templates/TODO/GOTCHAS.md](templates/TODO/GOTCHAS.md) | Pitfall accumulation log |
| [templates/TODO/ROADMAP-TEMPLATE.md](templates/TODO/ROADMAP-TEMPLATE.md) | Per-milestone roadmap |
| [templates/copilot-instructions.md](templates/copilot-instructions.md) | AI context file |

**Quick bootstrap:**

```powershell
# Windows — fresh repo
.\bootstrap.ps1 -ProjectName "MyProject" -DestinationPath "C:\path\to\your\repo"

# Windows — sub-directory within an existing repo
.\bootstrap.ps1 -ProjectName "DataPipeline" -DestinationPath "C:\repos\monorepo\packages\data-pipeline" -SubProject

# Windows — re-run on an existing setup (skip already-present files)
.\bootstrap.ps1 -ProjectName "MyProject" -DestinationPath "C:\path\to\your\repo"

# Windows — re-run and overwrite everything
.\bootstrap.ps1 -ProjectName "MyProject" -DestinationPath "C:\path\to\your\repo" -Force
```

```bash
# macOS / Linux — fresh repo
./bootstrap.sh MyProject /path/to/your/repo

# macOS / Linux — sub-directory within an existing repo
./bootstrap.sh --sub-project DataPipeline /path/to/monorepo/packages/data-pipeline

# macOS / Linux — re-run on an existing setup (skip already-present files)
./bootstrap.sh MyProject /path/to/your/repo

# macOS / Linux — re-run and overwrite everything
./bootstrap.sh --force MyProject /path/to/your/repo
```

**Flags:**

| Flag | PowerShell | Bash | Effect |
| ---- | ---------- | ---- | ------ |
| Sub-project mode | `-SubProject` | `--sub-project` | Scopes `copilot-instructions.md` inside the target subdir; skips `.github/` copy |
| Force overwrite | `-Force` | `--force` | Overwrites files that already exist; default is to skip them |

**Sub-project mode** is for targeted planning within an area of a larger repo (a
package, a module, a major feature). The `TODO/` folder and `copilot-instructions.md`
live inside the subdirectory and describe only that scope. The repo-level
`.github/copilot-instructions.md` (if any) is left untouched — attach the scoped
file manually when opening an AI session on that sub-project.

**Existing repos:** running without `-Force` / `--force` is safe — already-present
files are skipped with a notice, so you can add missing files to a partial setup
without risk of overwriting customized content.

---

## Anti-patterns to Avoid

| Anti-pattern | Problem | Fix |
| ------------ | ------- | --- |
| Deleting old DECISIONS.md entries | Lose rationale for "why it's done this way" | Never delete; annotate with amendments |
| Deleting resolved GOTCHAS.md entries | Re-discover the same problem | Add "RESOLVED: YYYY-MM-DD"; leave the entry |
| Skipping the Closing Protocol | Next session starts blind | Even a 3-line summary is better than nothing |
| Putting implementation details in STATUS.md | STATUS.md becomes too long to skim | Details go in ROADMAP files; STATUS links to them |
| Starting M2 before M1 is gated | Loose ends compound | Enforce milestone gates strictly |
| Vague acceptance criteria ("add the feature") | Can't tell when done | Always specify observable, testable outcomes |

---

## Companion Frameworks

| Framework | What it adds |
| --------- | ------------ |
| [feature-bug-reporting/](../feature-bug-reporting/) | Inbox for bugs and feature requests; integrates with the Closing Protocol as optional steps 10–11 |
