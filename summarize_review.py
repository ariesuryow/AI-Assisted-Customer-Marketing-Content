"""
Summarise the human review into numbers for the README.

Usage:
  python summarize_review.py review_done.csv

Rules:
- Only rows with a human_decision count as "reviewed". Empty rows are ignored.
- Empty final_* columns mean the original AI text was used unchanged.
- Works with comma- or semicolon-separated CSV (Excel in some locales saves with ';').
"""
import sys
from pathlib import Path

import pandas as pd

SCORES = ["score_segment_fit", "score_tone", "score_cta", "score_factual_safety", "score_channel_format"]
FINALS = ["final_subject", "final_body", "final_cta"]


def pct(n, total):
    return f"{n / total * 100:.0f}%" if total else "n/a"


def main(path):
    df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig").fillna("")
    df.columns = [c.strip() for c in df.columns]
    df["human_decision"] = df["human_decision"].astype(str).str.strip().str.lower()
    for c in SCORES:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    total = len(df)
    rev = df[df["human_decision"] != ""].copy()
    n = len(rev)
    if n == 0:
        print("No reviewed rows found (human_decision is empty everywhere).")
        return

    out = []
    out.append("## Results\n")
    out.append(f"I reviewed **{n} of {total}** generated items ({pct(n, total)}). Unreviewed items are excluded from all figures below.\n")

    out.append("### Coverage of the reviewed sample\n")
    for col in ["segment", "channel", "angle"]:
        counts = rev[col].value_counts().to_dict()
        out.append(f"- {col}: " + ", ".join(f"{k} ({v})" for k, v in counts.items()))
    out.append("")

    out.append("### Average human scores (1-5)\n")
    out.append("| Criterion | Average | Rated items |\n|---|---|---|")
    for c in SCORES:
        s = rev[c].dropna()
        out.append(f"| {c.replace('score_', '').replace('_', ' ')} | {s.mean():.2f} | {len(s)} |" if len(s) else f"| {c} | n/a | 0 |")
    out.append("")

    out.append("### Review decisions\n")
    out.append("| Decision | Count | Share |\n|---|---|---|")
    for k, v in rev["human_decision"].value_counts().items():
        out.append(f"| {k} | {v} | {pct(v, n)} |")
    out.append("")

    flagged = (rev["auto_flags"].astype(str).str.strip() != "")
    out.append("### Automatic checks\n")
    out.append(f"- Items flagged by automatic checks: {flagged.sum()} of {n} reviewed ({pct(flagged.sum(), n)})")
    flag_counts = (
        rev.loc[flagged, "auto_flags"].astype(str).str.split(";").explode().str.strip().value_counts()
    )
    for k, v in flag_counts.items():
        out.append(f"  - {k}: {v}")
    out.append("")

    out.append("### What humans edited\n")
    out.append("| Field edited | Items | Share of reviewed |\n|---|---|---|")
    for c in FINALS:
        if c in rev.columns:
            k = (rev[c].astype(str).str.strip() != "").sum()
            out.append(f"| {c.replace('final_', '')} | {k} | {pct(k, n)} |")
    out.append("")

    out.append("### Average scores by segment\n")
    by_seg = rev.groupby("segment")[SCORES].mean().round(2)
    by_seg.insert(0, "n", rev.groupby("segment").size())
    try:
        out.append(by_seg.reset_index().to_markdown(index=False))  # needs: pip install tabulate
    except ImportError:
        out.append("```\n" + by_seg.to_string() + "\n```")
    out.append("")

    text = "\n".join(out)
    print(text)
    Path("review_summary.md").write_text(text, encoding="utf-8")
    print("\nSaved to review_summary.md")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python summarize_review.py <review.csv>")
    main(sys.argv[1])
