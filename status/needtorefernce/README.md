# Tips & Tricks: Working with AI

A collection of practical patterns and reusable templates for collaborating effectively
with AI coding assistants (GitHub Copilot, Claude, etc.) on real software projects.

---

## Contents

| Section | What it gives you |
| ------- | ----------------- |
| [ai-session-planning/](ai-session-planning/) | Framework for long-running, multi-session AI development projects |
| [feature-bug-reporting/](feature-bug-reporting/) | Lightweight inbox system for capturing bugs and feature requests between sessions |

---

## Prerequisites

- **Git** — to clone this repo and use it with your own projects ([git-scm.com](https://git-scm.com))
- **A terminal** — PowerShell (Windows) or bash (macOS / Linux) to run the bootstrap scripts
- **An AI coding assistant** — GitHub Copilot, Claude Code, Cursor, or similar

No special installation required. Everything here is plain markdown files and shell scripts.

---

## Getting started

1. **Clone or download this repo** to your machine (you only need it long enough to copy templates or run the bootstrap)
2. **Pick the framework you want:**
   - [ai-session-planning/](ai-session-planning/) — for multi-session project planning with an AI assistant
   - [feature-bug-reporting/](feature-bug-reporting/) — for a lightweight bug and feature request inbox
3. **Read the README** in that folder — each framework explains itself and includes setup instructions
4. **Copy the templates or run the bootstrap script** into your own project
5. **Fill in the placeholders** (`{{ProjectName}}` etc.) and you're ready

Both frameworks work independently. Using them together gives the most complete workflow.

---

## Philosophy

AI assistants are stateless. Each new chat or agentic session starts with no memory of
what happened before. For trivial tasks that doesn't matter, but for a project spanning
weeks and dozens of sessions the gap between "what the AI knows" and "what is actually
true" compounds into wasted time reinvestigating settled decisions, rediscovering the same
pitfalls, and re-reading the same onboarding material.

The patterns here are solutions to that problem.
