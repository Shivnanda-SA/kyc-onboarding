from __future__ import annotations

import logging
from pathlib import Path

from sqlmodel import Session, select

from ..extraction.pipeline import extract_text_from_file
from ..llm.extract import classify_doc_type, extract_fields_for_doc
from ..rules.loader import load_country_rules
from ..storage import AuditEvent, Case, Document, ExtractedField, engine
from ..utils import json_dumps, new_id

logger = logging.getLogger(__name__)


def extract_and_map_documents(case_id: str) -> None:
    with Session(engine) as session:
        case = session.get(Case, case_id)
        docs = session.exec(select(Document).where(Document.case_id == case_id)).all()

    # Use the case jurisdiction to avoid cross-country misclassification.
    jurisdiction = (case.jurisdiction if case else "IN").upper()
    rules = load_country_rules(jurisdiction)
    candidate_doc_types = sorted(rules.doc_types.keys())

    for doc in docs:
        logger.info(f"Processing document {doc.id}: {doc.filename}")
        file_path = Path(doc.stored_path)
        extracted = extract_text_from_file(file_path)
        logger.info(f"Extracted {len(extracted.text)} chars using {extracted.method}")
        
        detected = classify_doc_type(
            candidate_doc_types=candidate_doc_types,
            document_text=extracted.text,
            hints={"filename": doc.filename},
            jurisdiction=jurisdiction,
            entity_type=(case.entity_type if case else "company"),
            products=[],
            risk_tier=(case.risk_tier if case else "medium"),
        )
        logger.info(f"Classified as: {detected.doc_type} (confidence: {detected.confidence}, rationale: {detected.rationale})")
        
        # Schema fields from the case jurisdiction rules only
        doc_spec = rules.doc_types.get(detected.doc_type)
        schema_fields = list(doc_spec.fields.keys()) if doc_spec else []
        logger.info(f"Schema fields to extract: {schema_fields}")
        
        fields = extract_fields_for_doc(
            doc_type=detected.doc_type,
            schema_fields=schema_fields,
            document_text=extracted.text,
        )
        
        # Log extracted fields
        extracted_summary = {k: v.value for k, v in fields.fields.items() if v.value}
        logger.info(f"Extracted fields: {extracted_summary}")

        with Session(engine) as session:
            doc_db = session.get(Document, doc.id)
            if doc_db:
                doc_db.detected_doc_type = detected.doc_type
                doc_db.detected_doc_confidence = float(detected.confidence)
                doc_db.detected_doc_rationale = detected.rationale
                session.add(doc_db)
            for fname, fobj in fields.fields.items():
                session.add(
                    ExtractedField(
                        id=new_id("field"),
                        case_id=case_id,
                        document_id=doc.id,
                        doc_type=detected.doc_type,
                        field_name=fname,
                        value=fobj.value,
                        evidence=fobj.evidence,
                        confidence=fobj.confidence,
                    )
                )
            session.add(
                AuditEvent(
                    id=new_id("audit"),
                    case_id=case_id,
                    event_type="document_extracted",
                    payload_json=json_dumps(
                        {
                            "document_id": doc.id,
                            "doc_type": detected.doc_type,
                            "chars": len(extracted.text),
                        }
                    ),
                )
            )
            session.commit()

