from __future__ import annotations

import json
import logging
import re
from datetime import datetime

from sqlmodel import Session, select

from ..storage import ChecklistItem, Document, ExtractedField, GapItem, engine
from ..utils import new_id
from .loader import load_country_rules

logger = logging.getLogger(__name__)


def _parse_products(products_json: str) -> list[str]:
    try:
        v = json.loads(products_json)
        if isinstance(v, list):
            return [str(x) for x in v]
    except Exception:  # noqa: BLE001
        pass
    return []


def _norm_name(v: str | None) -> str:
    if not v:
        return ""
    return re.sub(r"[^A-Z0-9]", "", v.upper())


def _parse_date(v: str) -> bool:
    value = v.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


def _is_valid_field_value(field_name: str, value: str, country: str) -> bool:
    v = value.strip()
    if not v:
        return False
    if field_name == "pan":
        return re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", re.sub(r"\s+", "", v).upper()) is not None
    if field_name == "llpin":
        vv = re.sub(r"\s+", "", v).upper()
        return re.fullmatch(r"[A-Z]{3}-?\d{4}", vv) is not None
    if field_name == "registration_number":
        vv = re.sub(r"\s+", "", v).upper()
        if country == "IN":
            # CIN pattern
            if re.fullmatch(r"L\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}", vv):
                return True
        if country == "SG":
            # UEN (common forms)
            if re.fullmatch(r"[Tt]\d{2}[A-Z]{2}\d{5}[A-Z]?", vv):
                return True
        # allow generic alnum registration IDs for flexibility
        return re.fullmatch(r"[A-Z0-9\-]{6,25}", vv) is not None
    if field_name in {"incorporation_date", "resolution_date", "authorization_date", "effective_date", "ubo_dob"}:
        return _parse_date(v)
    if field_name == "ownership_percent":
        nums = re.findall(r"\d+(?:\.\d+)?", v)
        if not nums:
            return False
        p = float(nums[0])
        return 0.0 <= p <= 100.0
    return True


def evaluate_case(case_id: str) -> None:
    from ..storage import Case  # avoid cycle

    with Session(engine) as session:
        case = session.get(Case, case_id)
        if not case:
            logger.error(f"Case {case_id} not found for evaluation")
            return
        
        country = case.jurisdiction.upper()
        entity_type = case.entity_type
        risk_tier = case.risk_tier
        products = _parse_products(case.products_json)
        
        logger.info(f"Evaluating case {case_id}: country={country}, entity={entity_type}, risk={risk_tier}, products={products}")
        
        rules = load_country_rules(country)
        required_docs = rules.required_docs_for(entity_type=entity_type, products=products, risk_tier=risk_tier)
        
        logger.info(f"Required documents for {country}: {required_docs}")

        docs = session.exec(select(Document).where(Document.case_id == case_id)).all()
        docs_by_type: dict[str, Document] = {}
        for d in docs:
            if d.detected_doc_type and d.detected_doc_type != "unknown":
                docs_by_type.setdefault(d.detected_doc_type, d)
        
        logger.info(f"Uploaded documents by type: {list(docs_by_type.keys())}")

        # Checklist
        checklist_count = 0
        for dt in required_docs:
            doc = docs_by_type.get(dt)
            session.add(
                ChecklistItem(
                    id=new_id("chk"),
                    case_id=case_id,
                    doc_type=dt,
                    required=True,
                    satisfied=doc is not None,
                    satisfied_by_document_id=doc.id if doc else None,
                    created_at=datetime.utcnow(),
                )
            )
            checklist_count += 1
        
        logger.info(f"Created {checklist_count} checklist items")

        # Missing documents
        missing_docs_count = 0
        for dt in required_docs:
            if dt not in docs_by_type:
                doc_spec = rules.doc_types.get(dt)
                title = doc_spec.title if doc_spec else dt
                session.add(
                    GapItem(
                        id=new_id("gap"),
                        case_id=case_id,
                        kind="missing_doc",
                        item_key=dt,
                        severity="high",
                        message=f"Missing required document: {title}",
                        created_at=datetime.utcnow(),
                    )
                )
                missing_docs_count += 1
        
        logger.info(f"Created {missing_docs_count} missing document gaps")

        # Missing fields per doc present
        fields = session.exec(select(ExtractedField).where(ExtractedField.case_id == case_id)).all()
        fields_by_doc_type: dict[str, dict[str, ExtractedField]] = {}
        for f in fields:
            fields_by_doc_type.setdefault(f.doc_type, {})[f.field_name] = f
        
        logger.info(f"Extracted fields by doc type: { {k: list(v.keys()) for k, v in fields_by_doc_type.items()} }")

        missing_fields_count = 0
        invalid_fields_count = 0
        # Only enforce required fields for documents that are required for this case AND present.
        for dt in required_docs:
            if dt not in docs_by_type:
                continue
            doc_spec = rules.doc_types.get(dt)
            if not doc_spec:
                continue
            extracted = fields_by_doc_type.get(dt, {})
            for fname, spec in doc_spec.fields.items():
                if not spec.required:
                    continue
                val = extracted.get(fname).value if fname in extracted else None
                if val is None or not str(val).strip():
                    session.add(
                        GapItem(
                            id=new_id("gap"),
                            case_id=case_id,
                            kind="missing_field",
                            item_key=f"{dt}.{fname}",
                            severity="medium",
                            message=f"Missing required field `{fname}` in `{doc_spec.title}`",
                            created_at=datetime.utcnow(),
                        )
                    )
                    missing_fields_count += 1
                elif not _is_valid_field_value(fname, str(val), country):
                    session.add(
                        GapItem(
                            id=new_id("gap"),
                            case_id=case_id,
                            kind="inconsistency",
                            item_key=f"{dt}.{fname}",
                            severity="high" if fname in {"pan", "registration_number", "llpin"} else "medium",
                            message=f"Field `{fname}` in `{doc_spec.title}` appears invalid: `{val}`",
                            created_at=datetime.utcnow(),
                        )
                    )
                    invalid_fields_count += 1
        
        logger.info(f"Created {missing_fields_count} missing field gaps")
        logger.info(f"Created {invalid_fields_count} invalid field gaps")

        # Cross-document entity consistency checks (prevents accepting unrelated docs).
        name_fields = {
            "entity_name",
            "company_name",
            "llp_name",
            "firm_name",
            "trust_name",
            "business_name",
        }
        names_by_doc: dict[str, str] = {}
        for dt in required_docs:
            extracted = fields_by_doc_type.get(dt, {})
            for nf in name_fields:
                val = extracted.get(nf).value if nf in extracted else None
                if val and str(val).strip():
                    names_by_doc[dt] = str(val).strip()
                    break

        canonical_raw = (case.client_name or "").strip()
        if not canonical_raw and names_by_doc:
            canonical_raw = max(names_by_doc.values(), key=len)
        canonical = _norm_name(canonical_raw)

        inconsistency_count = 0
        if canonical:
            for dt, raw_name in names_by_doc.items():
                nn = _norm_name(raw_name)
                if not nn:
                    continue
                # relaxed match to tolerate OCR noise, but still catch unrelated entities
                if canonical != nn and canonical not in nn and nn not in canonical:
                    session.add(
                        GapItem(
                            id=new_id("gap"),
                            case_id=case_id,
                            kind="inconsistency",
                            item_key=f"{dt}.entity_name",
                            severity="high",
                            message=(
                                f"Entity name mismatch in `{dt}`. "
                                f"Expected similar to `{canonical_raw}`, found `{raw_name}`."
                            ),
                            created_at=datetime.utcnow(),
                        )
                    )
                    inconsistency_count += 1
        logger.info(f"Created {inconsistency_count} cross-document inconsistency gaps")

        session.commit()
        logger.info(f"Evaluation complete for case {case_id}")

