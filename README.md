# AI-Assisted Customer Marketing Content

**Background.** Customer segmentation helps businesses understand different customer behaviours. However, segmentation insights still need to be translated into actionable marketing communication.

**Objective.** To explore how generative AI can assist marketers in transforming data-driven customer segment insights into targeted marketing content, with human review and responsible-AI guardrails, across 8 customer segments, 4 channels (email, Instagram, WhatsApp, push) and 2 seasonal angles.

This project extends my earlier [Customer Segmentation (K-Means + RFM) on Online Retail II] project.

## Workflow

```
Online Retail II  ->  RFM + K-Means (8 segments)  ->  segment-level profile (no Customer ID)
   ->  prompt template + guardrails  ->  LLM  ->  automatic checks  ->  human review  ->  approved content
```

| Step | File | What it does |
|---|---|---|
| 1 | clustering notebook | Produces 8 segments (4 main + 4 outlier) |
| 2 | `export_segment_stats.py` | Exports segment-level aggregates only, small segments suppressed |
| 3 | `segment_profiles.json` | Segment goal, tone, and the list of **approved offers** |
| 4 | `generate_content.py` | Builds prompts, calls the LLM, runs rule-based checks, writes a review CSV |
| 5 | `marketer_playbook.md` | One-page guide for non-technical marketers |

## Segments

| Segment | Behaviour | Marketing goal |
|---|---|---|
| WHALES | Recent, very high frequency and spend | Recognise and retain top customers |
| BONUS | Recent, high frequency and spend | Reward loyalty |
| PRESERVE | Recent, high frequency and spend | Maintain repeat purchasing |
| STEADY | Recent, frequent, smaller orders | Increase basket size |
| GROWTH | Recent, low frequency and spend | Build engagement |
| CASUALS | Recent, low frequency and spend | Stay top of mind |
| RECONNECT | Not recent, low frequency and spend | Reactivate |
| QUIET | Long ago, lowest frequency and spend | Win back |

## Responsible AI design

- **Data minimisation:** only segment-level summaries go to the LLM. No Customer ID, no individual transactions. Segments under 20 customers are suppressed.
- **No invented offers:** the model may only use offers from an approved list. Discount values are set by marketing, never by the model.
- **Automatic checks:** flags numbers/prices, forbidden phrases (false urgency, guarantees), possible IDs, missing CTA, and length limits per channel.
- **Human in the loop:** nothing is "approved" automatically. Every item goes to a review CSV with a rubric and decision column.
- **Honest limits:** see below.

## Evaluation rubric (score 1-5, by a human reviewer)

| Criterion | Question |
|---|---|
| Segment fit | Does the message match the segment's behaviour and goal? |
| Tone | Does it match brand voice and the segment's tone? |
| CTA clarity | Is there one clear next step? |
| Factual safety | No invented offers, claims or urgency? |
| Channel format | Right length and style for the channel? |

Report: average score per criterion, % of items flagged by automatic checks, % approved without edits, and the most common edit types.

## Results

I reviewed **64 of 64** generated items (100%). Unreviewed items are excluded from all figures below.

### Coverage of the reviewed sample

- segment: WHALES (8), BONUS (8), PRESERVE (8), STEADY (8), GROWTH (8), CASUALS (8), RECONNECT (8), QUIET (8)
- channel: email (16), instagram_caption (16), whatsapp_broadcast (16), push_notification (16)
- angle: christmas_gifting (32), new_year_refresh (32)

### Average human scores (1-5)

| Criterion | Average | Rated items |
|---|---|---|
| segment fit | 4.22 | 64 |
| tone | 4.25 | 64 |
| cta | 4.23 | 64 |
| factual safety | 4.23 | 64 |
| channel format | 4.20 | 64 |

### Review decisions

| Decision | Count | Share |
|---|---|---|
| approved | 46 | 72% |
| edit | 18 | 28% |

### Automatic checks

- Items flagged by automatic checks: 0 of 64 reviewed (0%)

### What humans edited

| Field edited | Items | Share of reviewed |
|---|---|---|
| subject | 6 | 9% |
| body | 3 | 5% |
| cta | 8 | 12% |

### Average scores by segment

```
           n  score_segment_fit  score_tone  score_cta  score_factual_safety  score_channel_format
segment                                                                                           
BONUS      8               4.25        4.38       4.25                  4.12                  4.38
CASUALS    8               4.00        4.50       4.12                  4.25                  4.25
GROWTH     8               4.38        4.12       4.38                  4.38                  4.25
PRESERVE   8               4.38        4.12       4.38                  4.12                  4.12
QUIET      8               4.12        4.12       4.00                  4.12                  4.00
RECONNECT  8               4.12        4.25       4.25                  4.38                  4.50
STEADY     8               4.25        4.38       4.25                  4.25                  4.12
WHALES     8               4.25        4.12       4.25                  4.25                  4.00
```

**Tool used:** 
CLAUDE free tier -- AI Development & Prompt Engineering, 
Gemini free tier -- AI Copywriting & Content Generation,
Human Revier -- Quality Control & Final Approval,
prompted manually with one prompt per segment (see `manual_prompts.txt`). 
Final review data is in `review_done.csv`.

### Interpretation

Average scores were uniformly high and close together across all five criteria (4.20-4.25 out of 5). With only 8 items per segment and a single reviewer, I do not read the small differences between criteria or segments as meaningful.

The more informative result is *what* was edited. 18 of 64 items (28%) were edited, and 11 of those 18 were a single wording preference: replacing "festive" with "Christmas" in subject lines and CTAs. That is a matter of taste, not an AI error. The remaining 7 items (11% of all items) needed substantive edits: 4 had text rewritten (a generic body, a caption's structure, CTA wording) and 3 were marked "too long" without a rewritten version recorded. In total, 4 of the 7 substantive edits cite length, even though every item passed the automatic length checks, which suggests the length limits in my prompts were too generous.

None of the 64 items was flagged by the rule-based checks, so the automatic checks did not predict which items a human wanted to change. They are a safety net for obvious problems (invented prices, missing CTA), not a substitute for review.

### Examples of human edits

**1. Generic body, tightened (WHALES, email, New Year angle)**
- AI: "Thank you for your continued loyalty to our brand. To help you start the year with fresh ideas, enjoy early access to our latest home decor and restock essentials. Your VIP membership perks and dedicated account contact are ready to assist with any personal requests. We have also included a surprise gift with order as a special thank-you. Explore the new arrivals today and elevate your living space for the new year."
- Edited: "Start the new year fresh with early access to our latest home decor and restock essentials. Designed to help you tidy and elevate your space, this collection is available to you first."
- Why: the AI stacked every approved offer into one message, which made it long and generic. I kept one clear benefit (early access) and a single idea.

**2. CTA matched to the channel (WHALES, Instagram caption, New Year angle)**
- AI: "Shop new arrivals in bio"
- Edited: "Tap link in bio to shop"
- Why: Instagram captions cannot hold clickable links, so the CTA should say what the reader actually does: tap the link in the bio.

**3. Wording preference, not an AI error (11 items across 7 segments)**
- AI: "Explore Festive Ideas" / "Warm Festive Ideas & A Win-Back Offer"
- Edited: "Explore Christmas Ideas" / "Warm Christmas Ideas & A Win-Back Offer"
- Why: for a Christmas gifting angle, I prefer the more specific "Christmas" over the vaguer "festive". This is a personal editorial choice, and in a real team it would be decided by the brand guidelines.

## Limitations (state these in your write-up)

- The dataset has no campaign response data, so this project **does not measure conversion or revenue impact**. It evaluates content quality and fit. A/B testing is the recommended next step.
- Review was done by a single person who also designed the prompts, so scores may be biased and there is no inter-reviewer agreement to compare against.
- Segments are behavioural (RFM) only, with no demographics or preferences.
- The data is a UK retailer from 2009-2011, so content is illustrative, not production-ready.
- Tone and brand voice per segment are design assumptions, not derived from the data.
- LLM output can be generic, inaccurate or biased, which is why review is mandatory.
- Workflow time savings, if mentioned, must be labelled as estimates unless you time it yourself.

## How to run

Prerequisite: `segment_stats.json` exported from the clustering notebook (see `export_segment_stats.py`).

**Option A: with an LLM API (automated)**
```bash
pip install anthropic
export ANTHROPIC_API_KEY=...             # Windows PowerShell: $env:ANTHROPIC_API_KEY="..."
python generate_content.py --segments WHALES   # test with one segment first
python generate_content.py                     # all segments -> generated_content_for_review.csv
```

**Option B: with any chat AI, no API key (manual)**
```bash
python generate_content.py --manual            # writes manual_prompts.txt (1 prompt per segment)
```
1. Paste one segment prompt into the chat AI of your choice (note which tool and model you used).
2. Paste each AI answer (a JSON array) into `manual_responses.txt`.
3. Build the review CSV with automatic checks:
```bash
python generate_content.py --import-responses manual_responses.txt
```

Both options end in the same review CSV. Scoring and approval are done by a human.

## Ideas to extend

1. A small Streamlit or Gradio app so marketers pick segment, channel and angle.
2. Compare 2 prompt versions (basic vs. with guardrails) on the same rubric.
3. LLM-as-judge as a second reviewer, compared with your own scores.
4. Bahasa Indonesia version of the prompts.
