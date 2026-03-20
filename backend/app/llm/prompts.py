from __future__ import annotations


def system_doc_classifier() -> str:
    return (
        "You are a banking KYC document classifier. Classify documents based on their content and filename.\n\n"
        "RULES:\n"
        "1. Return ONLY valid JSON with keys: doc_type, confidence, rationale\n"
        "2. doc_type MUST be one of the provided candidate_doc_types or \"unknown\"\n"
        "3. Look for these indicators in the text:\n"
        "   - certificate_of_incorporation: 'Certificate of Incorporation', 'CIN', 'Company Registration'\n"
        "   - ubo_declaration: 'UBO', 'Beneficial Owner', 'Ultimate Beneficial'\n"
        "   - proof_of_address: 'Utility Bill', 'Address Proof', 'Electricity Bill', 'Service Address'\n"
        "   - board_resolution: 'Board Resolution', 'Resolution of the Board'\n"
        "   - directors_list: 'Directors List', 'Board of Directors', 'Company Profile'\n"
        "4. Confidence: 0.9 for clear match, 0.7 for partial match, <= 0.5 for uncertain\n"
        "5. Rationale: brief explanation of why you chose this type\n"
        "6. Use \"unknown\" if the document doesn't match any candidate type\n\n"
        "EXAMPLE:\n"
        'Input: text contains "Certificate of Incorporation" and "CIN: L12345"\n'
        'Output: {"doc_type": "certificate_of_incorporation", "confidence": 0.95, "rationale": "Contains Certificate of Incorporation and CIN number"}}'
    )


def user_doc_classifier(
    *,
    jurisdiction: str,
    entity_type: str,
    products: list[str],
    risk_tier: str,
    candidate_doc_types: list[str],
    document_text: str,
    hints: dict,
) -> str:
    # keep prompt compact to reduce cost; evidence is in text
    text = document_text[:12000]
    return (
        f"jurisdiction: {jurisdiction}\n"
        f"entity_type: {entity_type}\n"
        f"products: {products}\n"
        f"risk_tier: {risk_tier}\n"
        f"candidate_doc_types: {candidate_doc_types}\n"
        f"hints: {hints}\n"
        "document_text:\n"
        f"{text}\n"
    )


def system_field_extractor() -> str:
    return (
        "You are a precise KYC document field extractor for noisy real-world OCR text. "
        "Your task is to extract specific fields strictly from provided text.\n\n"
        "RULES:\n"
        "1. Return ONLY valid JSON with key 'fields'\n"
        "2. Each field must have: {value: string|null, evidence: string|null, confidence: number|null}\n"
        "3. Look for field names in the text (e.g., 'Company Name:', 'Address:', 'UBO Name:') and OCR variants\n"
        "4. The value should be the text AFTER the field name, not including the label\n"
        "5. Evidence must be the exact line from the document where you found the value\n"
        "6. Use null if field is not found in the text\n"
        "7. Confidence: 0.9 if exact match, 0.7 if partial/unclear, null if not found\n"
        "8. For addresses, capture the full multi-line address\n"
        "9. Do not invent values - only extract what's in the text\n"
        "10. Never output placeholder text such as 'Not found', '-', 'N/A' as a value; use null instead\n"
        "11. For PAN, return uppercase 10-char format (AAAAA9999A) without spaces when possible\n"
        "12. For name fields, avoid headers like 'Income Tax Department' and choose the actual entity/person name\n\n"
        "EXAMPLE:\n"
        'Input: "Company Name: TechVenture Solutions\\nAddress: 123 Main St"\n'
        'Output: {"fields": {"company_name": {"value": "TechVenture Solutions", "evidence": "Company Name: TechVenture Solutions", "confidence": 0.9}}}}'
    )


def user_field_extractor(*, doc_type: str, schema_fields: list[str], document_text: str) -> str:
    # Include more text for better context, but limit to avoid token limits
    text = document_text[:15000]
    return (
        f"DOCUMENT TYPE: {doc_type}\n"
        f"REQUIRED FIELDS TO EXTRACT: {', '.join(schema_fields)}\n\n"
        "INSTRUCTIONS:\n"
        "1. Search the document text below for each required field\n"
        "2. Field labels may be formatted as 'Field Name:', 'Field Name -', or just 'Field Name'\n"
        "3. Extract the value that appears AFTER the field label (or nearest reliable line)\n"
        "4. For addresses, include the full street, city, state, and postal code\n"
        "5. Return null if a field is not present in the document\n"
        "6. If OCR text is noisy, choose the most likely exact value and lower confidence accordingly\n"
        "7. Do not return placeholders like 'Not found' or '-'; return null instead\n\n"
        "DOCUMENT TEXT:\n"
        "---\n"
        f"{text}\n"
        "---\n\n"
        "Extract the fields and return as JSON."
    )


def system_gap_explainer() -> str:
    return (
        "Explain missing KYC requirements strictly using the provided policy_excerpts. "
        "Return JSON only with key: items. "
        "Each item is {item, why, citations}. citations is a list of source_id values. "
        "If policy_excerpts do not support an explanation, say so and leave citations empty. "
        "Do not add extra keys."
    )


def user_gap_explainer(*, missing_items: list[str], policy_excerpts: list[dict]) -> str:
    return (
        f"missing_items: {missing_items}\n"
        f"policy_excerpts: {policy_excerpts}\n"
    )


def system_outreach_email() -> str:
    return (
        "You are a senior KYC onboarding specialist at a major international bank. "
        "Draft a formal, professional email to a corporate client regarding outstanding KYC requirements.\n\n"
        "EMAIL STRUCTURE:\n"
        "1. Professional greeting with client name\n"
        "2. Opening paragraph acknowledging relationship/reference number\n"
        "3. Section: 'Required Documents' - list each required document and mark it as Received, Missing, or Not Valid\n"
        "4. Section: 'Document Validity Issues' - list issues for any uploaded documents that are present but not valid (e.g., name mismatch, invalid PAN/CIN/ID format)\n"
        "5. Section: 'Outstanding Information' - list missing fields in plain language\n"
        "6. Section: 'Other Uploaded Documents' - list any uploaded document types that are not required for this case context (if provided)\n"
        "7. Section: 'Timeline & Next Steps' - explain what happens when they submit\n"
        "8. Section: 'Important Notice' - brief mention of consequences if delayed (regulatory hold, account limitations)\n"
        "9. Professional closing with contact information\n\n"
        "RULES:\n"
        "1. Return ONLY valid JSON with keys: subject, body\n"
        "2. Use formal business language throughout\n"
        "3. Do not use technical field names like 'ubo_declaration.ubo_dob' - convert to 'UBO date of birth'\n"
        "4. Be specific about what is needed and why\n"
        "5. Mention that delays may result in: account opening delays, transaction limitations, or regulatory compliance holds\n"
        "6. Provide clear submission instructions\n"
        "7. Include estimated timeline for review once documents are received\n"
        "8. Add escalation contact for urgent matters\n\n"
        "9. Ensure the email body includes clearly labeled sections: 'Required Documents', 'Document Validity Issues' (if any), 'Outstanding Information', and 'Other Uploaded Documents' (if any).\n\n"
        "EXAMPLE OUTPUT:\n"
        '{"subject": "KYC Documentation Required - [Company Name] Account Opening", '
        '"body": "Dear [Client Name],\\n\\nThank you for choosing [Bank Name] for your banking needs..."}'
    )


def user_outreach_email(
    *,
    client_name: str | None,
    required_docs: list[str],
    received_docs: list[str],
    missing_docs: list[str],
    missing_fields: list[str],
    invalid_docs: list[str],
    inconsistency_messages: list[str],
    extra_docs: list[str],
    jurisdiction: str = "",
) -> str:
    # Convert technical field names to human-readable format
    field_descriptions = {
        "certificate_of_incorporation.registered_address": "Registered business address (as shown on Certificate of Incorporation)",
        "certificate_of_incorporation.company_name": "Legal company name",
        "certificate_of_incorporation.registration_number": "Company registration number / CIN",
        "certificate_of_incorporation.incorporation_date": "Date of company incorporation",
        "ubo_declaration.entity_name": "Entity name on UBO declaration",
        "ubo_declaration.ubo_name": "Ultimate Beneficial Owner full name",
        "ubo_declaration.ubo_dob": "UBO date of birth (for identity verification)",
        "ubo_declaration.ubo_nationality": "UBO nationality",
        "proof_of_address.entity_name": "Entity name on address proof",
        "proof_of_address.registered_address": "Current registered address proof",
        "directors_list.company_name": "Company name on directors list",
        "directors_list.directors": "List of current directors with their designations",
        "board_resolution.company_name": "Company name on board resolution",
        "board_resolution.resolution_date": "Date of board resolution (must be within last 6 months)",
    }
    
    # Convert missing fields to readable format
    readable_fields = []
    for field in missing_fields:
        if field in field_descriptions:
            readable_fields.append(field_descriptions[field])
        else:
            # Convert snake_case to readable format
            readable = field.replace("_", " ").replace(".", " - ").title()
            readable_fields.append(readable)
    
    def _readable_doc(d: str) -> str:
        return d.replace("_", " ").title()

    readable_required_docs = [_readable_doc(d) for d in required_docs]
    readable_received_docs = [_readable_doc(d) for d in received_docs]
    readable_missing_docs = [_readable_doc(d) for d in missing_docs]
    readable_invalid_docs = [_readable_doc(d) for d in invalid_docs]
    readable_extra_docs = [_readable_doc(d) for d in extra_docs]
    
    return (
        f"CLIENT INFORMATION:\n"
        f"- Client Name: {client_name or 'Valued Client'}\n"
        f"- Jurisdiction: {jurisdiction or 'Multi-jurisdiction'}\n"
        f"- Account Type: Corporate Banking\n\n"
        f"REQUIRED DOCUMENTS ({len(readable_required_docs)}):\n"
        f"{chr(10).join(['- ' + d for d in readable_required_docs]) if readable_required_docs else '- None - No checklist available'}\n\n"
        f"RECEIVED DOCUMENTS ({len(readable_received_docs)}):\n"
        f"{chr(10).join(['- ' + d for d in readable_received_docs]) if readable_received_docs else '- None -'}\n\n"
        f"MISSING REQUIRED DOCUMENTS ({len(readable_missing_docs)}):\n"
        f"{chr(10).join(['- ' + d for d in readable_missing_docs]) if readable_missing_docs else '- None - All required documents received'}\n\n"
        f"INVALID (NOT VALID) UPLOADED DOCUMENTS ({len(readable_invalid_docs)}):\n"
        f"{chr(10).join(['- ' + d for d in readable_invalid_docs]) if readable_invalid_docs else '- None - No invalid documents detected'}\n\n"
        f"DOCUMENT VALIDITY ISSUES ({len(inconsistency_messages)}):\n"
        f"{chr(10).join(['- ' + msg for msg in inconsistency_messages]) if inconsistency_messages else '- None -'}\n\n"
        f"OTHER UPLOADED DOCUMENTS NOT REQUIRED ({len(readable_extra_docs)}):\n"
        f"{chr(10).join(['- ' + d for d in readable_extra_docs]) if readable_extra_docs else '- None -'}\n\n"
        f"MISSING INFORMATION/DATA FIELDS ({len(readable_fields)}):\n"
        f"{chr(10).join(['- ' + f for f in readable_fields]) if readable_fields else '- None - All required information complete'}\n\n"
        f"TONE REQUIREMENTS:\n"
        f"- Professional and courteous\n"
        f"- Clear and specific about requirements\n"
        f"- Emphasize importance of timely submission\n"
        f"- Mention regulatory compliance requirements\n"
        f"- Provide helpful guidance on submission\n\n"
        f"IMPORTANT: In the email body, include a section titled 'Required Documents' listing each required doc and marking it as Received or Missing.\n"
        f"Also include a section titled 'Document Validity Issues' if there are any invalid/not-valid documents.\n"
        f"Also include a section titled 'Outstanding Information' for missing fields.\n"
        f"Also include a section titled 'Other Uploaded Documents' if there are other uploaded docs not required.\n"
        f"Generate a formal business email with subject line and body."
    )

