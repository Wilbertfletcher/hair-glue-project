# {{ProjectName}} — AI Assistant Context

> This file provides stable project context for AI coding assistants (GitHub Copilot,
> Claude, Cursor, etc.). It describes what the project IS, not where it currently stands
> (that's STATUS.md). Update this file when architecture or conventions change, not
> every session.
>
> For GitHub Copilot: place a copy at `.github/copilot-instructions.md` for automatic
> injection. For other assistants, attach this file when starting a new session.

---

## Overview

*(2–3 sentence description of the project: what it does, who it's for, what problem it solves.)*

---

## Repository Structure

```
project-root/
├── src/                   ← *(what lives here)*
│   ├── module_a/          ← *(purpose)*
│   └── module_b/          ← *(purpose)*
├── tests/                 ← *(test suite description)*
├── TODO/                  ← Planning hub (STATUS, TODO, DECISIONS, GOTCHAS, ROADMAPs)
└── copilot-instructions.md
```

---

## Architecture

*(Architecture diagram or description. Explain the major components and how they
interact. ASCII diagrams are fine.)*

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Component A │───▶│  Component B │───▶│  Component C │
│ (purpose)    │    │ (purpose)    │    │ (purpose)    │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## Key Files

| File | Purpose |
| ---- | ------- |
| `src/main.py` | *(Entry point / what it does)* |
| `src/config.py` | *(Configuration loading — what keys matter)* |
| `TODO/STATUS.md` | **Start here each session** |
| `TODO/DECISIONS.md` | Permanent design decision log |
| `TODO/GOTCHAS.md` | Known pitfalls — read before working in a new area |

---

## Naming Conventions

*(Document any non-obvious naming patterns. Examples:)*

- Functions: `verb_noun()` (e.g., `parse_question()`, `build_exam()`)
- Classes: `PascalCase`
- Config keys: `snake_case`
- *(Add project-specific patterns)*

---

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt   # or: npm install / cargo build / etc.

# Run the main application
python -m src.main

# Run tests
pytest tests/
```

---

## Important Constraints

> *These are hard rules that must be respected during any implementation work.*

1. *(Constraint 1 — e.g., "Never write to disk without user confirmation")*
2. *(Constraint 2 — e.g., "All public API methods must have type hints")*
3. *(Constraint 3 — e.g., "Do not add dependencies without updating requirements.txt")*

---

## External Dependencies / Configuration

*(Describe any external services, config files, or environment variables the project uses.)*

| Dependency | How it's configured | Notes |
| ---------- | ------------------- | ----- |
| *(e.g., Database)* | `config.json` → `db_path` | *(any special setup)* |
| *(e.g., API key)* | `MYAPP_API_KEY` env var | *(falls back to config file)* |

---

## Testing

*(Describe the test suite structure and how to verify work is correct.)*

```bash
# Run all tests
pytest tests/

# Run a specific test file
pytest tests/test_module_a.py -v

# Run tests matching a pattern
pytest tests/ -k "test_parse"
```

**Current baseline:** *(N tests passing / M pre-existing failures)*

---

## When Working Across Multiple Repositories

*(If the project spans multiple repos, describe coordination requirements here.)*

*(Delete this section if the project is a single repository.)*
