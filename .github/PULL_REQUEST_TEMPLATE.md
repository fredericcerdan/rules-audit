<!-- Thanks for contributing! Keep changes generic — see CONTRIBUTING.md. -->

## What does this change?

<!-- One or two sentences. -->

## Why?

<!-- The problem it solves or the audit gap it came from. -->

## Checklist

- [ ] Change stays **generic** (no project-/domain-specific logic, paths, or names)
- [ ] If `scripts/scan_rules.py` changed, `python scripts/scan_rules.py --path SKILL.md` exits 0 and emits valid JSON
- [ ] Any new finding type does **not** add false positives (precision over recall)
- [ ] Docs (`README.md` / `SKILL.md`) updated if behavior or usage changed
