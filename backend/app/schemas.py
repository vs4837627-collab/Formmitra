from pydantic import BaseModel, Field
from typing import List, Optional


class DocumentRequirement(BaseModel):
    document_name: str = Field(description="Name of the required document or certificate")
    purpose: str = Field(description="Why this document is needed for the form")
    original_or_copy: str = Field(
        default="Self-Attested Photocopy",
        description="Type required: Original, Self-Attested Photocopy, Notarized, or Scanned Softcopy"
    )
    is_mandatory: bool = Field(default=True, description="Whether this document is strictly required")
    where_to_get: Optional[str] = Field(
        default=None,
        description="Where or how the user can obtain this document if they don't have it"
    )


class FieldGuide(BaseModel):
    field_id: str = Field(description="Unique identifier or field number (e.g., 'sec_1_fname', 'item_4')")
    field_label: str = Field(description="Exact label or title printed on the form")
    section_name: str = Field(description="Name of the section this field belongs to")
    plain_english_meaning: str = Field(description="Clear, non-technical explanation of what this field asks for")
    what_to_enter: str = Field(description="Exact instructions on what to write, format to use, uppercase rules, etc.")
    is_mandatory: bool = Field(default=True, description="Whether this field must be filled")
    supporting_document: Optional[str] = Field(
        default=None,
        description="Which document should be checked to verify the exact spelling or value for this field"
    )
    sample_value: Optional[str] = Field(
        default=None,
        description="A clear example of a valid entry (e.g., '05/08/2001', 'RAMESH KUMAR SHARMA')"
    )
    format_rules: Optional[str] = Field(
        default=None,
        description="Any specific format rules (e.g. DD/MM/YYYY, BLOCK LETTERS ONLY, CAPITAL LETTERS, 10-digits)"
    )
    mistake_risk: Optional[str] = Field(
        default=None,
        description="Specific pitfall or mistake to watch out for in this particular field"
    )


class FormSection(BaseModel):
    section_id: str = Field(description="Identifier for the section (e.g., 'sec_personal', 'sec_academic')")
    section_title: str = Field(description="Title of the section (e.g., 'Section 1: Personal Particulars')")
    description: str = Field(description="Brief overview of what this section covers")
    fields: List[FieldGuide] = Field(default_factory=list, description="Fields within this section")


class MistakeWarning(BaseModel):
    mistake_id: str = Field(description="Unique id for the mistake warning")
    title: str = Field(description="Catchy summary of the mistake (e.g., 'Name Mismatch with 10th Certificate')")
    severity: str = Field(
        default="CRITICAL",
        description="Severity level: 'CRITICAL' (causes immediate rejection), 'WARNING' (causes delay/query), or 'TIP'"
    )
    why_it_causes_rejection: str = Field(description="Why forms commonly get rejected or sent back due to this mistake")
    how_to_prevent: str = Field(description="Precise, actionable steps the applicant must take to avoid this mistake")
    related_fields: List[str] = Field(default_factory=list, description="Field names or labels related to this mistake")


class FormMitraAnalysis(BaseModel):
    form_title: str = Field(description="Official name or title of the form or document")
    issuing_authority: str = Field(description="Name of the department, ministry, university, or organization")
    document_category: str = Field(
        description="Category: e.g. 'Government Scheme / Benefit', 'Identity Document / ID Card', 'Examination / Admit Card', 'Academic / Admission Form', 'Employment / Job Application', 'Financial / Bank / Tax', 'Affidavit / Legal Certificate', 'Other'"
    )
    simple_summary: str = Field(
        description="Friendly, easy-to-understand explanation of what this form is for, why it exists, and what filling it accomplishes"
    )
    who_should_fill: str = Field(
        description="Who is eligible to fill this form (eligibility conditions, age, qualifications, criteria)"
    )
    deadline_or_validity: Optional[str] = Field(
        default=None,
        description="Any deadline, cutoff date, expiration date, or validity period indicated or applicable"
    )
    submission_mode: str = Field(
        default="Online Portal",
        description="How to submit: 'Online Portal', 'Physical Office / Counter', 'Speed Post / Courier', or 'Both Online & Physical'"
    )
    fee_details: Optional[str] = Field(
        default="Free / Not Specified",
        description="Application or processing fee details, if mentioned or applicable"
    )
    estimated_time_to_fill: Optional[str] = Field(
        default="15-20 minutes",
        description="Realistic estimate of how long it takes to collect docs and fill the form"
    )
    document_checklist: List[DocumentRequirement] = Field(
        default_factory=list,
        description="List of supporting documents, proofs, photos, certificates needed before filling"
    )
    sections: List[FormSection] = Field(
        default_factory=list,
        description="Structured list of form sections containing field-by-field guidance"
    )
    critical_mistakes: List[MistakeWarning] = Field(
        default_factory=list,
        description="Top common mistakes, traps, and errors that cause this form to be rejected"
    )
    step_by_step_instructions: List[str] = Field(
        default_factory=list,
        description="Chronological step-by-step instructions from gathering documents to final submission"
    )


class AskMitraRequest(BaseModel):
    query: str = Field(description="User's question about the form")
    file_id: Optional[str] = Field(default=None, description="Filename or identifier of the uploaded form")
    analysis_context: Optional[dict] = Field(default=None, description="Full or partial FormMitraAnalysis context")
    language: Optional[str] = Field(default="en", description="Preferred response language: 'en', 'hi', or 'hinglish'")


class AskMitraResponse(BaseModel):
    answer: str = Field(description="Direct, helpful, friendly answer from FormMitra")
    relevant_fields: List[str] = Field(default_factory=list, description="Fields relevant to the user's question")
    caution_note: Optional[str] = Field(default=None, description="Important caution or warning related to the answer")
    suggested_next_questions: List[str] = Field(
        default_factory=list,
        description="2-3 helpful follow-up questions the user might want to ask next"
    )
