#!/usr/bin/env python3
"""
scan.py — rule checks for a coded dataset.

Runs every check against every row. Reports what it finds and exits
non-zero if anything turned up.

This is the complement to a sampling audit, not a replacement for it.
A sample estimates a rate; these checks find defects that cluster
(one file format, one document type, one code added late) and that a
random sample is therefore least likely to hit.

Usage:
    python scan.py data.csv
    python scan.py data.csv --codes codes.txt
"""

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict

# ---------------------------------------------------------------------------
# CONFIG — edit this to match your dataset. Nothing below needs changing.
# ---------------------------------------------------------------------------

CONFIG = {
    # Column holding the unique unit id.
    "id_column": "id",

    # Columns holding verbatim quotations from the source documents.
    "quote_columns": ["claim", "evidence"],

    # Characters that must never appear inside a quotation. A field
    # delimiter here means the extraction ran past a table cell boundary
    # and absorbed a neighbouring cell.
    "forbidden_in_quotes": ["|", "\t"],

    # Column holding the category code, checked against the code list file.
    "code_column": "code",

    # Categorical columns and their permitted values. Anything else is
    # flagged — including a plausible-looking synonym.
    "categorical_columns": {
        "acknowledged": ["full", "partial", "none"],
        "outcome": ["adopted", "partly adopted", "not adopted",
                    "no traceable outcome", "n/a"],
    },

    # Values whose definition requires evidence: (column, value, evidence column).
    # "not adopted" means an explicit refusal was recorded, so the evidence
    # field cannot be empty. A value that asserts absence of evidence —
    # "no traceable outcome" — is deliberately not listed here.
    "requires_evidence": [
        ("outcome", "not adopted", "evidence"),
    ],

    # Combinations the coding scheme makes impossible:
    # ((col_a, val_a), (col_b, val_b))
    "impossible_pairs": [
        (("acknowledged", "none"), ("outcome", "adopted")),
        (("acknowledged", "none"), ("outcome", "partly adopted")),
    ],
}

TERMINAL = "。！？；.!?"
ENUM = re.compile(r'^[（(]?[一二三四五六七八九十百]+[）)、.]|^\d+[、.](?!\d)|^[（(]\d+[）)]')

# ---------------------------------------------------------------------------
# Checks. Each takes the rows and returns a list of (unit_id, message).
# ---------------------------------------------------------------------------


def check_quote_contamination(rows, codes):
    """A field delimiter inside a quotation means the extraction crossed a
    cell boundary. In a response table this can pull the NEXT unit's text
    into this unit's evidence, which inflates how responsive the record
    looks — the defect changes the finding, not just the formatting."""
    out = []
    for r in rows:
        for col in CONFIG["quote_columns"]:
            for ch in CONFIG["forbidden_in_quotes"]:
                if ch in r.get(col, ""):
                    out.append((r[CONFIG["id_column"]],
                                f"{col}: contains {ch!r}"))
    return out


def check_code_membership(rows, codes):
    """Every code must come from the fixed list. A code invented during
    coding means the scheme grew without the researcher deciding so."""
    col = CONFIG["code_column"]
    return [(r[CONFIG["id_column"]], f"{col}: {r.get(col, '')!r} not in code list")
            for r in rows if r.get(col, "").strip().lstrip("?") not in codes]


def check_empty_codes(rows, codes):
    """A code with zero units is either dead weight or — more usefully —
    a sign that units meant for it were never moved there."""
    used = Counter(r.get(CONFIG["code_column"], "").strip().lstrip("?") for r in rows)
    return [("—", f"code {c!r} has no units") for c in sorted(codes) if used[c] == 0]


def check_categorical_values(rows, codes):
    """Permitted values only. Catches silent drift such as 'Partially
    adopted' where the scheme says 'partly adopted'."""
    out = []
    for col, allowed in CONFIG["categorical_columns"].items():
        allow = {a.lower() for a in allowed}
        for r in rows:
            v = r.get(col, "").strip()
            if v.lower() not in allow:
                out.append((r[CONFIG["id_column"]], f"{col}: {v!r} not permitted"))
    return out


def check_required_evidence(rows, codes):
    """A value defined by the presence of evidence cannot be assigned
    without it. This is the check that catches a value doing double duty
    as 'refused' and 'no record either way'."""
    out = []
    for col, val, ev in CONFIG["requires_evidence"]:
        for r in rows:
            if r.get(col, "").strip().lower() == val.lower() and not r.get(ev, "").strip():
                out.append((r[CONFIG["id_column"]],
                            f"{col}={val!r} but {ev} is empty"))
    return out


def check_impossible_pairs(rows, codes):
    """Combinations the scheme rules out. One appearing means either a
    coding error or a gap in the scheme — both worth knowing."""
    out = []
    for (ca, va), (cb, vb) in CONFIG["impossible_pairs"]:
        for r in rows:
            if (r.get(ca, "").strip().lower() == va.lower()
                    and r.get(cb, "").strip().lower() == vb.lower()):
                out.append((r[CONFIG["id_column"]],
                            f"{ca}={va!r} with {cb}={vb!r}"))
    return out


def check_quote_boundaries(rows, codes):
    """A quotation that ends without terminal punctuation was probably cut
    short; one that begins with an enumeration marker probably starts at
    the wrong place. Both are extraction faults, not coding faults."""
    out = []
    for r in rows:
        for col in CONFIG["quote_columns"]:
            t = r.get(col, "").strip()
            if not t:
                continue
            if t[-1] not in TERMINAL:
                out.append((r[CONFIG["id_column"]], f"{col}: no terminal punctuation"))
            if ENUM.match(t):
                out.append((r[CONFIG["id_column"]], f"{col}: starts on an enumeration marker"))
    return out


def check_duplicates(rows, codes):
    """A repeated id breaks joins silently. Identical text under two ids
    usually means the same unit was extracted twice."""
    out = []
    ids = Counter(r[CONFIG["id_column"]] for r in rows)
    out += [("—", f"id {i!r} appears {n} times") for i, n in ids.items() if n > 1]

    seen = defaultdict(list)
    for r in rows:
        key = re.sub(r"\s+", "", r.get(CONFIG["quote_columns"][0], ""))
        if key:
            seen[key].append(r[CONFIG["id_column"]])
    out += [("—", f"identical text in units {v}") for v in seen.values() if len(v) > 1]
    return out


CHECKS = [
    ("quote contamination", check_quote_contamination),
    ("code membership", check_code_membership),
    ("empty codes", check_empty_codes),
    ("categorical values", check_categorical_values),
    ("required evidence", check_required_evidence),
    ("impossible pairs", check_impossible_pairs),
    ("quote boundaries", check_quote_boundaries),
    ("duplicates", check_duplicates),
]

# ---------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description="Rule checks for a coded dataset.")
    ap.add_argument("data", help="CSV of coded units")
    ap.add_argument("--codes", default="codes.txt",
                    help="one permitted code per line (default: codes.txt)")
    args = ap.parse_args()

    with open(args.data, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    try:
        with open(args.codes, encoding="utf-8") as f:
            codes = {ln.strip() for ln in f if ln.strip() and not ln.startswith("#")}
    except FileNotFoundError:
        print(f"code list not found: {args.codes}", file=sys.stderr)
        return 2

    print(f"{len(rows)} units, {len(codes)} permitted codes\n")

    total = 0
    for name, fn in CHECKS:
        found = fn(rows, codes)
        total += len(found)
        mark = "FAIL" if found else "ok"
        print(f"[{mark:>4}] {name}  ({len(found)})")
        for unit, msg in found:
            print(f"         {unit}: {msg}")

    pct = 100 * total / len(rows) if rows else 0
    print(f"\n{total} finding(s) across {len(rows)} units ({pct:.1f}%)")
    print("Every unit was checked. A sampling audit covers a fraction and\n"
          "is the only way to check the judgements these rules cannot express.")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
