import json
import os
import pickle
import re
from typing import List, Dict, Any
import torch
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import util
from dotenv import load_dotenv
import pypdf
# Import the separated processing logic
from processing import generate_legal_analysis

# Load environment variables
load_dotenv()

# --- Configuration ---
CACHE_PATH = "law_data_cache_legalbert_chunked.pkl"
FAMILY_CACHE_PATH = "family_law_cache_v2.pkl"
FAMILY_PDF_PATH = "family_laws.pdf"

MODEL_PATH = "./Pakistani_LegalBERT"

# Chunking Config
CHUNK_SIZE_WORDS = 250
CHUNK_OVERLAP_WORDS = 50

CATEGORY_DEFINITIONS = {
    "Contract Disputes": "breach of contract, agreement violation, non-performance, damages, specific relief, debt recovery, business deal, financial dispute, signatures, terms.",
    "Property Disputes": "land possession, illegal dispossession, tenant eviction, rent payment, title, plot allotment, encroachment, lease agreement, transfer of property, real estate.",
    "Family Disputes": "divorce, khula, maintenance, child custody, guardianship, dowry, haq mehr, restitution of conjugal rights, paternity, inheritance, family courts."
}

# --- STATIC FALLBACK KNOWLEDGE BASE (For specific Family Laws) ---
FAMILY_LAW_KB = {
    "khula": {
        "source_title": "Muslim Family Laws Ordinance, 1961",
        "source_text": "Section 8: Dissolution of marriage otherwise than by talaq.—Where the right to divorce has been duly delegated to the wife and she wishes to exercise that right, or where any of the parties to a marriage wishes to dissolve the marriage otherwise than by talaq (i.e. Khula), the provisions of section 7 shall, mutatis mutandis and so far as applicable, apply.",
        "relevance_score": 0.92
    },
    "divorce": {
        "source_title": "Muslim Family Laws Ordinance, 1961",
        "source_text": "Section 7: Talaq.—(1) Any man who wishes to divorce his wife shall, as soon as may be after the pronouncement of talaq in any form whatsoever, give the Chairman notice in writing of his having done so, and shall supply a copy thereof to the wife.",
        "relevance_score": 0.92
    },
    "maintenance": {
        "source_title": "Muslim Family Laws Ordinance, 1961",
        "source_text": "Section 9: Maintenance.—(1) If any husband fails to maintain his wife adequately, or where there are more wives than one, fails to maintain them equitably, the wife may apply to the Chairman who shall constitute an Arbitration Council to determine the matter.",
        "relevance_score": 0.90
    },
    "custody": {
        "source_title": "Guardians and Wards Act, 1890",
        "source_text": "Section 17: Matters to be considered by the Court in appointing guardian.—(1) In appointing or declaring the guardian of a minor, the Court shall, subject to the provisions of this section, be guided by what, consistently with the law to which the minor is subject, appears in the circumstances to be for the welfare of the minor.",
        "relevance_score": 0.89
    },
    "dower": {
        "source_title": "Muslim Family Laws Ordinance, 1961",
        "source_text": "Section 10: Dower.—Where no details about the mode of payment of dower are specified in the nikah nama, the entire amount of the dower shall be presumed to be payable on demand.",
        "relevance_score": 0.88
    }
}


class LegalAIEngine:
    def __init__(self):
        print("--- Initializing Legal AI Engine (Concise Mode) ---")

        # 1. Load BERT Model
        print(f"Loading BERT Model: {MODEL_PATH}...")
        self.device = torch.device("cpu")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
            self.model = AutoModel.from_pretrained(MODEL_PATH)
            self.model.to(self.device)
            self.model.eval()
            print("✅ Pakistani Legal BERT Loaded Successfully.")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.tokenizer = None
            self.model = None

        # 2. Load Indices
        self.law_database = []
        self.law_embeddings = None
        self._load_main_cache()

        self.family_database = []
        self.family_embeddings = None

        if self.model:
            self._prepare_family_index()
            self._build_category_embeddings()

    def _chunk_text(self, text: str, source_title: str) -> List[Dict[str, str]]:
        words = text.split()
        chunks = []
        if not words: return []

        for i in range(0, len(words), CHUNK_SIZE_WORDS - CHUNK_OVERLAP_WORDS):
            chunk_words = words[i: i + CHUNK_SIZE_WORDS]
            chunk_text = " ".join(chunk_words)
            if len(chunk_text) < 50: continue

            chunks.append({
                "text": chunk_text,
                "source": source_title
            })
        return chunks

    def _get_embedding(self, text: str):
        if not self.model or not self.tokenizer:
            return torch.zeros(768)

        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
        inputs = inputs.to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)

        token_embeddings = outputs.last_hidden_state
        attention_mask = inputs['attention_mask']
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        return torch.nn.functional.normalize(sum_embeddings / sum_mask, p=2, dim=1)

    def _build_category_embeddings(self):
        self.category_embeddings = {}
        for cat, desc in CATEGORY_DEFINITIONS.items():
            self.category_embeddings[cat] = self._get_embedding(desc)

    def _load_main_cache(self):
        if os.path.exists(CACHE_PATH):
            print(f"📦 Loading Main Index from {CACHE_PATH}...")
            try:
                with open(CACHE_PATH, 'rb') as f:
                    cache_data = pickle.load(f)
                    self.law_database = cache_data['database']
                    self.law_embeddings = cache_data['embeddings']
                print(f"✅ Main Database: {len(self.law_database)} chunks ready.")
            except Exception as e:
                print(f"❌ Error loading main cache: {e}")
        else:
            print(f"⚠️ Main cache '{CACHE_PATH}' not found.")

    def _prepare_family_index(self):
        if os.path.exists(FAMILY_CACHE_PATH):
            print(f"📦 Loading Specialized Family Index from {FAMILY_CACHE_PATH}...")
            try:
                with open(FAMILY_CACHE_PATH, 'rb') as f:
                    data = pickle.load(f)
                    self.family_database = data['database']
                    self.family_embeddings = data['embeddings']
                print(f"✅ Family Index: {len(self.family_database)} chunks ready.")
                return
            except Exception as e:
                print(f"⚠️ Family cache corrupted, rebuilding... {e}")

        if not os.path.exists(FAMILY_PDF_PATH):
            print(f"⚠️ Warning: '{FAMILY_PDF_PATH}' not found.")
            return

        print(f"⚙️ Building Family Index...")
        try:
            reader = pypdf.PdfReader(FAMILY_PDF_PATH)
            full_text = ""

            # Start from page 10 to avoid Table of Contents noise
            start_page_index = 10
            if len(reader.pages) <= start_page_index:
                start_page_index = 0

            for i, page in enumerate(reader.pages):
                if i < start_page_index: continue
                text = page.extract_text()
                if text:
                    text = re.sub(r'Page - \d+', '', text)
                    full_text += text + "\n"

            chunks = self._chunk_text(full_text, "Family Laws in Pakistan (Reference Book)")

            embeddings_list = []
            for i, chunk in enumerate(chunks):
                emb = self._get_embedding(chunk['text'])
                embeddings_list.append(emb)

            if embeddings_list:
                self.family_embeddings = torch.cat(embeddings_list, dim=0)
                self.family_database = chunks

                with open(FAMILY_CACHE_PATH, 'wb') as f:
                    pickle.dump({
                        'database': self.family_database,
                        'embeddings': self.family_embeddings
                    }, f)
                print("✅ Family Law Index Built & Cached.")

        except Exception as e:
            print(f"❌ Failed to build family index: {e}")

    def _validate_category(self, description: str, category: str) -> bool:
        if not self.model or category not in self.category_embeddings:
            return True
        desc_vec = self._get_embedding(description)
        cat_vec = self.category_embeddings[category]
        if util.cos_sim(desc_vec, cat_vec).item() < 0.20:
            return False
        return True

    def _is_valid_legal_chunk(self, text: str) -> bool:
        text_lower = text.lower()
        bad_keywords = ["survey", "respondents", "percentage", "table", "figure",
                        "introduction", "preface", "acknowledgment", "bibliography"]
        if any(word in text_lower for word in bad_keywords):
            return False
        return True

    def _sanitize_for_display(self, text: str) -> str:
        """Truncates text to ~150 chars or first sentence for UI display."""
        clean = text.replace('\n', ' ').strip()
        if len(clean) > 150:
            first_period = clean.find('.', 100)
            if first_period != -1 and first_period < 200:
                return clean[:first_period + 1]
            return clean[:150] + "..."
        return clean

    def analyze_case(self, description: str, category: str) -> Dict:
        target_embeddings = self.law_embeddings
        target_db = self.law_database

        if category == "Family Disputes" and self.family_embeddings is not None:
            print("ℹ️ Using Specialized Family Law Index")
            target_embeddings = self.family_embeddings
            target_db = self.family_database
        elif target_embeddings is None:
            return self._get_error_response("Knowledge Base not loaded.")

        if not self._validate_category(description, category):
            return {
                "case_summary": "Category Mismatch",
                "key_facts": [],
                "relevant_laws": [],
                "validity_status": "REJECTED",
                "validity_assessment": {
                    "risk_level": "N/A",
                    "advice_summary": f"The description does not align with '{category}'.",
                    "simplified_advice": "Category mismatch."
                }
            }

        relevant_laws = []

        # A. Hybrid Injection for Family Law (Manual KB)
        if category == "Family Disputes":
            desc_lower = description.lower()
            for key, law_obj in FAMILY_LAW_KB.items():
                if key in desc_lower:
                    relevant_laws.append(law_obj)

        # B. Vector Search
        query_vec = self._get_embedding(f"{category}: {description}")
        search_results = util.cos_sim(query_vec, target_embeddings)[0]

        top_results = torch.topk(search_results, k=min(50, len(target_db)))

        seen_texts = set(l['source_text'] for l in relevant_laws)

        for score, idx in zip(top_results.values, top_results.indices):
            s = float(score.item())

            if s < 0.55: continue

            chunk_data = target_db[idx.item()]
            text_content = chunk_data.get('text', '')

            if not self._is_valid_legal_chunk(text_content): continue
            if text_content in seen_texts: continue

            seen_texts.add(text_content)
            relevant_laws.append({
                "source_title": chunk_data.get('source', 'Unknown'),
                "source_text": text_content,
                "relevance_score": s,
                "source_category": "Specialized Family Law" if target_embeddings is self.family_embeddings else "Pakistan Law"
            })

        # TOP 3 Only
        relevant_laws = sorted(relevant_laws, key=lambda x: x['relevance_score'], reverse=True)[:3]

        # 4. Generation (using separated processing module)
        llm_response = generate_legal_analysis(category, description, relevant_laws)

        # 5. Prepare Output for Frontend (Truncated Laws)
        display_laws = []
        for law in relevant_laws:
            display_laws.append({
                "source_title": law['source_title'],
                "source_text": self._sanitize_for_display(law['source_text']),
                "relevance_score": law['relevance_score'],
                "source_category": law.get('source_category', 'Pakistan Law')
            })

        if llm_response:
            return {
                "case_summary": llm_response.get("case_summary", "Summary unavailable."),
                "key_facts": llm_response.get("key_facts", []),
                "relevant_laws": display_laws,
                "validity_status": llm_response.get("validity_status", "Uncertain"),
                "validity_assessment": llm_response.get("validity_assessment", {})
            }
        else:
            return self._get_error_response("AI Analysis Failed")

    def _get_error_response(self, msg):
        return {
            "case_summary": f"System Alert: {msg}",
            "key_facts": [],
            "relevant_laws": [],
            "validity_status": "ERROR",
            "validity_assessment": {
                "risk_level": "Unknown",
                "advice_summary": "Service unavailable.",
                "simplified_advice": "Please try again."
            }
        }


legal_engine = LegalAIEngine()