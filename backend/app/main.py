import os
import shutil
import uuid
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.schemas import FormMitraAnalysis, AskMitraRequest, AskMitraResponse
from app.services.gemini_service import analyze_document_with_gemini, ask_mitra_query

logger = logging.getLogger("formmitra.api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="FormMitra API",
    description="Your empathetic AI companion for demystifying and completing complex forms & documents.",
    version="2.0.0"
)

# Enable CORS for development and cross-origin access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "uploads"))
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# In-memory session store for analyzed forms
ANALYSIS_CACHE: Dict[str, Dict[str, Any]] = {}

# Mount static directory if it exists
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_home():
    """Serves the FormMitra frontend interface."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "app": "FormMitra API",
        "status": "Online",
        "message": "FormMitra backend running. Frontend index.html loading..."
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": "FormMitra",
        "version": "2.0.0",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY"))
    }


@app.post("/api/analyze-form")
async def analyze_form(
    file: UploadFile = File(...),
    language: str = Form("en")
):
    """
    Main FormMitra endpoint:
    Reads uploaded form (PDF/Image) natively using Gemini multimodal vision.
    Returns structured analysis with form purpose, document checklist,
    field-by-field guidance, and critical rejection mistakes.
    """
    allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{file_ext}'. Please upload a PDF or image (PNG, JPG, WEBP)."
        )

    # Generate a safe file id
    safe_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    filepath = os.path.join(UPLOADS_DIR, safe_filename)

    file_bytes = await file.read()
    with open(filepath, "wb") as buffer:
        buffer.write(file_bytes)

    # Determine MIME type
    mime_type = file.content_type or ("application/pdf" if file_ext == ".pdf" else f"image/{file_ext.replace('.', '')}")

    try:
        analysis = analyze_document_with_gemini(
            file_bytes=file_bytes,
            mime_type=mime_type,
            language=language
        )

        analysis_dict = analysis.model_dump()
        ANALYSIS_CACHE[safe_filename] = analysis_dict

        return {
            "success": True,
            "file_id": safe_filename,
            "filename": file.filename,
            "analysis": analysis_dict
        }

    except Exception as e:
        logger.error(f"Error analyzing document: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Could not analyze document: {str(e)}"
        )


@app.post("/api/ask-mitra", response_model=AskMitraResponse)
async def ask_mitra(request: AskMitraRequest):
    """
    Allows the user to ask questions about the analyzed form,
    clarifying ambiguities, ink color, optional fields, or missing documents.
    """
    context = request.analysis_context
    if not context and request.file_id:
        context = ANALYSIS_CACHE.get(request.file_id)

    try:
        response = ask_mitra_query(
            query=request.query,
            analysis_context=context,
            language=request.language or "en"
        )
        return response
    except Exception as e:
        logger.error(f"Error answering Mitra query: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Could not process question: {str(e)}"
        )


@app.get("/api/sample-forms")
def list_sample_forms():
    """
    Lists sample documents pre-existing in the uploads folder
    for instant 1-click testing in the UI.
    """
    if not os.path.exists(UPLOADS_DIR):
        return {"samples": []}

    allowed = {".pdf", ".png", ".jpg", ".jpeg"}
    samples = []
    
    friendly_names = {
        "adhar varun.jpeg": "Aadhaar Card (Sample Identity Proof)",
        "AdmitCard-260310517952 (1).pdf": "Official Exam Admit Card / Hall Ticket",
        "JEE_MAIN_29th_Jan.pdf": "National Entrance Exam Document",
        "Varun Singh Internship Completion Certificate (1).pdf": "Internship Completion Certificate",
        "jee main result.pdf": "Entrance Examination Scorecard / Result",
        "varun_resume.pdf": "Professional Curriculum Vitae / Resume"
    }

    for fname in os.listdir(UPLOADS_DIR):
        ext = os.path.splitext(fname)[1].lower()
        if ext in allowed and not fname.startswith("page_") and not fname.startswith("Screenshot"):
            samples.append({
                "filename": fname,
                "display_name": friendly_names.get(fname, fname),
                "type": "PDF" if ext == ".pdf" else "Image"
            })

    return {"samples": samples[:8]}


@app.post("/api/analyze-sample/{filename}")
async def analyze_sample(filename: str, language: str = "en"):
    """
    Analyzes an existing sample document directly from the server.
    """
    filepath = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Sample file not found.")

    ext = os.path.splitext(filename)[1].lower()
    mime_type = "application/pdf" if ext == ".pdf" else f"image/{ext.replace('.', '')}"

    with open(filepath, "rb") as f:
        file_bytes = f.read()

    try:
        analysis = analyze_document_with_gemini(
            file_bytes=file_bytes,
            mime_type=mime_type,
            language=language
        )
        analysis_dict = analysis.model_dump()
        ANALYSIS_CACHE[filename] = analysis_dict

        return {
            "success": True,
            "file_id": filename,
            "filename": filename,
            "analysis": analysis_dict
        }
    except Exception as e:
        logger.error(f"Sample analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# BACKWARD COMPATIBLE ENDPOINTS
# ==========================================

@app.post("/upload")
async def legacy_upload(file: UploadFile = File(...)):
    """Legacy upload endpoint maintained for backwards compatibility."""
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    filepath = os.path.join(UPLOADS_DIR, file.filename)
    with open(filepath, "wb") as buffer:
        buffer.write(await file.read())
    return {
        "message": "File uploaded successfully",
        "filename": file.filename
    }


@app.post("/explain-form")
async def legacy_explain_form(file: UploadFile = File(...)):
    """Legacy explain-form endpoint mapped directly to Gemini analysis."""
    file_bytes = await file.read()
    ext = os.path.splitext(file.filename)[1].lower()
    mime_type = "application/pdf" if ext == ".pdf" else f"image/{ext.replace('.', '')}"
    analysis = analyze_document_with_gemini(file_bytes, mime_type, "en")
    return analysis.model_dump()