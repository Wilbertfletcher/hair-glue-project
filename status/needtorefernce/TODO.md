# {{ProjectName}} — Codebase Gotchas

> Persistent list of known pitfalls, non-obvious behaviors, deliberate deferrals,
> and "I already looked into this and decided not to fix it yet" notes.
>
> **Add new entries when you discover something. Never delete entries —
> annotate with "RESOLVED: YYYY-MM-DD" and a brief note when resolved.**
>
> Read this before diving into a new area of the codebase.

---

## Template Entry Format

```text
## [Area/File name] Short description of the gotcha

One paragraph explaining what the pitfall is, what symptom it produces,
and why it exists.

Workaround / status: What to do instead, or why it's deferred.
```

---

## Pre-existing Issues (inherited; don't fix without discussion)

> If you're inheriting a codebase, list known issues here so future sessions
> don't waste time re-investigating them.

Add entries here as you discover pre-existing issues.

---

## Deliberate Deferrals

> Things that were considered but intentionally left for later.
> Add a DEC reference if the deferral decision was formally logged.

Add entries here.

---

<!--
Guidelines:
- Keep entries short — one paragraph is ideal.
- Link to relevant DEC entries when a gotcha is connected to a design decision.
- When a gotcha is resolved: add `RESOLVED: YYYY-MM-DD — <brief explanation>` at the
  bottom of the entry. Do NOT delete the entry.
- Group related gotchas under the same heading.
-->
