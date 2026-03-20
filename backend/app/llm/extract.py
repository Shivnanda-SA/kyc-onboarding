from __future__ import annotations

import re
from dataclasses import dataclass

from ..settings import settings
from .client import chat_json
from .prompts import (
    system_doc_classifier,
    system_field_extractor,
    user_doc_classifier,
    user_field_extractor,
)
from .schemas import DocClassification, ExtractedFields, FieldValue


def _is_placeholder_value(v: str | None) -> bool:
    if v is None:
        return True
    s = v.strip().lower()
    if not s:
        return True
    placeholders = {
        "-",
        "--",
        "n/a",
        "na",
        "none",
        "null",
        "not found",
        "not available",
        "unknown",
    }
    return s in placeholders


def _looks_low_quality(field: str, v: str | None, confidence: float | None) -> bool:
    if _is_placeholder_value(v):
        return True
    if confidence is not None and confidence < 0.65:
        return True
    val = (v or "").strip()
    if field in {"entity_name", "company_name", "llp_name", "firm_name", "trust_name"} and len(val) < 4:
        return True
    if field == "pan" and re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", re.sub(r"\s+", "", val).upper()) is None:
        return True
    return False


def _heuristic_doc_type(candidate_doc_types: list[str], text: str, hints: dict) -> DocClassification:
    """Use filename and content patterns to classify documents."""
    filename = hints.get("filename", "").lower()
    content = text[:3000].lower()
    
    # Filename-based detection (strong signal)
    filename_patterns = {
        "certificate_of_incorporation": ["incorporation", "coi", "certificate", "company_registration"],
        "llp_incorporation_certificate": ["llp", "llpin", "incorporation", "registration", "certificate"],
        "ubo_declaration": ["ubo", "beneficial", "ownership"],
        "proof_of_address": ["address", "utility", "bill", "electricity", "water"],
        "board_resolution": ["board", "resolution"],
        "directors_list": ["director", "company_profile", "profile"],
        "pan_card": ["pan", "permanent_account", "tax", "income_tax"],
        "moa_aoa": ["moa", "aoa", "memorandum", "articles"],
        "llp_agreement": ["llp_agreement", "llp deed", "agreement"],
        "authorization_letter": ["authorization", "authorisation", "authorize", "account_opening"],
        "partner_list": ["partner", "partners", "designated_partner"],
    }
    
    # Check filename first
    for doc_type, keywords in filename_patterns.items():
        if doc_type in candidate_doc_types:
            if any(kw in filename for kw in keywords):
                return DocClassification(doc_type=doc_type, confidence=0.8, rationale=f"filename_match:{filename}")
    
    # Content-based detection
    content_patterns = [
        ("certificate_of_incorporation", ["certificate of incorporation", "incorporation certificate", "cin:", "company identification"]),
        ("llp_incorporation_certificate", ["llp identification number", "llpin", "certificate of incorporation (llp)", "incorporation certificate (llp)"]),
        ("ubo_declaration", ["ultimate beneficial owner", "beneficial owner declaration", "ubo name"]),
        ("proof_of_address", ["utility bill", "electricity bill", "water bill", "service address", "proof of address"]),
        ("board_resolution", ["board resolution", "resolution of the board", "authorized signatories"]),
        ("directors_list", ["board of directors", "directors:", "director name", "date appointed"]),
        ("pan_card", ["permanent account number", "income tax department", "pan:"]),
        ("moa_aoa", ["memorandum of association", "articles of association", "objects clause", "registered office clause"]),
        ("llp_agreement", ["llp agreement", "partners:", "designated partner"]),
        ("authorization_letter", ["authorization letter", "we authorize", "authorized signatory", "account opening"]),
    ]
    
    for dt, keys in content_patterns:
        if dt in candidate_doc_types and any(k in content for k in keys):
            return DocClassification(doc_type=dt, confidence=0.7, rationale="content_match")
    
    return DocClassification(doc_type="unknown", confidence=0.3, rationale="no_match")


def classify_doc_type(
    *,
    candidate_doc_types: list[str],
    document_text: str,
    hints: dict,
    jurisdiction: str = "IN",
    entity_type: str = "company",
    products: list[str] | None = None,
    risk_tier: str = "medium",
) -> DocClassification:
    """Classify document using heuristics first, then LLM if available and needed."""
    products = products or []
    
    # Always try heuristics first - they're more reliable for filename patterns
    heuristic = _heuristic_doc_type(candidate_doc_types, document_text, hints)
    
    # If heuristic has high confidence, use it directly
    if heuristic.confidence >= 0.7:
        return heuristic
    
    # If no LLM, return heuristic result (even if low confidence)
    if not settings.openai_api_key:
        return heuristic
    
    # Use LLM for ambiguous cases or to refine
    try:
        llm_result = chat_json(
            settings.openai_model,
            system=system_doc_classifier(),
            user=user_doc_classifier(
                jurisdiction=jurisdiction,
                entity_type=entity_type,
                products=products,
                risk_tier=risk_tier,
                candidate_doc_types=candidate_doc_types,
                document_text=document_text,
                hints=hints,
            ),
            out_model=DocClassification,
        )
        # Prefer LLM if it has reasonable confidence
        if llm_result.confidence >= 0.6 and llm_result.doc_type != "unknown":
            return llm_result
        # Otherwise fall back to heuristic
        return heuristic if heuristic.doc_type != "unknown" else llm_result
    except Exception:
        # LLM failed, fall back to heuristic
        return heuristic


def _heuristic_fields(schema_fields: list[str], text: str) -> ExtractedFields:
    """Extract fields using regex patterns as fallback when LLM fails."""
    out: dict[str, FieldValue] = {f: FieldValue(value=None, evidence=None, confidence=None) for f in schema_fields}
    normalized_text = re.sub(r"[ \t]+", " ", text).strip()

    def pick(pattern: str, multiline: bool = True) -> tuple[str | None, str | None]:
        flags = re.IGNORECASE | (re.MULTILINE if multiline else 0)
        m = re.search(pattern, normalized_text, flags=flags)
        if not m:
            return None, None
        v = m.group(1).strip() if m.group(1) else m.group(0).strip()
        # Clean up the value
        v = v.replace('\n', ' ').replace('  ', ' ').strip()
        # Get evidence (the matching line)
        lines = text.split('\n')
        for line in lines:
            if m.group(0)[:50] in line or m.group(0) in line:
                return v, line.strip()[:200]
        return v, m.group(0)[:200]

    # More flexible patterns to match various document formats
    patterns = {
        "entity_name": [
            r"(?:Entity|Customer|Company|LLP)\s*Name[:\s]+([^\n]+?)(?=\n|Registration|CIN|LLPIN|PAN|$)",
            r"(?:Name\s*of\s*Assessee|Assessee\s*Name|Name)[:\s]+([^\n]{3,120})",
            r"(?:Name\s*of\s*(?:Company|Entity))[:\s]+([^\n]{3,120})",
        ],
        "llp_name": [
            r"(?:LLP)\s*Name[:\s]+([^\n]+?)(?=\n|LLPIN|Registration|$)",
        ],
        "llpin": [
            r"(?:LLPIN|LLP\s*ID(?:entification)?\s*No\.?)[:\s]+([A-Z0-9\-]+)",
            r"\b(AAC-\d{4})\b",
        ],
        "pan": [
            r"(?:PAN|Permanent\s*Account\s*Number)[:\s]+([A-Z]{5}\d{4}[A-Z])\b",
            r"\b([A-Z]{5}\s*[\-\s]*\d{4}\s*[\-\s]*[A-Z])\b",
            r"\b([A-Z]{5}[\-\s]*\d{4}[\-\s]*[A-Z])\b",
        ],
        "company_name": [
            r"Company\s*Name[:\s]+([^\n]+?)(?=\n|Registration|CIN|$)",
            r"Customer[:\s]+([^\n]+?)(?=\n|$)",
        ],
        "registration_number": [
            r"(?:Registration\s*(?:No\.?|Number)|CIN|UEN)[:\s]+([A-Z0-9\-]+)",
            r"\b(L\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b",  # India CIN format
            r"\b(T\d{2}[A-Z]\d{5})\b",  # Singapore UEN format
        ],
        "incorporation_date": [
            r"(?:Incorporation\s*)?(?:Date\s*of\s*Incorporation|Incorporation\s*Date)[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})",
            r"Date\s*of\s*Issue[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})",
        ],
        "registered_address": [
            r"(?:Registered\s*)?(?:Address|Office)[:\s]+([^\n]+(?:\n[^A-Z][^\n]*)*?)(?=\s*\n\s*\n|\n[A-Z]|Phone|Email|$)",
            r"Service\s*Address[:\s]+([^\n]+(?:\n[^A-Z][^\n]*)*?)(?=\s*\n\s*\n|\n[A-Z]|Bill|$)",
            r"Address[:\s]+([^\n]+(?:\n[^A-Z][^\n]*){0,3})(?=\n|$)",
        ],
        "registered_office": [
            r"Registered\s*Office(?:\s*Address)?[:\s]+([^\n]+(?:\n[^A-Z][^\n]*)*?)(?=\s*\n\s*\n|\n[A-Z]|Clause|$)",
        ],
        "ubo_name": [
            r"(?:UBO\s*)?(?:Name|Full\s*Name)[:\s]+([A-Za-z\s\.]+)(?=\n|DOB|Nationality|$)",
            r"UBO\s*Name[:\s]+([A-Za-z\s\.]+)",
            r"Beneficial\s*Owner[:\s]+([A-Za-z\s\.]+)",
        ],
        "ubo_dob": [
            r"(?:UBO\s*)?(?:DOB|Date\s*of\s*Birth|Birth\s*Date)[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})",
            r"DOB[:\s]+([\d\-/]+)",
        ],
        "ubo_nationality": [
            r"(?:UBO\s*)?(?:Nationality)[:\s]+([A-Za-z\s]+)(?=\n|DOB|$)",
            r"Nationality[:\s]+([A-Za-z]+)",
        ],
        "ownership_percent": [
            r"(?:Ownership\s*%|Ownership\s*Percent|Ownership\s*Percentage)[:\s]+(\d{1,3}(?:\.\d+)?)\s*%?",
            r"(?:Percentage\s*of\s*Ownership|Percent\s*of\s*Ownership)[:\s]+(\d{1,3}(?:\.\d+)?)\s*%?",
            r"(?:Holding\s*%|Share\s*Holding)[:\s]+(\d{1,3}(?:\.\d+)?)\s*%?",
        ],
        "resolution_date": [
            r"(?:Date\s*of\s*)?Resolution[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})",
            r"Date[:\s]+(\d{4}-\d{2}-\d{2})",
        ],
        "authorization_date": [
            r"(?:Date)[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})",
        ],
        "effective_date": [
            r"(?:Effective\s*Date|Dated)[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})",
        ],
        "partners": [
            r"(?:Partners|Designated\s*Partners)[:\s]+(.+?)(?=\n\n|\n[A-Z]|Date|$)",
        ],
        "authorized_signatories": [
            r"(?:Authorized\s*Signatories|Authorized\s*Signatory|Signatories)[:\s]+(.+?)(?=\n\n|\n[A-Z]|$)",
        ],
        "directors": [
            r"(?:Board\s*of\s*)?Directors?[:\s]+(.+?)(?=\n\n|\n[A-Z]|Date|$)",
            r"Name\s*\|\s*Designation\s*\|\s*Date[^|]+\n(.+?)(?=\n\n|$)",  # Table format
        ],
    }
    
    for field in schema_fields:
        if field in patterns:
            for pattern in patterns[field]:
                v, ev = pick(pattern)
                if v and len(v) > 1:  # Ensure value is not empty
                    if field == "pan":
                        v = re.sub(r"\s+", "", v).upper()
                    out[field] = FieldValue(value=v, evidence=ev, confidence=0.6)
                    break

    # Robust PAN fallback: OCR often inserts spaces between characters.
    if "pan" in schema_fields and (out["pan"].value is None or not str(out["pan"].value).strip()):
        cleaned = "".join(ch for ch in normalized_text.upper() if ch.isalnum())
        m = re.search(r"([A-Z]{5}\d{4}[A-Z])", cleaned)
        if m:
            pan = m.group(1)
            out["pan"] = FieldValue(value=pan, evidence=pan, confidence=0.55)

    # PAN docs in real data often have sparse labels; derive entity_name from nearby lines if PAN exists.
    if "entity_name" in schema_fields and (out["entity_name"].value is None or not str(out["entity_name"].value).strip()):
        pan_val = out.get("pan").value if "pan" in out else None
        if pan_val:
            lines = [ln.strip() for ln in normalized_text.split("\n") if ln.strip()]
            header_tokens = {
                "income tax department",
                "government of india",
                "permanent account number",
                "name",
                "card",
            }
            # OCR sometimes prints PAN with spaces/hyphens/special separators.
            # Normalize each line to alphanumeric-only before matching.
            pan_idx = -1
            for i, ln in enumerate(lines):
                norm_ln = re.sub(r"[^A-Z0-9]", "", ln.upper())
                if pan_val in norm_ln:
                    pan_idx = i
                    break
            if pan_idx > 0:
                # Try candidates before PAN first...
                for j in range(pan_idx - 1, max(-1, pan_idx - 6), -1):
                    candidate = lines[j]
                    lc = candidate.lower()
                    if len(candidate) < 3:
                        continue
                    if any(tok in lc for tok in header_tokens):
                        continue
                    out["entity_name"] = FieldValue(value=candidate, evidence=candidate[:200], confidence=0.55)
                    break

                # ...then try after PAN. Many PAN layouts have Name below the PAN token.
                if out["entity_name"].value is None or not str(out["entity_name"].value).strip():
                    for j in range(pan_idx + 1, min(len(lines), pan_idx + 7)):
                        candidate = lines[j]
                        lc = candidate.lower()
                        if len(candidate) < 3:
                            continue
                        if any(tok in lc for tok in header_tokens):
                            continue
                        # Avoid obvious date/number-only lines
                        if re.fullmatch(r"\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}", candidate.strip()):
                            continue
                        out["entity_name"] = FieldValue(value=candidate, evidence=candidate[:200], confidence=0.55)
                        break
    
    return ExtractedFields(fields=out)


def extract_fields_for_doc(*, doc_type: str, schema_fields: list[str], document_text: str) -> ExtractedFields:
    """Extract fields using heuristics first, then LLM refinement for weak fields."""
    if not schema_fields:
        return ExtractedFields(fields={})
    
    # Always start with heuristics - more reliable for structured docs
    heuristic_result = _heuristic_fields(schema_fields, document_text)
    
    # If no LLM or all fields found, return heuristic result
    if not settings.openai_api_key:
        return heuristic_result
    
    # Ask LLM for fields that are missing OR weak from heuristics.
    llm_target_fields = []
    for f, fv in heuristic_result.fields.items():
        if _looks_low_quality(f, fv.value, fv.confidence):
            llm_target_fields.append(f)
    
    # If heuristics are already good enough, return immediately.
    if not llm_target_fields:
        return heuristic_result
    
    # Use LLM for weak fields and merge with quality preference.
    try:
        llm_result = chat_json(
            settings.openai_model,
            system=system_field_extractor(),
            user=user_field_extractor(doc_type=doc_type, schema_fields=llm_target_fields, document_text=document_text),
            out_model=ExtractedFields,
        )
        
        # Merge: keep heuristic for strong fields, replace weak fields with confident LLM values.
        merged = dict(heuristic_result.fields)
        for field, value in llm_result.fields.items():
            if field not in merged:
                continue
            if _is_placeholder_value(value.value):
                continue
            base = merged[field]
            if _looks_low_quality(field, base.value, base.confidence):
                merged[field] = value
                continue
            # If both present, prefer higher-confidence extraction.
            if (value.confidence or 0.0) > (base.confidence or 0.0) + 0.15:
                merged[field] = value
        
        return ExtractedFields(fields=merged)
    except Exception:
        # LLM failed, return heuristic result
        return heuristic_result

