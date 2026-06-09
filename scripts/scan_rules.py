#!/usr/bin/env python3
"""
scan_rules.py - deterministic pre-scan for the rules-audit skill.

Audits the always-on instruction layer of a repo using Claude Code: the
`CLAUDE.md` / `CLAUDE.local.md` files at the repo root and every `*.md` under
`.claude/rules/`. These files are loaded into context every session, so they
are worth keeping accurate, lean, and non-duplicative.

Like the skill-audit pre-scan, this does ONLY the boring, identical-every-time
work and emits FACTS and CANDIDATES, never verdicts:
  - locate the context files
  - measure each one's size (lines + bytes) for the always-on-budget question
  - extract referenced paths and classify each as ok / partial / stale / external
  - surface cross-file duplicate passages as candidates

Every judgment -- "is this stale reference worth fixing?", "is this passage
real duplication or just similar?", "is this file too big to be always-on?" --
is
deliberately left to the model running the skill.

The reference classifier is the heart of this script and is tuned for
PRECISION (near-zero false positives), because a noisy staleness check is
worse than none:
  - ok      : path resolves exactly, relative to the repo root
  - partial : path does not resolve as-written but is a suffix of a real file
              (e.g. "conditions/base.py" -> "pkg/conditions/base.py") -- almost
              always a shorthand reference, NOT a dead link
  - stale   : missing, no suffix match, AND its top-level dir EXISTS in the
              repo -> a high-confidence dead link (a file removed from a dir
              that's still here)
  - unresolved : missing, no suffix match, and its top-level dir does NOT exist
              in the repo -> almost always a reference into another project
              (e.g. an external tool's `src/foo.js`), not a dead link here.
              Reported separately so the model can confirm, biasing toward
              precision over recall (a wholesale dir deletion lands here, not
              in `stale`)
  - external: URL, `~/...`, or an absolute path -> points outside the repo, not
              checked (reported so the model can spot-check if it wants)

Repo-agnostic: nothing about any particular project is baked in. The script
only reads the repo's own files as data.

Usage:
  python scan_rules.py                  # auto-detect repo root (cwd)
  python scan_rules.py --root DIR       # scan a specific repo root
  python scan_rules.py --path FILE      # scan a single .md file (no dup pass)

Output: JSON to stdout. Stdlib only, Python 3.8+.
"""

import argparse
import glob
import json
import os
import re
import sys

KNOWN_EXTS = {
    "py", "md", "sh", "json", "yml", "yaml", "txt", "db", "cfg",
    "ini", "toml", "js", "ts", "tsx", "jsx", "html", "css", "sql", "csv",
    "env", "lock", "rs", "go", "java", "rb", "php", "c", "cpp", "h",
}

# Directories never worth indexing when resolving references.
IGNORE_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__",
               ".mypy_cache", ".pytest_cache", "dist", "build", ".idea"}

# A path-ish token: may start with ~ . / or a word char; then word chars,
# dots, slashes, hyphens, tildes. Captures ".claude/x", "~/y", "/abs/z", "a/b.py".
TOKEN_RE = re.compile(r"[~./\w][\w./~-]*")

MAX_DUP_PER_PAIR = 8     # cap duplicate-line output per file pair
MIN_DUP_LINE_LEN = 40    # ignore short shared lines (headings, boilerplate)


def auto_detect_root():
    """The repo root is the current working directory if it looks like a
    Claude Code project (has CLAUDE.md or a .claude/rules dir). Returns cwd
    regardless, so --root can override; discovery just confirms targets exist."""
    cwd = os.getcwd()
    return cwd


def find_targets(root):
    """Return the list of context files to audit under root."""
    out = []
    for name in ("CLAUDE.md", "CLAUDE.local.md"):
        p = os.path.join(root, name)
        if os.path.isfile(p):
            out.append(p)
    out += sorted(glob.glob(os.path.join(root, ".claude", "rules", "*.md")))
    return out


def build_file_index(root):
    """Return a set of repo-relative file paths (posix-style) for reference
    resolution, skipping heavy/irrelevant directories."""
    index = set()
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fn in files:
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            index.add(rel.replace(os.sep, "/"))
    return index


def is_path_like(tok):
    """A token is a path candidate only if it contains a slash AND ends in a
    known file extension. This rejects domains, version numbers, prose like
    'and/or', AND bare directory refs (`rules/`, `skills/`) -- the latter are
    usually tree-diagram labels, not resolvable paths, and checking them is
    pure noise. Staleness is meaningful for specific files, so we check only
    those."""
    if "/" not in tok or tok.endswith("/"):
        return False
    m = re.search(r"\.([A-Za-z0-9]+)$", tok)
    return bool(m) and m.group(1).lower() in KNOWN_EXTS


def classify_reference(tok, root, index):
    """Classify a path-like token. See module docstring for categories."""
    if re.match(r"^(https?://|git@|[a-z]+://)", tok):
        return "external"
    if tok.startswith("~") or os.path.isabs(tok):
        return "external"

    clean = tok.replace(os.sep, "/")

    if os.path.exists(os.path.join(root, clean)):
        return "ok"

    # Not exact: is it a suffix of a real file path? Then it's a shorthand, not
    # a dead link.
    suffix = "/" + clean
    for rel in index:
        if rel == clean or rel.endswith(suffix):
            return "partial"

    # Missing and unmatched. Only call it a dead link if its top-level dir is
    # actually here; otherwise it points into another project.
    top = clean.split("/", 1)[0]
    if os.path.isdir(os.path.join(root, top)):
        return "stale"
    return "unresolved"


def extract_references(text, root, index):
    """Return {category: sorted [tokens]} for all path-like tokens in text."""
    buckets = {"ok": set(), "partial": set(), "stale": set(),
               "unresolved": set(), "external": set()}
    for raw in TOKEN_RE.findall(text):
        tok = raw.rstrip(".,;:")  # trim trailing prose punctuation (keep leading '.')
        if not is_path_like(tok):
            continue
        buckets[classify_reference(tok, root, index)].add(tok)
    return {k: sorted(v) for k, v in buckets.items()}


def headings(text):
    """Return the markdown heading outline (## / ### lines)."""
    return [ln.strip() for ln in text.splitlines() if re.match(r"^#{1,4}\s", ln)]


def normalize_line(ln):
    return re.sub(r"\s+", " ", ln.strip()).lower()


def duplicate_candidates(files_text):
    """Surface normalized lines shared across file pairs (candidates only)."""
    norm = {}
    for path, text in files_text.items():
        seen = {}
        for ln in text.splitlines():
            n = normalize_line(ln)
            if len(n) >= MIN_DUP_LINE_LEN and not n.startswith(("#", "```", "|", "-", "*")):
                seen.setdefault(n, ln.strip())
        norm[path] = seen

    out = []
    paths = list(norm)
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            a, b = paths[i], paths[j]
            shared = sorted(set(norm[a]) & set(norm[b]))
            if shared:
                out.append({
                    "file_a": a, "file_b": b,
                    "shared_line_count": len(shared),
                    "samples": [norm[a].get(s, s)[:140] for s in shared[:MAX_DUP_PER_PAIR]],
                })
    out.sort(key=lambda d: d["shared_line_count"], reverse=True)
    return out


def analyse_file(path, root, index):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    return rel, text, {
        "file": rel,
        "line_count": len(text.splitlines()),
        "byte_size": len(text.encode("utf-8")),
        "headings": headings(text),
        "references": extract_references(text, root, index),
    }


def main():
    ap = argparse.ArgumentParser(description="Deterministic pre-scan for rules-audit.")
    ap.add_argument("--root", default=None, help="Repo root to scan (default: cwd).")
    ap.add_argument("--path", help="Scan a single .md file (skips the duplication pass).")
    args = ap.parse_args()

    if args.path:
        if not os.path.isfile(args.path):
            print(json.dumps({"error": f"No file at {args.path}"}), file=sys.stderr)
            sys.exit(1)
        root = args.root or os.path.dirname(os.path.abspath(args.path)) or "."
        index = build_file_index(root)
        _, _, info = analyse_file(args.path, root, index)
        print(json.dumps({"scan_root": root, "files": [info],
                          "_note": "FACTS and CANDIDATES only. Verdicts are the model's job."},
                         indent=2))
        return

    root = args.root or auto_detect_root()
    targets = find_targets(root)
    if not targets:
        print(json.dumps({"error": f"No CLAUDE.md or .claude/rules/*.md found under {root}",
                          "hint": "Pass --root pointing at a Claude Code project, or --path for one file."}),
              file=sys.stderr)
        sys.exit(1)

    index = build_file_index(root)
    files_text, infos = {}, []
    for t in targets:
        rel, text, info = analyse_file(t, root, index)
        files_text[rel] = text
        infos.append(info)

    report = {
        "scan_root": root,
        "files_found": len(infos),
        "total_lines": sum(i["line_count"] for i in infos),
        "files": infos,
        "duplication_candidates": duplicate_candidates(files_text),
        "_note": "FACTS and CANDIDATES only. All verdicts are the model's job.",
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
