from __future__ import annotations

from sqlmodel import Session, select

from ..llm.client import chat_json
from ..llm.prompts import system_outreach_email, user_outreach_email
from ..llm.schemas import OutreachEmail
from ..settings import settings
from ..storage import Case, ChecklistItem, Document, GapItem, engine


def _fallback_email(
    client_name: str | None,
    *,
    checklist_required: list[str],
    checklist_missing: list[str],
    missing_fields: list[str],
    invalid_docs: list[str],
    inconsistency_messages: list[str],
    extra_docs: list[str],
    jurisdiction: str = "",
) -> OutreachEmail:
    """Generate professional email when LLM is not available."""
    who = client_name or "Valued Client"
    
    # Convert technical names to readable format
    field_map = {
        "certificate_of_incorporation.registered_address": "Registered business address",
        "certificate_of_incorporation.company_name": "Legal company name",
        "certificate_of_incorporation.registration_number": "Company registration number / CIN",
        "certificate_of_incorporation.incorporation_date": "Date of company incorporation",
        "ubo_declaration.entity_name": "Entity name on UBO declaration",
        "ubo_declaration.ubo_name": "Ultimate Beneficial Owner full name",
        "ubo_declaration.ubo_dob": "UBO date of birth",
        "ubo_declaration.ubo_nationality": "UBO nationality",
        "proof_of_address.entity_name": "Entity name on address proof",
        "proof_of_address.registered_address": "Current registered address proof",
        "directors_list.company_name": "Company name on directors list",
        "directors_list.directors": "Complete list of current directors",
        "board_resolution.company_name": "Company name on board resolution",
        "board_resolution.resolution_date": "Date of board resolution (within last 6 months)",
    }
    
    readable_fields = [field_map.get(f, f.replace("_", " ").replace(".", " - ").title()) for f in missing_fields]
    readable_required = [d.replace("_", " ").title() for d in checklist_required]
    readable_missing_docs = [d.replace("_", " ").title() for d in checklist_missing]
    invalid_set = {d.replace("_", " ").title() for d in invalid_docs}
    
    body_lines = [
        f"Dear {who},",
        "",
        "Thank you for your interest in banking with us. To complete your Know Your Customer (KYC) onboarding process and activate your corporate account, we require the following outstanding documentation and information:",
        "",
    ]
    
    body_lines.extend(["REQUIRED DOCUMENTS:", ""])
    if readable_required:
        for i, doc in enumerate(readable_required, 1):
            if doc in readable_missing_docs:
                status = "Missing"
            elif doc in invalid_set:
                status = "Received (not valid)"
            else:
                status = "Received"
            body_lines.append(f"{i}. {doc} — {status}")
        body_lines.append("")
    else:
        body_lines.extend([
            "- None - No checklist available for this case context",
        ])
        body_lines.append("")
    
    if readable_fields:
        body_lines.extend([
            "OUTSTANDING INFORMATION:",
            "",
        ])
        for i, field in enumerate(readable_fields, 1):
            body_lines.append(f"{i}. {field}")
        body_lines.append("")
    else:
        body_lines.extend([
            "OUTSTANDING INFORMATION:",
            "",
            "- None - All required information complete",
            "",
        ])

    if inconsistency_messages:
        body_lines.extend(["DOCUMENT VALIDITY ISSUES:", ""])
        for i, msg in enumerate(inconsistency_messages, 1):
            body_lines.append(f"{i}. {msg}")
        body_lines.append("")

    if extra_docs:
        body_lines.extend(["OTHER UPLOADED DOCUMENTS (not required for this case):", ""])
        for i, doc in enumerate(extra_docs, 1):
            body_lines.append(f"{i}. {doc.replace('_', ' ').title()}")
        body_lines.append("")
    
    body_lines.extend([
        "TIMELINE & NEXT STEPS:",
        "Upon receipt of all required documents and information, our KYC review team will complete the verification process within 2-3 business days. You will receive a confirmation email once your account is fully activated.",
        "",
        "IMPORTANT NOTICE:",
        "Please note that delays in providing the requested documentation may result in:",
        "- Delayed account activation",
        "- Temporary restrictions on transaction capabilities",
        "- Extended compliance review period",
        "",
        "We are committed to ensuring a smooth onboarding experience. If you have any questions or require assistance, please contact your Relationship Manager or reply to this email.",
        "",
        "We look forward to serving your banking needs.",
        "",
        "Best regards,",
        "",
        "KYC Onboarding Team",
        "Corporate Banking Division",
        "",
        "---",
        "This is an automated message. Please do not reply with sensitive information.",
    ])
    
    subject = f"Action Required: KYC Documentation - {who}"
    if jurisdiction:
        subject += f" [{jurisdiction}]"
    
    return OutreachEmail(subject=subject, body="\n".join(body_lines))


def draft_outreach_email(case_id: str) -> dict:
    with Session(engine) as session:
        case = session.get(Case, case_id)
        gaps = session.exec(select(GapItem).where(GapItem.case_id == case_id)).all()
        checklist = session.exec(select(ChecklistItem).where(ChecklistItem.case_id == case_id)).all()
        documents = session.exec(select(Document).where(Document.case_id == case_id)).all()

    checklist_required = [c.doc_type for c in checklist if c.required]
    checklist_missing = [c.doc_type for c in checklist if c.required and not c.satisfied]
    checklist_received = [c.doc_type for c in checklist if c.required and c.satisfied]

    missing_fields = [g.item_key for g in gaps if g.kind == "missing_field"]
    inconsistency_messages = [g.message for g in gaps if g.kind == "inconsistency"]
    invalid_docs = sorted({g.item_key.split(".")[0] for g in gaps if g.kind == "inconsistency" and g.item_key})
    uploaded_doc_types = sorted(
        {d.detected_doc_type for d in documents if d.detected_doc_type and d.detected_doc_type != "unknown"}
    )
    required_doc_set = set(checklist_required)
    extra_docs = sorted([dt for dt in uploaded_doc_types if dt not in required_doc_set])
    jurisdiction = case.jurisdiction if case else ""

    # Use fallback (no LLM) if no API key - it's now very professional
    if not settings.openai_api_key:
        email = _fallback_email(
            case.client_name if case else None,
            checklist_required=checklist_required,
            checklist_missing=checklist_missing,
            missing_fields=missing_fields,
            invalid_docs=invalid_docs,
            inconsistency_messages=inconsistency_messages,
            extra_docs=extra_docs,
            jurisdiction=jurisdiction,
        )
        return email.model_dump()

    # Use LLM for even better quality
    try:
        email = chat_json(
            settings.openai_model,
            system=system_outreach_email(),
            user=user_outreach_email(
                client_name=case.client_name if case else None,
                required_docs=checklist_required,
                received_docs=checklist_received,
                missing_docs=checklist_missing,
                missing_fields=missing_fields,
                invalid_docs=invalid_docs,
                inconsistency_messages=inconsistency_messages,
                extra_docs=extra_docs,
                jurisdiction=jurisdiction,
            ),
            out_model=OutreachEmail,
        )
        # Post-process to guarantee all gap categories are visible in the email,
        # even if the LLM omits some sections.
        body_l = (email.body or "").lower()

        if inconsistency_messages and "document validity issues" not in body_l:
            email.body = (
                email.body
                + "\n\nDOCUMENT VALIDITY ISSUES:\n"
                + "\n".join([f"- {m}" for m in inconsistency_messages])
            )

        if extra_docs and "other uploaded documents" not in body_l:
            email.body = (
                email.body
                + "\n\nOTHER UPLOADED DOCUMENTS (not required for this case):\n"
                + "\n".join([f"- {d.replace('_', ' ').title()}" for d in extra_docs])
            )

        # Ensure missing fields (missing_field gaps) are not lost.
        if missing_fields and "outstanding information" not in body_l:
            email.body = (
                email.body
                + "\n\nOUTSTANDING INFORMATION:\n"
                + "\n".join([f"- {f}" for f in missing_fields])
            )

        return email.model_dump()
    except Exception:
        # Fallback if LLM fails
        email = _fallback_email(
            case.client_name if case else None,
            checklist_required=checklist_required,
            checklist_missing=checklist_missing,
            missing_fields=missing_fields,
            invalid_docs=invalid_docs,
            inconsistency_messages=inconsistency_messages,
            extra_docs=extra_docs,
            jurisdiction=jurisdiction,
        )
        return email.model_dump()

