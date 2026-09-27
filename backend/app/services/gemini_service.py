import os
import json
import base64
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from google import genai
import requests
from app.schemas import FormMitraAnalysis, AskMitraResponse

# Load environment variables
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

logger = logging.getLogger("formmitra.gemini")
logging.basicConfig(level=logging.INFO)

PREFERRED_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.7-flash"
]

_client = None

def get_gemini_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured. Please add GEMINI_API_KEY to your backend/.env file."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def clean_json_text(text: str) -> str:
    """Clean markdown code fences and whitespace from model JSON output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def analyze_document_with_gemini(
    file_bytes: bytes,
    mime_type: str,
    language: str = "en"
) -> FormMitraAnalysis:
    """
    Natively analyzes a PDF or image form using Gemini Interactions API with resilient model fallback
    and returns a structured FormMitraAnalysis object.
    """
    client = get_gemini_client()
    b64_data = base64.b64encode(file_bytes).decode("utf-8")

    # Determine input type for Gemini
    is_pdf = "pdf" in mime_type.lower()
    input_item = {
        "type": "document" if is_pdf else "image",
        "data": b64_data,
        "mime_type": "application/pdf" if is_pdf else mime_type
    }

    lang_instructions = {
        "en": "Respond in clear, friendly, and easy-to-understand English without confusing bureaucratic jargon.",
        "hi": "सभी विवरण, फ़ील्ड्स के निर्देश, आवश्यक दस्तावेज़ और सावधानियाँ शुद्ध, सरल और विनम्र हिंदी (Devanagari) में लिखें ताकि कोई भी आम नागरिक आसानी से समझ सके।",
        "hinglish": "Explain everything in warm, conversational Hinglish (Hindi words written in Latin/English script) like a helpful friend explaining how to fill the form."
    }.get(language.lower(), "Respond in clear, friendly, and easy-to-understand English.")

    prompt_text = f"""
You are FormMitra (फॉर्म मित्र), an expert and empathetic AI document assistant.
Your goal is to help citizens, students, and applicants understand and fill complex forms without fear, confusion, or rejection.

Carefully inspect the attached document visually, including its title, department, headers, columns, tables, checkboxes, fine-print instructions, and footnote guidelines.

CRITICAL INSTRUCTIONS:
1. FORM PURPOSE & OVERVIEW:
   - Identify the exact official form title and issuing authority.
   - Explain what this form is for, who needs it, and what happens once filled.
   - Identify eligibility criteria and submission guidelines (online portal or physical counter, fee, deadlines).

2. DOCUMENT CHECKLIST (PRE-FLIGHT):
   - List every single supporting document, proof of identity, certificate, photograph, or receipt the applicant must gather BEFORE starting to fill the form.
   - Specify whether an original, self-attested photocopy, or digital softcopy is required.

3. FIELD-BY-FIELD GUIDANCE:
   - Group the form into logical sections (e.g., Personal Details, Address Details, Academic/Category, Declaration & Signature).
   - For EVERY field/box on the form:
     * field_label: Exact text/label printed on the form.
     * plain_english_meaning: What this field really means in simple terms.
     * what_to_enter: Clear instructions on exact format, capitalization (e.g. BLOCK LETTERS), date formats (DD/MM/YYYY), or abbreviations.
     * is_mandatory: True if required, False if optional.
     * supporting_document: Which document to verify the exact spelling or value from (e.g. 10th marksheet, Aadhaar card).
     * sample_value: A realistic, valid example.
     * format_rules: E.g., 'Only 10 digits', 'Capital letters only, no initials'.
     * mistake_risk: Any specific pitfall in this field.

4. CRITICAL REJECTION MISTAKES:
   - Identify the top common errors that lead to forms being rejected or delayed (e.g., name mismatch with Aadhaar/10th certificate, signing outside the box, using wrong ink, missing self-attestation, incorrect date format, incorrect category certificate date).
   - For each mistake, explain WHY it causes rejection and HOW to prevent it.

5. STEP-BY-STEP INSTRUCTIONS:
   - Provide an ordered checklist of steps from start to final submission.

LANGUAGE REQUIREMENT:
{lang_instructions}

Return the analysis strictly adhering to the FormMitraAnalysis JSON schema.
"""

    logger.info(f"Sending document ({len(file_bytes)} bytes, {mime_type}) to Gemini...")
    schema = FormMitraAnalysis.model_json_schema()

    last_error = None
    for model_name in PREFERRED_MODELS:
        try:
            logger.info(f"Attempting analysis with model: {model_name}")
            interaction = client.interactions.create(
                model=model_name,
                input=[
                    input_item,
                    {"type": "text", "text": prompt_text}
                ],
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": schema
                }
            )

            output_text = clean_json_text(interaction.output_text or "{}")
            logger.info(f"Successfully received structured response from {model_name}.")

            # Validate with Pydantic
            analysis = FormMitraAnalysis.model_validate_json(output_text)
            return analysis

        except Exception as e:
            logger.warning(f"Model {model_name} failed with: {e}")
            last_error = e
            continue

    # If schema validation failed across all models, try standard json parse
    for model_name in PREFERRED_MODELS[:2]:
        try:
            interaction = client.interactions.create(
                model=model_name,
                input=[
                    input_item,
                    {"type": "text", "text": prompt_text + "\nIMPORTANT: Return valid JSON ONLY matching the requested structure."}
                ]
            )
            cleaned = clean_json_text(interaction.output_text or "{}")
            data = json.loads(cleaned)
            return FormMitraAnalysis.model_validate(data)
        except Exception as err:
            last_error = err
            continue

    raise RuntimeError(f"All Gemini models failed to analyze document. Last error: {last_error}")


def ask_mitra_query(
    query: str,
    analysis_context: Optional[Dict[str, Any]] = None,
    language: str = "en"
) -> AskMitraResponse:
    """
    Answers user doubts and specific questions about the analyzed form with resilient model fallback.
    """
    client = get_gemini_client()

    context_str = ""
    if analysis_context:
        context_str = f"""
FORM CONTEXT:
- Title: {analysis_context.get('form_title', 'Uploaded Form')}
- Authority: {analysis_context.get('issuing_authority', 'Official Authority')}
- Purpose: {analysis_context.get('simple_summary', '')}
- Who Should Fill: {analysis_context.get('who_should_fill', '')}
- Submission Mode: {analysis_context.get('submission_mode', '')}
- Document Checklist: {[d.get('document_name') for d in analysis_context.get('document_checklist', [])]}
- Common Mistakes: {[m.get('title') for m in analysis_context.get('critical_mistakes', [])]}
- Sections: {[s.get('section_title') for s in analysis_context.get('sections', [])]}
"""

    lang_instructions = {
        "en": "Respond in warm, reassuring, crystal-clear English.",
        "hi": "जवाब विनम्र, आत्मीय और सरल हिंदी में दें ताकि प्रयोक्ता का संशय पूरी तरह दूर हो सके।",
        "hinglish": "Respond in warm, friendly Hinglish like an approachable mentor."
    }.get(language.lower(), "Respond in warm, reassuring, crystal-clear English.")

    prompt_text = f"""
You are FormMitra (फॉर्म मित्र), an AI guide helping a user fill their form.
The user has a question or doubt about this document.

{context_str}

USER QUESTION:
"{query}"

GUIDELINES:
1. Provide a direct, compassionate, and precise answer addressing their exact scenario.
2. If relevant, mention the specific field names or required documents they should pay attention to.
3. If their question touches a critical area (like signature, mismatch in name, date formats, ink color), add a caution_note.
4. Suggest 2 to 3 practical follow-up questions they may find helpful.
5. LANGUAGE: {lang_instructions}

Return ONLY valid JSON strictly matching the AskMitraResponse schema:
{{
  "answer": "string",
  "relevant_fields": ["string"],
  "caution_note": "string or null",
  "suggested_next_questions": ["string", "string"]
}}
"""

    schema = AskMitraResponse.model_json_schema()

    last_error = None
    for model_name in PREFERRED_MODELS:
        try:
            interaction = client.interactions.create(
                model=model_name,
                input=prompt_text,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": schema
                }
            )
            cleaned = clean_json_text(interaction.output_text or "{}")
            return AskMitraResponse.model_validate_json(cleaned)
        except Exception as e:
            logger.warning(f"AskMitra on {model_name} failed: {e}")
            last_error = e
            continue

    # Fallback to direct json parse
    for model_name in PREFERRED_MODELS[:2]:
        try:
            interaction = client.interactions.create(
                model=model_name,
                input=prompt_text
            )
            cleaned = clean_json_text(interaction.output_text or "{}")
            data = json.loads(cleaned)
            return AskMitraResponse.model_validate(data)
        except Exception as e:
            last_error = e
            continue

    # Fallback to OpenRouter if configured
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        try:
            logger.info("Falling back to OpenRouter for AskMitra...")
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta-llama/llama-3.3-70b-instruct:free",
                    "messages": [{"role": "user", "content": prompt_text}]
                },
                timeout=30
            )
            if res.status_code == 200:
                raw_json = res.json()["choices"][0]["message"]["content"]
                cleaned = clean_json_text(raw_json)
                return AskMitraResponse.model_validate(json.loads(cleaned))
        except Exception as or_err:
            logger.warning(f"OpenRouter fallback failed: {or_err}")

    raise RuntimeError(f"Unable to process Ask Mitra query. Last error: {last_error}")
