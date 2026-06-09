---
name: rules-audit
description: >-
  Audit a repo's always-on instruction context — CLAUDE.md / CLAUDE.local.md
  and .claude/rules/*.md — across three dimensions: staleness (references to
  paths/files that no longer exist), always-on token budget (oversized files,
  or content that should load on-demand instead of every session), and
  duplication/contradiction across the context layer. Use this whenever the
  user wants to audit, review, lint, or clean up their rules or CLAUDE.md:
  phrasings like "audit my rules", "review my CLAUDE.md", "are my rules
  stale", "check my context files", "is my CLAUDE.md too big", "any
  duplicated guidance across my rules". Proposes changes by default and does
  NOT edit files unless the user explicitly asks.
---

# rules-audit

Review a repo's **always-on instruction context** — `CLAUDE.md`,
`CLAUDE.local.md`, and every `*.md` under `.claude/rules/` — and produce an
honest, evidence-based audit, followed by concrete fixes and a changelog.
These files load into context *every session*, so accuracy, leanness, and
non-duplication matter more here than for an on-demand skill.

This skill is **propose-only by default** — it reads and recommends; it never
edits a file unless the user explicitly says to apply the changes.

## Core principle: a clean result is a valid result

The biggest failure mode of an audit is manufacturing findings to look
thorough. Do not do this. A well-maintained rules set will produce a short
report with few or no changes — that is success, not a thin deliverable.
Inventing a "stale" reference that is actually fine, or calling two unrelated
passages "duplication", erodes trust and may push the user to break working
rules. The pre-scan is tuned for precision precisely so you can trust its
`stale` flags and reject its softer signals.

## What does NOT apply here (state this, don't audit it)

Rules and CLAUDE.md have **no invocation model** — no `disable-model-invocation`,
no `user-invocable`, no "should the model auto-fire this". They are always-on
context. So unlike a skill audit, there is **no visibility/invocation-safety
dimension** to assess. Do not invent one.

## Step 0 — Load prior lessons first

Read this skill's `LESSONS.md` (generic lessons from past runs, shipped) and
`LESSONS.local.md` if it exists (repo-/user-specific notes, gitignored, never
shipped). They prime the run — a recurring false-positive to reject, a project
convention to respect. If neither exists, skip this step.

## Step 1 — Run the deterministic pre-scan (don't eyeball files)

Locating the context files, measuring their size, extracting + resolving every
path reference, and finding cross-file overlap are fixed, repeatable operations.
Run the bundled script — same result every time, no token cost:

```bash
python scripts/scan_rules.py              # auto-detect repo root (cwd)
python scripts/scan_rules.py --root DIR   # a specific repo root
python scripts/scan_rules.py --path FILE  # a single .md file (no dup pass)
```

The script emits **facts and candidates only** — per-file line/byte counts,
heading outlines, reference classification, and duplication candidates. It
renders **no verdicts**. Reference categories, and how much to trust each:

- **`stale`** — missing file whose top-level directory still exists in the repo
  → high-confidence dead link. Trust these; they are the headline findings.
- **`partial`** — resolves as a suffix of a real file (e.g. `utils/parse.py`
  → `src/utils/parse.py`). Almost always a deliberate shorthand, NOT a problem.
  Only flag if the shorthand is genuinely ambiguous.
- **`unresolved`** — missing, and its top-level dir isn't in the repo → usually
  a reference into *another* project (an external tool's source). Confirm from
  context; rarely a real defect in this repo.
- **`external`** — URL / `~/...` / absolute path. Not checked. Leave alone
  unless the user asked you to verify external links.

If code execution is unavailable, fall back to reading the files directly; do
not block the audit on the script.

## Step 2 — Staleness / dead references

For each `stale` reference, confirm it really is dead and propose the fix:
point it at the current path, or remove the line if the thing is gone. Use
judgment on WHERE it lives — an actively-runnable snippet (a command block) that
is wrong is worse than a historical note (a "parked task", a changelog entry)
that mentions an old path on purpose. Fix the former; flag the latter and let
the user decide rather than rewriting their own record.

Do not "fix" `partial` / `unresolved` / `external` references unless you have
specific evidence they're wrong — that is the noise the precision tuning exists
to let you ignore.

## Step 3 — Always-on token budget

These files cost tokens on every turn. Using the pre-scan's line/byte counts:
- Flag files that are large for what they carry. There is no hard limit, but a
  rule file in the high hundreds of lines is worth a look.
- The sharper question than raw size: **does this content need to be always-on?**
  Reference material consulted occasionally (a long API dump, a one-off
  procedure, an indicator's full source) belongs in an on-demand **skill** or a
  `docs/` file that the rule *links to*, not inline in always-on context.
- Propose concrete trims: extract section X to `docs/…` and link it; move
  procedure Y into a skill. Never propose deleting guidance outright — relocate
  it so nothing is lost.

Be honest: if every file is reasonably sized and genuinely needs to be
always-on, say the budget is fine and move on.

## Step 4 — Duplication & contradiction

Using the duplication candidates (and your reading), find:
- **Duplication** — the same guidance stated in two places (rule ↔ rule, rule ↔
  CLAUDE.md, rule ↔ a skill). Duplicated facts drift out of sync. Propose a
  single home and a one-line pointer from the other.
- **Contradiction** — two places giving conflicting instructions. This is the
  most damaging finding; surface it clearly with both locations.

Be strict about real overlap: the pre-scan's duplication candidates are raw
line matches and include coincidental phrasing. Two passages on different topics
are not duplication. If the context layer is small or already deduplicated, say
there's nothing to extract.

## Output format

Produce, in this order:

1. **One-line headline** — overall result (e.g. "N files, ~M always-on lines;
   1 stale ref, the rest clean").
2. **Per-file / per-dimension findings** — mark clean dimensions clean. Cite
   specific file:line and the scan's categories as evidence.
3. **Changelog table** — columns: File | Change | Why. Separate recommended
   changes from optional ones. If nothing was applied, label it
   "proposed — files not modified".
4. **Fixes** — show the concrete before/after for each recommended change. For a
   relocation (budget), show the new file + the linking line.

## Applying changes — git-aware, and only when asked

This skill is propose-only until the user says to apply. When they do, the
targets (`CLAUDE.md`, `.claude/rules/*.md`) are almost always tracked in git;
`CLAUDE.local.md` is usually gitignored. Treat them accordingly:

- **Verify tracking from the repo root, never from the cwd:**
  `git -C <repo-root> ls-files <path>` and `git -C <repo-root> status --short`.
  A path-scoped git command run from inside a subfolder silently doubles the
  path and returns nothing — do not read that empty result as "untracked".
- **Delete tracked content with `git rm`** (or just edit in place for line-level
  fixes); a plain edit is fine for a gitignored file like `CLAUDE.local.md`.
- **After applying anything, show `git status --short`** and offer to commit —
  but do not commit or push unless asked. If the repo isn't under git, say so.
- Be extra careful editing `CLAUDE.local.md` and other personal-note files:
  prefer surgical line edits and preserve the user's historical records (parked
  tasks, changelogs) rather than rewriting them.

## Step 5 — Reflect and record lessons (close the loop)

Run this only if the run hit friction: the user corrected you, the scan
mis-classified something, or a judgment call turned out wrong. Do not
manufacture lessons on a clean run.

When there is something real, propose each lesson as a one-liner and let the
user route it — never write silently:

- **Fold in (generic):** true for anyone using rules-audit → fold into the
  relevant step here, or append a dated bullet to `LESSONS.md`. Ships publicly,
  so keep it generic (no repo names, paths, or user specifics).
- **Keep local:** specific to this repo or user → append to `LESSONS.local.md`
  (gitignored, never shipped). Create it if absent.
- **Discard:** a one-off that isn't a lesson → drop it.

## Scope and assumptions to state up front

- `CLAUDE.md` / `.claude/rules/` are **Claude Code** conventions. If it's unclear
  whether the repo's instructions run through Claude Code, say the audit assumes
  that context.
- This skill deliberately does **not** audit memory files — the separate
  memory-consolidation tooling owns that. Auditing it here would duplicate it.
- The pre-scan's reference classifier biases toward **precision over recall**: a
  wholesale directory deletion lands in `unresolved`, not `stale`. If the user
  wants exhaustive dead-link detection, note this trade-off.
