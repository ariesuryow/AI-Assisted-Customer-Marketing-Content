"""
Segment profile -> prompt template -> LLM -> automatic checks -> CSV for human review.

Usage:
  python generate_content.py --dry-run     # no API call, writes prompts_preview.txt
  python generate_content.py               # needs ANTHROPIC_API_KEY (pip install anthropic)

Only segment-level information is sent to the LLM. No Customer ID, no individual data.
"""
import argparse
import csv
import json
import os
import re
from pathlib import Path

MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")  # change to any model you have access to
HERE = Path(__file__).parent

CHANNELS = {
    "email": "Subject line (max 60 characters) and body of 60-90 words.",
    "instagram_caption": "Caption of 25-45 words with at most 3 hashtags. subject must be empty.",
    "whatsapp_broadcast": "Short message of 30-50 words, conversational, at most 1 emoji. subject must be empty.",
    "push_notification": "Title (max 40 characters) in subject, body max 90 characters.",
}

ANGLES = {
    "christmas_gifting": "Christmas gifting season: gift ideas, hosting, festive home decor.",
    "new_year_refresh": "New Year refresh: tidy, restock, start the year with fresh ideas.",
}

SYSTEM_PROMPT = """You are a marketing copywriter assistant for an online retailer.
Rules you must follow:
1. Use ONLY the offers listed under APPROVED OFFERS. Never invent discounts, prices, percentages, deadlines, stock levels or free gifts.
2. If an offer says "value set by marketing", refer to it generically (for example "a special discount") and do not state a number.
3. Do not claim anything about the customer's personal data or purchase history beyond the segment summary provided.
4. Do not use pressure tactics, false urgency or guilt.
5. Write in the requested language and tone.
6. Return ONLY valid JSON with keys: subject, body, cta. No markdown, no explanation."""

USER_TEMPLATE = """SEGMENT: {name}
Behaviour: recency = {recency}, frequency = {frequency}, spend = {monetary}
Marketing goal: {goal}
Tone: {tone}
Brand voice: {voice}
Language: {language}
Popular product themes for this segment: {products}
APPROVED OFFERS: {offers}

CHANNEL: {channel}. Format: {channel_format}
SEASONAL ANGLE: {angle}

Write one piece of content. Return JSON: {{"subject": "...", "body": "...", "cta": "..."}}"""

FORBIDDEN = ["guarantee", "guaranteed", "100%", "best price", "last chance", "only today", "act now"]


def load_profiles():
    profiles = json.loads((HERE / "segment_profiles.json").read_text())
    stats_path = HERE / "segment_stats.json"
    stats = json.loads(stats_path.read_text()) if stats_path.exists() else {}
    return profiles, stats


def build_prompt(name, seg, ctx, stats, channel, angle):
    st = stats.get(name, {})
    products = ", ".join(st.get("top_products", [])) or "not provided (use general giftware and home decor themes)"
    return USER_TEMPLATE.format(
        name=name, recency=seg["recency"], frequency=seg["frequency"], monetary=seg["monetary"],
        goal=seg["goal"], tone=seg["tone"], voice=ctx["voice"], language=ctx["language"],
        products=products, offers="; ".join(seg["approved_offers"]),
        channel=channel, channel_format=CHANNELS[channel], angle=ANGLES[angle],
    )


def call_llm(user_prompt):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL, max_tokens=600, system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = msg.content[0].text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    return json.loads(text)


def auto_checks(channel, out):
    """Cheap rule-based guardrails. They do NOT replace human review."""
    flags = []
    subject, body, cta = out.get("subject", ""), out.get("body", ""), out.get("cta", "")
    full = f"{subject} {body} {cta}".lower()
    words = len(body.split())
    if not cta.strip():
        flags.append("missing_cta")
    if re.search(r"[%£$]|\d+\s?%", full):
        flags.append("contains_number_or_price")
    if any(p in full for p in FORBIDDEN):
        flags.append("forbidden_phrase")
    if re.search(r"\b\d{5}\b", full):
        flags.append("possible_customer_id")
    if channel == "email" and not (50 <= words <= 100):
        flags.append("email_length")
    if channel == "email" and len(subject) > 60:
        flags.append("subject_too_long")
    if channel == "push_notification" and (len(body) > 90 or len(subject) > 40):
        flags.append("push_too_long")
    return flags


MANUAL_TEMPLATE = """{system}

{profile}

Create content for ALL of the following combinations (channel / seasonal angle):
{combos}

Return ONLY a JSON array with {n} objects. Each object must have exactly these keys:
"segment", "channel", "angle", "subject", "body", "cta".
Use the segment, channel and angle names exactly as written above. No markdown, no explanation."""


def build_manual_prompt(name, seg, ctx, stats):
    st = stats.get(name, {})
    products = ", ".join(st.get("top_products", [])) or "not provided (use general giftware and home decor themes)"
    profile = (
        f"SEGMENT: {name}\n"
        f"Behaviour: recency = {seg['recency']}, frequency = {seg['frequency']}, spend = {seg['monetary']}\n"
        f"Marketing goal: {seg['goal']}\nTone: {seg['tone']}\n"
        f"Brand voice: {ctx['voice']}\nLanguage: {ctx['language']}\n"
        f"Popular product themes for this segment: {products}\n"
        f"APPROVED OFFERS: {'; '.join(seg['approved_offers'])}"
    )
    combos = "\n".join(
        f"- channel={c} ({CHANNELS[c]}) | angle={a} ({ANGLES[a]})"
        for c in CHANNELS for a in ANGLES
    )
    return MANUAL_TEMPLATE.format(
        system=SYSTEM_PROMPT.replace("Return ONLY valid JSON with keys: subject, body, cta. No markdown, no explanation.",
                                     "Return only the JSON array requested below."),
        profile=profile, combos=combos, n=len(CHANNELS) * len(ANGLES),
    )


def parse_json_arrays(text):
    """Find every JSON array of objects in a text file (for pasted AI answers)."""
    dec, items, i = json.JSONDecoder(), [], 0
    while True:
        i = text.find("[", i)
        if i == -1:
            return items
        try:
            obj, end = dec.raw_decode(text[i:])
            if isinstance(obj, list):
                items.extend(o for o in obj if isinstance(o, dict))
            i += end
        except json.JSONDecodeError:
            i += 1


def make_row(segment, channel, angle, out):
    return {
        "segment": segment, "channel": channel, "angle": angle,
        "subject": out.get("subject", ""), "body": out.get("body", ""), "cta": out.get("cta", ""),
        "auto_flags": ";".join(auto_checks(channel, out)),
        "score_segment_fit": "", "score_tone": "", "score_cta": "",
        "score_factual_safety": "", "score_channel_format": "",
        "human_decision": "", "reviewer_notes": "",
    }


def write_review_csv(rows, name="generated_content_for_review.csv"):
    out_path = HERE / name
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig so Excel reads it correctly
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    flagged = sum(1 for r in rows if r["auto_flags"])
    print(f"Wrote {len(rows)} items to {out_path.name}; {flagged} flagged by automatic checks.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="write one prompt per segment x channel x angle")
    ap.add_argument("--manual", action="store_true", help="write 1 combined prompt per segment to manual_prompts.txt")
    ap.add_argument("--import-responses", metavar="FILE", help="parse pasted AI answers (JSON arrays) into the review CSV")
    ap.add_argument("--segments", nargs="*", help="limit to some segments, e.g. WHALES QUIET")
    args = ap.parse_args()

    profiles, stats = load_profiles()
    ctx, segs = profiles["brand_context"], profiles["segments"]

    if args.manual:
        parts = []
        for name, seg in segs.items():
            if args.segments and name not in args.segments:
                continue
            parts.append(f"{'=' * 20} PROMPT FOR SEGMENT: {name} {'=' * 20}\n{build_manual_prompt(name, seg, ctx, stats)}\n")
        (HERE / "manual_prompts.txt").write_text("\n".join(parts), encoding="utf-8")
        print(f"Wrote {len(parts)} prompts to manual_prompts.txt")
        return

    if args.import_responses:
        text = Path(args.import_responses).read_text(encoding="utf-8")
        rows, skipped = [], 0
        for o in parse_json_arrays(text):
            if o.get("channel") in CHANNELS and o.get("segment") in segs:
                rows.append(make_row(o["segment"], o["channel"], o.get("angle", ""), o))
            else:
                skipped += 1
        if not rows:
            print("No valid items found. Check that the answers are JSON arrays.")
            return
        write_review_csv(rows)
        if skipped:
            print(f"Skipped {skipped} items with unknown segment/channel names.")
        return

    dry = args.dry_run or not os.getenv("ANTHROPIC_API_KEY")
    if dry:
        print("Dry run: no API call. Prompts will be written to prompts_preview.txt")

    rows, previews = [], []
    for name, seg in segs.items():
        if args.segments and name not in args.segments:
            continue
        for channel in CHANNELS:
            for angle in ANGLES:
                prompt = build_prompt(name, seg, ctx, stats, channel, angle)
                if dry:
                    previews.append(f"=== {name} | {channel} | {angle} ===\n{prompt}\n")
                    continue
                rows.append(make_row(name, channel, angle, call_llm(prompt)))

    if dry:
        (HERE / "prompts_preview.txt").write_text(f"SYSTEM PROMPT:\n{SYSTEM_PROMPT}\n\n" + "\n".join(previews), encoding="utf-8")
        print(previews[0] if previews else "No prompts built.")
        return
    write_review_csv(rows)


if __name__ == "__main__":
    main()
