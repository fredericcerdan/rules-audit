# rules-audit — lessons log

This file is part of the skill and **ships publicly**. It holds short, dated,
*generic* lessons from real audit runs — improvements that apply to anyone
using rules-audit, not to any one user's repo.

Triage rule (see "Step 5 — Reflect" in `SKILL.md`): a lesson lands here only if
it is generic and the user approved it. Repo- or user-specific notes go to
`LESSONS.local.md` (gitignored, never shipped). The strongest generic lessons
get folded directly into the relevant step in `SKILL.md` rather than logged
here.

## Lessons

<!-- newest first — format: `- YYYY-MM-DD — one-line lesson` -->

_None yet. The precision design of the reference classifier — preserve leading
dots, require a known file extension, treat suffix matches as `partial`, and
only call a missing file `stale` when its top-level dir still exists — came out
of the first dry run and is baked into `scripts/scan_rules.py`._
