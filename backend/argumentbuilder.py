"""
argumentbuilder.py
──────────────────
Takes the full output of case analysis + case matching and uses Gemini
to produce the top 10 strongest arguments the user can make in court.
"""

import json
import os

import google.generativeai as genai

# Configure API key (same pattern as casematching.py)
_API_KEY = os.getenv("GEMINI_API_KEY", "")
if _API_KEY:
    genai.configure(api_key=_API_KEY)

MODEL_HIERARCHY = [
    "gemini-flash-lite-latest",
    "gemma-3-4b-it"
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-pro",
]


def _build_prompt(case_description: str, analysis: dict, matching: dict) -> str:
    """Construct the Gemini prompt from both upstream results."""

    # ── Case Analyzer summary ──────────────────────────────────────────────
    validity       = analysis.get("validity_status", "UNKNOWN")
    case_category  = analysis.get("case_category", "Unknown Category")
    legal_issues   = analysis.get("legal_issues", [])
    simplified     = analysis.get("simplified_advice", "")
    detailed       = analysis.get("detailed_advice", "")
    relevant_laws  = analysis.get("relevant_laws", [])

    issues_block = "\n".join(f"  - {i}" for i in legal_issues) if legal_issues else "  (none identified)"

    laws_block = ""
    for law in relevant_laws[:6]:          # cap at 6 to stay within context
        title = law.get("source_title", "")
        text  = law.get("source_text", "")[:400]
        score = law.get("relevance_score", 0)
        laws_block += f"\n  [{score:.0%}] {title}\n    \"{text}\"\n"
    if not laws_block:
        laws_block = "  (no specific provisions retrieved)"

    # ── Case Matching summary ──────────────────────────────────────────────
    top_matches    = matching.get("top_matches", [])
    matches_block  = ""
    for m in top_matches:
        label       = m.get("case_label", "Unknown Case")
        relevance   = m.get("relevance", "neutral")
        explanation = m.get("explanation", "")
        matches_block += (
            f"\n  Case: {label}\n"
            f"  Relevance to user: {relevance.upper()}\n"
            f"  Summary: {explanation}\n"
        )
    if not matches_block:
        matches_block = "  (no past cases matched)"

    prompt = f"""
You are a senior Pakistani family-law advocate preparing your client for a court hearing.
Below you have everything gathered so far about the client's situation.

═══════════════════════════════════════════════════════════════
USER'S CASE DESCRIPTION
═══════════════════════════════════════════════════════════════
{case_description}

═══════════════════════════════════════════════════════════════
CASE ANALYSIS RESULT  (Validity: {validity} | Category: {case_category})
═══════════════════════════════════════════════════════════════
Legal Issues Identified:
{issues_block}

Relevant Pakistani Laws / CPC Provisions:
{laws_block}

Simplified Advice:
{simplified}

Detailed Advice:
{detailed}

═══════════════════════════════════════════════════════════════
MATCHED PAST COURT CASES (Precedents)
═══════════════════════════════════════════════════════════════
{matches_block}

═══════════════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════════════
Using EVERYTHING above, produce exactly 10 arguments the user should make
when standing before the judge.

Rules:
1. Each argument must be directly actionable — something the user can *say
   or present* in the courtroom.
2. Rank them from strongest (#1) to least strong (#10).
3. Where a matched past case SUPPORTS the user, cite it explicitly in the
   relevant argument(s).
4. Where a matched past case OPPOSES the user, craft a counter-argument that
   distinguishes it.
5. Ground every argument in Pakistani law / CPC where applicable.
6. Write in plain, confident language a layperson can read aloud to a judge.
7. Each argument must have:
   - "rank": integer 1–10
   - "title": short bold headline (≤ 12 words)
   - "argument": the full argument text (2–5 sentences)
   - "legal_basis": the specific law, section, or case name backing it
   - "strength": "Strong" | "Moderate" | "Supplementary"

Return ONLY valid JSON — no markdown fences, no extra text.

JSON FORMAT:
[
  {{
    "rank": 1,
    "title": "Short headline here",
    "argument": "Full courtroom argument text here.",
    "legal_basis": "CPC Section XX / <Case Name>",
    "strength": "Strong"
  }},
  ...
]
"""
    return prompt.strip()


def generate_arguments(
    case_description: str,
    analysis_result: dict,
    matching_result: dict,
) -> dict:
    """
    Entry point called by main.py.
    Returns:
      {
        "arguments": [ { rank, title, argument, legal_basis, strength }, ... ],
        "message": str
      }
    """
    if not _API_KEY:
        return {
            "arguments": [],
            "message": "Gemini API key not configured. Please set GEMINI_API_KEY.",
        }

    prompt = _build_prompt(case_description, analysis_result, matching_result)

    for model_name in MODEL_HIERARCHY:
        try:
            print(f"[argumentbuilder] Generating arguments using {model_name}…")
            model    = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text     = response.text.strip()

            # Strip markdown fences
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            parsed = json.loads(text.strip())

            if not isinstance(parsed, list):
                raise ValueError("Response is not a JSON array.")

            # Ensure exactly 10 items, sorted by rank
            parsed = sorted(parsed, key=lambda x: x.get("rank", 99))[:10]

            return {
                "arguments": parsed,
                "message":   f"Generated {len(parsed)} court-ready arguments.",
            }

        except Exception as exc:
            print(f"[argumentbuilder] {model_name} failed: {exc}")
            continue

    return {
        "arguments": [],
        "message":   "All Gemini models failed. Please try again later.",
    }
