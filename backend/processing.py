import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure the Generative AI Model
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("CRITICAL WARNING: API Key not found in environment variables.")
else:
    genai.configure(api_key=api_key)

# Define the hierarchy of models to use for fallback
MODEL_HIERARCHY = [
    'gemini-flash-lite-latest',
    'gemma-3-4b-it',
    'gemini-pro-latest',
    'gemini-2.5-flash-lite',
    'gemini-flash-latest'
]


def generate_legal_analysis(case_type: str, case_description: str, relevant_laws: list) -> dict:
    """
    Generates a legal analysis using the configured Generative AI model.
    Iterates through MODEL_HIERARCHY if a model fails or hits a limit.
    """

    context_str = "\n\n--- RELEVANT LEGAL PROVISIONS ---\n"
    for i, law in enumerate(relevant_laws):
        title = law.get('source_title', 'Unknown Source')
        text = law.get('source_text', '')
        context_str += f"Source: {title}\nText: \"{text}\"\n\n"

    prompt = f"""
    Act as a Senior Pakistani Legal Advocate.
    Category: {case_type}

    CASE DETAILS:
    "{case_description}"

    LEGAL CONTEXT (Use these specific laws):
    {context_str}

    INSTRUCTIONS:
    1. **Validity Assessment:** Analyze the legal standing of the case based *strictly* on Pakistani Law.
    2. **Application of Law:** Apply the specific sections mentioned in 'LEGAL CONTEXT' to the facts.
    3. **Legal Analysis:** Provide a professional legal opinion on the strength of the case. 
       - DO NOT provide a "Recommended Strategy" list. 
       - Just provide the analysis of the legal position in paragraphs mainly based on 'LEGAL CONTEXT'.
    4. **Simplified Advice:** Explain it simply (ELU5 level) for a layperson.
    5. Return strictly Valid JSON.

    JSON FORMAT:
    {{
        "case_summary": "Professional summary.",
        "key_facts": ["Fact 1", "Fact 2"],
        "validity_status": "Strong/Moderate/Weak",
        "validity_assessment": {{
            "risk_level": "Low/Moderate/High",
            "advice_summary": "Write your strict legal analysis here. (Paragraphs only, no lists).",
            "simplified_advice": "Simple explanation here."
        }}
    }}
    """

    # Try each model in order
    for model_name in MODEL_HIERARCHY:
        try:
            print(f"Generating Analysis using {model_name}...")
            # Instantiate the specific model for this attempt
            model = genai.GenerativeModel(model_name)

            response = model.generate_content(prompt)
            text_response = response.text.strip()

            if text_response.startswith("```json"):
                text_response = text_response[7:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]

            # If successful, parse and return immediately
            return json.loads(text_response.strip())

        except Exception as e:
            print(f"Error with model {model_name}: {e}")
            print("Switching to next available model...")
            continue

    # If the loop finishes without returning, all models failed
    print("Error: All models in the hierarchy failed to generate analysis.")
    return None