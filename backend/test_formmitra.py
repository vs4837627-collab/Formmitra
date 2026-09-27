import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.schemas import FormMitraAnalysis, AskMitraRequest, AskMitraResponse

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "FormMitra"
    print("[PASS] Health check passed")

def test_home_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "FormMitra" in response.text
    assert "dropzone" in response.text
    print("[PASS] Home page serving index.html passed")

def test_sample_forms_list():
    response = client.get("/api/sample-forms")
    assert response.status_code == 200
    data = response.json()
    assert "samples" in data
    assert len(data["samples"]) > 0
    print(f"[PASS] Sample forms list returned {len(data['samples'])} samples")

def test_schemas():
    analysis = FormMitraAnalysis(
        form_title="Test Scholarship Form",
        issuing_authority="Dept of Higher Education",
        document_category="Government Scheme / Benefit",
        simple_summary="A scholarship application for post-matric students.",
        who_should_fill="Students enrolled in accredited colleges with family income under 2.5 LPA.",
        document_checklist=[
            {
                "document_name": "Income Certificate",
                "purpose": "Verify income threshold",
                "original_or_copy": "Original / Digitally Verified",
                "is_mandatory": True
            }
        ],
        sections=[
            {
                "section_id": "sec_1",
                "section_title": "Section 1: Personal Particulars",
                "description": "Basic student identity details",
                "fields": [
                    {
                        "field_id": "f_1",
                        "field_label": "Applicant Name",
                        "section_name": "Section 1",
                        "plain_english_meaning": "Your legal name exactly as on records",
                        "what_to_enter": "Write in BLOCK CAPITAL letters exactly matching Class 10th certificate",
                        "is_mandatory": True,
                        "sample_value": "RAVI KUMAR",
                        "supporting_document": "10th Marksheet"
                    }
                ]
            }
        ],
        critical_mistakes=[
            {
                "mistake_id": "m_1",
                "title": "Name Mismatch with Marksheet",
                "severity": "CRITICAL",
                "why_it_causes_rejection": "Directly rejected during automated Aadhaar-marksheet cross-verification.",
                "how_to_prevent": "Copy the spelling letter-for-letter from 10th marksheet."
            }
        ],
        step_by_step_instructions=[
            "Step 1: Arrange your Income Certificate and 10th Marksheet",
            "Step 2: Fill Personal details in capital letters",
            "Step 3: Review and submit at the college scholarship desk"
        ]
    )
    dumped = analysis.model_dump()
    assert dumped["form_title"] == "Test Scholarship Form"
    print("[PASS] Pydantic schemas validation passed")

if __name__ == "__main__":
    print("Running FormMitra test suite...")
    test_health()
    test_home_page()
    test_sample_forms_list()
    test_schemas()
    print("\nALL TESTS PASSED SUCCESSFULLY!")
