# Contributing to rules-audit

Thanks for your interest! This is a small, focused skill. Here's how to make a
contribution that lands.

## Scope

rules-audit stays **generic**. It audits any Claude Code repo's instruction
context, so it must not contain logic, paths, or assumptions specific to one
user's project.

- Improvements to the audit dimensions, the reference classifier, or the docs:
  welcome.
- Project- or domain-specific behavior: out of scope — that belongs in a local
  `LESSONS.local.md` (gitignored), not here.

## How to contribute

1. **Fork** and branch off `main`.
2. Make your change. Keep `SKILL.md` lean.
3. If you touch `scripts/scan_rules.py`, make sure it still runs:
   ```bash
   python scripts/scan_rules.py --path SKILL.md   # parses one file, emits JSON
   ```
   It must exit 0 and emit valid JSON. CI checks this on every PR.
4. **Open a pull request.** `main` is protected: changes merge via PR,
   squash-merged into a single commit.
5. The reference classifier is tuned for **precision over recall** — a change
   that adds findings should not add false positives. Note in the PR how you
   verified that.

## Style

- The pre-scan is intentionally **stdlib-only** (Python 3.8+). No dependencies.
- Match the tone in `SKILL.md`: honest, evidence-based, no manufactured
  findings.
