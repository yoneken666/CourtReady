"""
caseanalyzer.py  –  CourtReady Legal Analysis Engine (v3)
==========================================================
Architecture:
  • Knowledge base lives in knowledge_base.py (imported here).
  • Simple keyword-overlap retrieval selects the TOP 10 most relevant
    provisions from the category KB before any LLM call — the full KB
    is never sent to Gemini.
  • Gemini receives only the 10 retrieved chunks and produces the full
    legal analysis in a single API call.
  • In-memory response cache keyed on (category, SHA-256 of description)
    for sub-second repeat queries.
  • Falls back through MODEL_HIERARCHY if any model is unavailable.
"""

import os
import re
import json
import hashlib

import google.generativeai as genai
from dotenv import load_dotenv

from knowledge_base import CATEGORY_KB, VALID_CATEGORIES

load_dotenv()

# ── Gemini Configuration ─────────────────────────────────────────────────────
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("CRITICAL WARNING: GEMINI_API_KEY not found in environment variables.")
else:
    genai.configure(api_key=api_key)

MODEL_HIERARCHY = [
    "gemini-flash-lite-latest",
    "gemma-3-4b-it",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-pro-latest",
]

# ── In-Memory Response Cache ──────────────────────────────────────────────────
_RESPONSE_CACHE: dict = {}

# ── Stop-words (shared with casematching.py pattern) ─────────────────────────
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "not", "no", "nor", "so",
    "as", "if", "then", "than", "that", "this", "these", "those", "it",
    "its", "he", "she", "they", "we", "you", "i", "me", "him", "her",
    "us", "them", "his", "their", "our", "your", "my", "which", "who",
    "whom", "what", "when", "where", "how", "all", "both", "each",
    "more", "most", "other", "some", "such", "any", "also", "into",
    "through", "during", "before", "after", "above", "below", "between",
    "out", "off", "over", "under", "again", "further", "once", "only",
    "own", "same", "too", "very", "just", "about", "up", "down", "there",
    "here", "s", "t", "can", "don", "said", "court", "shall", "section",
    "order", "rule", "act", "person", "case", "suit", "property", "any",
    "thereof", "therein", "herein", "aforesaid", "where", "pursuant",
}

TOP_K = 10  # number of KB chunks sent to the LLM


def _cache_key(category: str, description: str) -> str:
    digest = hashlib.sha256(description.strip().lower().encode()).hexdigest()
    return f"{category}::{digest}"


# ════════════════════════════════════════════════════════════════════════════
# Simple keyword retrieval  (the "RAG" step)
# ════════════════════════════════════════════════════════════════════════════

def _tokenise(text: str) -> set:
    """Return a set of meaningful lowercase tokens from text."""
    tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return {t for t in tokens if t not in _STOPWORDS}


def _score(query_tokens: set, entry: dict) -> float:
    """
    Score a KB entry against the query using a weighted word-overlap metric:
      - Recall component  : what fraction of query terms appear in the chunk
      - Jaccard component : overlap / union (penalises very long chunks)

    Weighting: 0.65 recall + 0.35 Jaccard
    This gives more credit to chunks that cover the user's specific terms
    while still rewarding tight topical focus.
    """
    doc_tokens = _tokenise(entry["source_title"] + " " + entry["source_text"])
    if not query_tokens or not doc_tokens:
        return 0.0
    intersection = query_tokens & doc_tokens
    if not intersection:
        return 0.0
    recall  = len(intersection) / len(query_tokens)
    jaccard = len(intersection) / len(query_tokens | doc_tokens)
    return 0.65 * recall + 0.35 * jaccard


def retrieve_top_k(description: str, category: str, k: int = TOP_K) -> list:
    """
    Return the top-k most relevant KB entries for the given description
    and dispute category.  Always returns at least min(k, len(kb)) entries.
    """
    kb = CATEGORY_KB[category]
    query_tokens = _tokenise(description)

    scored = [(entry, _score(query_tokens, entry)) for entry in kb]
    scored.sort(key=lambda x: x[1], reverse=True)

    top = [entry for entry, _ in scored[:k]]
    print(f"[retrieval] Selected {len(top)} / {len(kb)} chunks for [{category}]")
    return top


# ════════════════════════════════════════════════════════════════════════════
# CORE ENGINE
# ════════════════════════════════════════════════════════════════════════════

class LegalAIEngine:
    """
    Lightweight engine: simple keyword retrieval + Gemini API.
    No heavy models, no disk caches, near-instant startup.
    """

    def __init__(self):
        total = sum(len(v) for v in CATEGORY_KB.values())
        print(
            f"--- Initialising Legal AI Engine ---\n"
            f"  Knowledge base: {total} total provisions across "
            f"{len(CATEGORY_KB)} categories (loaded from knowledge_base.py)\n"
            f"  Retrieval: top-{TOP_K} keyword-matched chunks sent to LLM"
        )
        if not api_key:
            print("  ⚠️  Gemini API key missing – analysis will fail.")
        else:
            print("  ✅  Gemini API configured.")

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze_case(self, description: str, category: str) -> dict:
        """
        Main entry point called by FastAPI.
        Returns the standard analysis dict expected by the frontend.
        """
        if category not in VALID_CATEGORIES:
            return self._rejection_response(
                f"Unknown category '{category}'. "
                f"Please choose from: {', '.join(sorted(VALID_CATEGORIES))}."
            )

        if not description or len(description.strip()) < 20:
            return self._rejection_response(
                "Please provide a more detailed description of your case "
                "(at least a few sentences)."
            )

        # Check in-memory cache
        key = _cache_key(category, description)
        if key in _RESPONSE_CACHE:
            print(f"⚡ Cache hit for [{category}]")
            return _RESPONSE_CACHE[key]

        # ── Step 1: retrieve top-k relevant chunks (the RAG step) ──────────
        retrieved_chunks = retrieve_top_k(description, category, k=TOP_K)

        # ── Step 2: call LLM with only those chunks ─────────────────────────
        result = self._generate_analysis(category, description, retrieved_chunks)

        if result is None:
            return self._error_response(
                "All Gemini models failed. Please try again later."
            )

        _RESPONSE_CACHE[key] = result
        return result

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _build_prompt(
        self, category: str, description: str, chunks: list
    ) -> str:
        """
        Build the Gemini prompt from the pre-retrieved chunks only.
        The LLM never sees the full KB — just these TOP_K entries.
        """
        context_block = ""
        for i, entry in enumerate(chunks):
            context_block += (
                f"[{i}] SOURCE: {entry['source_title']}\n"
                f"    TEXT: {entry['source_text']}\n\n"
            )

        return f"""You are a Senior Pakistani Legal Advocate specialising in civil litigation.

DISPUTE CATEGORY: {category}

CASE DESCRIPTION:
\"\"\"{description}\"\"\"

RELEVANT LEGAL PROVISIONS ({len(chunks)} most applicable provisions pre-selected):
{context_block}

TASK:
1. Using ONLY the provisions listed above, provide a professional legal analysis of the case.
2. Identify which 3 provisions are most directly applicable and reference them explicitly.
3. Return ONLY a single valid JSON object — no preamble, no markdown fences.

STRICT JSON FORMAT:
{{
    "selected_law_indices": [<index_a>, <index_b>, <index_c>],
    "case_summary": "One paragraph professional summary of the case and its legal standing.",
    "key_facts": ["Key legal fact 1", "Key legal fact 2", "Key legal fact 3"],
    "validity_status": "Strong|Moderate|Weak",
    "validity_assessment": {{
        "risk_level": "Low|Moderate|High",
        "advice_summary": "Full legal analysis in paragraphs only (no bullet lists). Apply the selected provisions directly to the facts. Minimum 3 paragraphs.",
        "simplified_advice": "Explain the situation in plain simple language a non-lawyer can understand in 2–3 sentences."
    }}
}}

INSTRUCTIONS:
- `validity_status` reflects how well-grounded the claim is in Pakistani law.
- `risk_level` reflects litigation risk for the claimant (Low = favourable, High = difficult).
- `advice_summary` must reference the specific sections/Acts used.
- Do NOT include any text outside the JSON object.
"""

    def _generate_analysis(
        self, category: str, description: str, chunks: list
    ) -> dict | None:
        """
        Call Gemini models in order using the pre-retrieved chunks.
        Returns the parsed result dict or None if all models fail.
        """
        prompt = self._build_prompt(category, description, chunks)

        for model_name in MODEL_HIERARCHY:
            try:
                print(f"🔍 Calling {model_name} for [{category}] "
                      f"({len(chunks)} chunks in context)…")
                model    = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                raw      = response.text.strip()

                # Strip accidental markdown fences
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                raw = raw.strip()

                parsed = json.loads(raw)
                result = self._build_response(parsed, chunks, category)
                print(f"✅ Analysis generated successfully using {model_name}.")
                return result

            except json.JSONDecodeError as e:
                print(f"⚠️  JSON parse error from {model_name}: {e}")
                continue
            except Exception as e:
                print(f"⚠️  Error with {model_name}: {e} – trying next model…")
                continue

        print("❌ All models in hierarchy failed.")
        return None

    def _build_response(
        self, parsed: dict, chunks: list, category: str
    ) -> dict:
        """
        Combine the LLM's JSON with the actual KB entries it selected.
        Produces the final dict returned to the frontend.
        """
        indices = parsed.get("selected_law_indices", [])
        valid_indices = [
            i for i in indices
            if isinstance(i, int) and 0 <= i < len(chunks)
        ]

        # Fallback: first 3 entries if model returned bad indices
        if not valid_indices:
            valid_indices = list(range(min(3, len(chunks))))

        relevant_laws = []
        for rank, idx in enumerate(valid_indices[:3]):
            entry = chunks[idx]
            relevant_laws.append({
                "source_title":    entry["source_title"],
                "source_text":     self._truncate(entry["source_text"]),
                "relevance_score": round(1.0 - rank * 0.05, 2),  # 1.0, 0.95, 0.90
                "source_category": entry["source_category"],
            })

        return {
            "case_summary":    parsed.get("case_summary", "Summary unavailable."),
            "key_facts":       parsed.get("key_facts", []),
            "relevant_laws":   relevant_laws,
            "validity_status": parsed.get("validity_status", "Uncertain"),
            "validity_assessment": parsed.get(
                "validity_assessment",
                {
                    "risk_level":        "Unknown",
                    "advice_summary":    "Analysis unavailable.",
                    "simplified_advice": "Please try again.",
                },
            ),
        }

    @staticmethod
    def _truncate(text: str, max_len: int = 220) -> str:
        """Truncate source_text for frontend display."""
        text = text.replace("\n", " ").strip()
        if len(text) <= max_len:
            return text
        cut = text.rfind(" ", 0, max_len)
        return text[: cut if cut > 0 else max_len] + "…"

    @staticmethod
    def _rejection_response(reason: str) -> dict:
        return {
            "case_summary": "Case Rejected",
            "key_facts": [],
            "relevant_laws": [],
            "validity_status": "REJECTED",
            "validity_assessment": {
                "risk_level":        "N/A",
                "advice_summary":    reason,
                "simplified_advice": reason,
            },
        }

    @staticmethod
    def _error_response(msg: str) -> dict:
        return {
            "case_summary": f"System Alert: {msg}",
            "key_facts": [],
            "relevant_laws": [],
            "validity_status": "ERROR",
            "validity_assessment": {
                "risk_level":        "Unknown",
                "advice_summary":    "The AI analysis service is temporarily unavailable.",
                "simplified_advice": "Please try again in a moment.",
            },
        }


# ── Singleton instance (imported by main.py) ─────────────────────────────────
legal_engine = LegalAIEngine()
