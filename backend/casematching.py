"""
casematching.py
---------------
Case Matching Engine for CourtReady.

Pipeline:
  1. Load and extract text from every PDF in ./family_cases/
     -> Cached to family_cases_cache.json (skips PDF parsing on subsequent runs).
     -> Module-level variable keeps cases in memory for the server process lifetime.
  2. Extract a human-readable case identity (court, date, parties) from the text.
  3. Compute word-overlap similarity between each case and the user query.
  4. Take the top-5 highest-scoring cases.
  5. Call Gemini (same MODEL_HIERARCHY as processing.py) to contextually compare
     them and craft explanations. Always returns 1-3 results.
"""

import os
import re
import json
import hashlib
import pypdf
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ── Gemini setup (mirrors processing.py exactly) ─────────────────────────────
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("CRITICAL WARNING: GEMINI_API_KEY not found in environment variables.")
else:
    genai.configure(api_key=api_key)

MODEL_HIERARCHY = [
    'gemini-flash-lite-latest',
    'gemma-3-4b-it',
    'gemini-pro-latest',
    'gemini-2.5-flash-lite',
    'gemini-flash-latest',
]

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE_DIR        = os.path.dirname(__file__)
FAMILY_CASES_DIR = os.path.join(_BASE_DIR, "family_cases")
_CACHE_FILE      = os.path.join(_BASE_DIR, "family_cases_cache.json")

# ── Module-level in-memory store (lives for the whole server process) ─────────
_CASES_IN_MEMORY = None

# ── Stop-words ────────────────────────────────────────────────────────────────
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
    "here", "s", "t", "can", "don", "said", "plaintiff", "defendant",
    "court", "case", "order", "judge", "petitioner", "respondent",
    "appellant", "vs", "v", "honourable", "hon", "whereas", "hereby",
    "thereof", "therein", "herein", "aforesaid",
}


# ── Text utilities ────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_pdf_text(path: str) -> str:
    text = ""
    try:
        with open(path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + " "
    except Exception as exc:
        print(f"[casematching] Could not read {path}: {exc}")
    return _clean(text)


def _tokenise(text: str) -> list:
    """Return a sorted list of unique meaningful tokens."""
    tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return sorted({t for t in tokens if t not in _STOPWORDS})


def _similarity(query_tokens: set, doc_tokens: set) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    intersection = query_tokens & doc_tokens
    recall  = len(intersection) / len(query_tokens)
    jaccard = len(intersection) / len(query_tokens | doc_tokens)
    return round(0.6 * recall + 0.4 * jaccard, 4)


def _extract_case_identity(text: str) -> str:
    """
    Pull the first 800 characters of the case text — this almost always
    contains the court name, citation, parties, and year — and use it as
    the identity snippet passed to Gemini for labelling.
    """
    return text[:800].strip()


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _build_dir_fingerprint() -> str:
    if not os.path.isdir(FAMILY_CASES_DIR):
        return ""
    entries = sorted(
        (fname, os.path.getsize(os.path.join(FAMILY_CASES_DIR, fname)))
        for fname in os.listdir(FAMILY_CASES_DIR)
        if fname.lower().endswith(".pdf")
    )
    raw = json.dumps(entries, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _load_cache():
    if not os.path.exists(_CACHE_FILE):
        return None
    try:
        with open(_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("fingerprint") != _build_dir_fingerprint():
            print("[casematching] Cache is stale (files changed). Rebuilding...")
            return None
        cases = []
        for c in data["cases"]:
            c["tokens"] = set(c["tokens"])
            cases.append(c)
        print(f"[casematching] Loaded {len(cases)} cases from disk cache.")
        return cases
    except Exception as exc:
        print(f"[casematching] Cache read error ({exc}). Rebuilding...")
        return None


def _save_cache(cases: list, fingerprint: str) -> None:
    serialisable = [
        {
            "filename": c["filename"],
            "text":     c["text"],
            "tokens":   sorted(c["tokens"]),
            "identity": c.get("identity", ""),
        }
        for c in cases
    ]
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"fingerprint": fingerprint, "cases": serialisable},
                      f, ensure_ascii=False)
        print(f"[casematching] Disk cache saved ({len(cases)} cases).")
    except Exception as exc:
        print(f"[casematching] Could not save cache: {exc}")


# ── Case loading (two-layer cache) ────────────────────────────────────────────

def _get_cases() -> list:
    """
    Layer 1: module-level in-memory variable  -> zero I/O, instant
    Layer 2: JSON disk cache                  -> skips all PDF parsing
    Layer 3: parse every PDF from scratch     -> slow, ONE-TIME ONLY
    """
    global _CASES_IN_MEMORY

    if _CASES_IN_MEMORY is not None:
        return _CASES_IN_MEMORY

    cached = _load_cache()
    if cached is not None:
        _CASES_IN_MEMORY = cached
        return _CASES_IN_MEMORY

    print("[casematching] No cache found. Parsing PDFs (one-time cost)...")
    if not os.path.isdir(FAMILY_CASES_DIR):
        print(f"[casematching] WARNING: {FAMILY_CASES_DIR} does not exist.")
        _CASES_IN_MEMORY = []
        return _CASES_IN_MEMORY

    cases = []
    for fname in sorted(os.listdir(FAMILY_CASES_DIR)):
        if not fname.lower().endswith(".pdf"):
            continue
        fpath = os.path.join(FAMILY_CASES_DIR, fname)
        text  = _extract_pdf_text(fpath)

        # Only skip truly empty / completely unreadable files
        if len(text) < 30:
            print(f"[casematching] Skipping {fname} (unreadable / empty).")
            continue

        cases.append({
            "filename": fname,
            "text":     text,
            "tokens":   set(_tokenise(text)),
            "identity": _extract_case_identity(text),
        })

    print(f"[casematching] Parsed {len(cases)} PDFs.")
    _save_cache(cases, _build_dir_fingerprint())
    _CASES_IN_MEMORY = cases
    return _CASES_IN_MEMORY


# ── Gemini contextual comparison ─────────────────────────────────────────────

def _gemini_compare(user_description: str, candidates: list) -> list:
    """
    Sends the top-5 candidates to Gemini with MODEL_HIERARCHY fallback.
    Returns 1-3 results. Each result includes a human-readable case label
    (derived from the case content: court, date, parties) AND the source
    PDF filename.
    """
    if not candidates:
        return []

    cases_block = ""
    for i, c in enumerate(candidates, 1):
        snippet = c["text"][:4000]
        cases_block += (
            f"\n--- CASE {i} ---\n"
            f"Source file: {c['filename']}\n"
            f"Keyword Similarity: {round(c['similarity'] * 100, 1)}%\n"
            f"Case Content:\n{snippet}\n"
        )

    prompt = f"""
You are a senior Pakistani legal analyst specialising in family law.
A user has described their family dispute. You have been given {len(candidates)} past
Pakistani court cases that share keywords with the user's case.

USER'S CASE:
\"\"\"{user_description}\"\"\"

CANDIDATE PAST CASES:
{cases_block}

YOUR TASK:
1. Rank these cases from most to least relevant to the user's situation.
2. Select and return the TOP 1 TO 3 most relevant cases. You MUST always return
   at least 1 case. Never return an empty array.
3. For each selected case provide:
   a. "case_label": A concise human-readable identifier extracted FROM THE CASE CONTENT.
      Format it as: "<Court Name>, <Year> — <Main Party Name(s)>"
      Example: "Lahore High Court, 2019 — Rehman v. Siddiqui"
      Use whatever identifying information is actually present in the text
      (court, year, citation number, names of parties). Do NOT use the filename.
   b. "source_file": Copy the exact "Source file:" filename shown above for that case.
   c. "relevance": "supports", "opposes", or "neutral"
   d. "explanation": 2-4 sentences that:
      - Identify the key legal principle or factual pattern in the past case.
      - Explain how that principle applies (or can be argued to apply) to the user's case.
      - State plainly whether this precedent helps or hurts the user's claim.
      Even if the contextual overlap is imperfect, find the strongest legal argument
      connecting the case to the user's situation.

4. Only omit a candidate if it truly shares zero legal relevance (e.g. a pure
   commercial contract dispute with no family law dimension). Even then, still
   return at least 1 case.

Return ONLY valid JSON — no markdown fences, no extra text.

JSON FORMAT:
[
  {{
    "case_label": "<Court Name, Year — Parties>",
    "source_file": "<exact pdf filename>",
    "relevance": "supports | opposes | neutral",
    "explanation": "<2-4 sentence explanation>"
  }}
]
"""

    for model_name in MODEL_HIERARCHY:
        try:
            print(f"[casematching] Generating match analysis using {model_name}...")
            model         = genai.GenerativeModel(model_name)
            response      = model.generate_content(prompt)
            text_response = response.text.strip()

            # Strip markdown fences (same pattern as processing.py)
            if text_response.startswith("```json"):
                text_response = text_response[7:]
            if text_response.startswith("```"):
                text_response = text_response[3:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]

            parsed = json.loads(text_response.strip())
            if not isinstance(parsed, list):
                raise ValueError("Response is not a JSON array.")

            name_to_sim = {c["filename"]: c["similarity"] for c in candidates}
            results = []
            for item in parsed[:3]:
                source_file = item.get("source_file", "")
                results.append({
                    "case_label":            item.get("case_label", source_file),
                    "source_file":           source_file,
                    "similarity_percentage": round(name_to_sim.get(source_file, 0) * 100, 1),
                    "relevance":             item.get("relevance", "neutral"),
                    "explanation":           item.get("explanation", ""),
                })
            return results

        except Exception as e:
            print(f"[casematching] Model {model_name} failed: {e}")
            print("[casematching] Switching to next available model...")
            continue

    print("[casematching] Error: All models in the hierarchy failed to generate analysis.")
    return []


# ── Public API ────────────────────────────────────────────────────────────────

def find_similar_cases(user_description: str) -> dict:
    """
    Main entry point called from main.py.

    Returns:
    {
      "top_matches": [
        {
          "case_label":            str,   <- human-readable (court, year, parties)
          "source_file":           str,   <- original PDF filename
          "similarity_percentage": float,
          "relevance":             "supports" | "opposes" | "neutral",
          "explanation":           str
        },
        ...  (1-3 items)
      ],
      "message": str
    }
    """
    if not user_description or len(user_description.strip()) < 20:
        return {"top_matches": [], "message": "Case description is too short to match."}

    # Step 1: get cases (memory -> disk cache -> parse PDFs)
    all_cases = _get_cases()
    if not all_cases:
        return {
            "top_matches": [],
            "message": (
                "No past family cases found. "
                "Please add PDF files to backend/family_cases/."
            ),
        }

    # Step 2: word-overlap scoring — include ALL cases, no minimum cutoff
    query_tokens = set(_tokenise(user_description))
    scored = []
    for case in all_cases:
        sim = _similarity(query_tokens, case["tokens"])
        scored.append({**case, "similarity": sim})

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    top5 = scored[:5]

    # Step 3: Gemini contextual comparison
    gemini_results = _gemini_compare(user_description, top5)

    if not gemini_results:
        # Hard fallback: return the best keyword match with a plain note
        best = top5[0]
        fallback = [{
            "case_label":            best.get("identity", best["filename"]),
            "source_file":           best["filename"],
            "similarity_percentage": round(best["similarity"] * 100, 1),
            "relevance":             "neutral",
            "explanation": (
                "This is the closest matching case found based on keyword overlap. "
                "The AI contextual analysis was unavailable at this time. "
                "Please review this case manually to assess its relevance to your situation."
            ),
        }]
        return {
            "top_matches": fallback,
            "message": "AI analysis unavailable. Showing closest keyword match.",
        }

    return {
        "top_matches": gemini_results,
        "message": f"Found {len(gemini_results)} relevant case(s) from the database.",
    }