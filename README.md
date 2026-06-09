# rules-audit

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that audits
your repo's **always-on instruction context** — `CLAUDE.md`,
`CLAUDE.local.md`, and `.claude/rules/*.md` — and proposes concrete fixes,
without touching anything unless you say so.

These files load into context *every session*, so they're worth keeping
accurate, lean, and non-duplicative. The skill reviews three dimensions:

1. **Staleness** — references to paths/files that no longer exist (dead links).
2. **Always-on token budget** — files that are oversized, or carry content that
   should load on-demand (a skill or a `docs/` file) rather than every session.
3. **Duplication & contradiction** — the same (or conflicting) guidance stated
   in more than one place across the context layer.

Its guiding rule: **a clean result is a valid result.** It won't manufacture
findings — if your rules are already tidy, it says so.

## How it works

- A dependency-free Python pre-scan (`scripts/scan_rules.py`) does the
  identical-every-time work: locate the context files, measure their size,
  extract and classify every path reference, and surface duplication
  candidates. It emits **facts and candidates only** — every verdict is the
  model's.
- The reference classifier is tuned for **precision** (near-zero false
  positives), so you can trust its `stale` flags:
  - `ok` — resolves exactly
  - `partial` — a shorthand suffix of a real file (not a problem)
  - `stale` — missing, but its top-level dir still exists → real dead link
  - `unresolved` — missing, top-level dir absent → usually points into another
    project, not a defect here
  - `external` — URL / `~/…` / absolute path, not checked

The skill is **propose-only by default** and **git-aware** when you do ask it to
apply a fix (verifies tracking, edits surgically, offers to commit).

## Install

### As a git submodule (recommended)
```bash
git submodule add https://github.com/fredericcerdan/rules-audit \
  .claude/skills/rules-audit
```

### Or copy it in
```bash
git clone https://github.com/fredericcerdan/rules-audit \
  .claude/skills/rules-audit && rm -rf .claude/skills/rules-audit/.git
```

## Usage

In Claude Code, just ask — "audit my rules", "review my CLAUDE.md", "are my
rules stale". Or run the pre-scan directly:

```bash
python scripts/scan_rules.py              # auto-detect repo root (cwd)
python scripts/scan_rules.py --root DIR   # a specific repo root
python scripts/scan_rules.py --path FILE  # a single .md file
```

Python 3.8+, stdlib only.

## Scope

rules-audit deliberately does **not** audit memory files — dedicated
memory-consolidation tooling owns that. It stays generic: nothing about any
particular project is baked in; it only reads a repo's own files as data.

## License

MIT — see [LICENSE](LICENSE).
