import os
import json
import torch
import numpy as np
import faiss
import glob
from transformers import AutoTokenizer, AutoModel
from datasets import load_dataset

# --- Configuration ---
MODEL_PATH = "./model"
JSON_DATA_PATH = "./data/pdf_data.json"
JUDGMENTS_FOLDER_PATH = "./data/Supreme_court_Of_Pakistan_judgments"
HF_DATASET_NAME = "Ibtehaj10/supreme-court-of-pak-judgments"
INDEX_PATH = "./data/legal_index.faiss"
METADATA_PATH = "./data/legal_metadata.json"


class AIService:
    def __init__(self):
        print("Loading Pakistani LegalBERT...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
            self.model = AutoModel.from_pretrained(MODEL_PATH)
        except OSError:
            print("Error: Model not found in ./model/. Using default LegalBERT.")
            self.tokenizer = AutoTokenizer.from_pretrained("nlpaueb/legal-bert-base-uncased")
            self.model = AutoModel.from_pretrained("nlpaueb/legal-bert-base-uncased")

        self.model.eval()
        self.index = None
        self.metadata = []

        # Load index if exists, otherwise build it
        if os.path.exists(INDEX_PATH) and os.path.exists(METADATA_PATH):
            self.load_index()
        else:
            self.build_index()

    def get_embedding(self, text):
        """Converts text into a vector using BERT."""
        # Truncate to 512 tokens to fit BERT's limit
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.last_hidden_state[:, 0, :].numpy()

    def load_all_documents(self):
        """Loads data from JSON, Hugging Face (ALL SPLITS), and local files."""
        print("--- Loading All Knowledge Sources ---")
        documents_list = []

        # 1. Load JSON Data
        if os.path.exists(JSON_DATA_PATH):
            try:
                with open(JSON_DATA_PATH, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)

                count = 0
                for entry in raw_data:
                    # Try common keys
                    text = entry.get('content') or entry.get('text') or entry.get('body')
                    if text and len(str(text)) > 100:
                        documents_list.append(str(text))
                        count += 1
                print(f"Loaded {count} documents from JSON.")
            except Exception as e:
                print(f"Error loading JSON: {e}")
        else:
            print(f"Warning: JSON data not found at {JSON_DATA_PATH}")

        # 2. Load Hugging Face Dataset (Robust & Complete)
        try:
            print(f"Downloading HF Dataset: {HF_DATASET_NAME}...")
            # Load dataset dict (contains all splits like 'train', 'test', etc.)
            hf_dataset_dict = load_dataset(HF_DATASET_NAME)

            hf_count = 0
            # Iterate through EVERY split available (train, test, validation)
            for split in hf_dataset_dict.keys():
                dataset = hf_dataset_dict[split]

                # Smartly find the text column
                text_col = next((col for col in ['text', 'content', 'judgment', 'body'] if col in dataset.column_names),
                                None)

                if text_col:
                    for entry in dataset:
                        text = entry[text_col]
                        if text and len(str(text)) > 100:
                            documents_list.append(str(text))
                            hf_count += 1

            print(f"Loaded {hf_count} documents from Hugging Face (All Splits).")
        except Exception as e:
            print(f"Warning: Could not load Hugging Face dataset. Error: {e}")

        # 3. Load Local Text Files
        if os.path.isdir(JUDGMENTS_FOLDER_PATH):
            text_files = glob.glob(os.path.join(JUDGMENTS_FOLDER_PATH, '**', '*.txt'), recursive=True)
            local_count = 0
            for filepath in text_files:
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if len(content) > 100:
                            documents_list.append(content)
                            local_count += 1
                except:
                    pass
            print(f"Loaded {local_count} documents from local folder.")
        else:
            print(f"Warning: Local judgments folder not found at {JUDGMENTS_FOLDER_PATH}")

        return documents_list

    def build_index(self):
        print("Building Knowledge Base Index...")
        documents = self.load_all_documents()

        if not documents:
            print("No documents found. Index build failed.")
            return

        self.metadata = []
        embeddings = []

        print(f"Total unique documents to index: {len(documents)}")

        # Batch processing for speed
        batch_size = 32
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i: i + batch_size]

            for doc in batch_docs:
                self.metadata.append({
                    "preview": doc[:300].replace('\n', ' ') + "...",
                    "full_text": doc
                })
                # Get embedding
                emb = self.get_embedding(doc)
                embeddings.append(emb)

            if i % 100 == 0:
                print(f"Indexed {i}/{len(documents)} documents...")

        if not embeddings:
            print("Failed to generate embeddings.")
            return

        # Stack and Index
        embedding_matrix = np.vstack(embeddings)
        dimension = embedding_matrix.shape[1]

        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embedding_matrix)

        # Save
        faiss.write_index(self.index, INDEX_PATH)
        with open(METADATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f)
        print(f"Index built and saved! Total vectors: {self.index.ntotal}")

    def load_index(self):
        print("Loading existing index...")
        self.index = faiss.read_index(INDEX_PATH)
        with open(METADATA_PATH, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)

    def analyze_case(self, user_case_text):
        """Performs Case Analysis and Matching."""
        # Sanity Check
        if len(user_case_text.strip()) < 10 or "asdf" in user_case_text.lower():
            return {
                "status": "error",
                "message": "The case details provided seem invalid. Please provide a clear description."
            }

        # Embed User Query
        user_emb = self.get_embedding(user_case_text)

        # Search Index
        k = 3
        distances, indices = self.index.search(user_emb, k)

        matches = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.metadata):
                # Loose threshold to ensure we get results for now
                if distances[0][i] < 300.0:
                    matches.append(self.metadata[idx])

        if not matches:
            return {
                "status": "success",
                "analysis": "No close Pakistani precedents were found in the database.",
                "matches": []
            }

        # Generate Analysis Text from the best match
        best_match = matches[0]['preview']
        analysis_text = (
            f"Based on Pakistani legal precedents, your case involves issues similar to:\n"
            f"'{best_match}'\n\n"
            f"Key legal points to consider:\n"
            f"1. Review the specific statutes mentioned in the matching judgment.\n"
            f"2. Ensure your evidence aligns with the facts established in these precedents."
        )

        return {
            "status": "success",
            "analysis": analysis_text,
            "matches": matches
        }


# Global instance
ai_system = AIService()