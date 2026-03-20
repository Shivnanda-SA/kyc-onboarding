from __future__ import annotations

import logging
from datetime import datetime

from sqlmodel import Session, delete, select

logger = logging.getLogger(__name__)

from ..rules.engine import evaluate_case
from ..storage import (
    AuditEvent,
    Case,
    CaseStatus,
    ChecklistItem,
    Document,
    ExtractionRun,
    ExtractedField,
    GapItem,
    engine,
)
from ..utils import json_dumps, new_id
from .extract_and_map import extract_and_map_documents


def process_case(case_id: str, run_id: str) -> None:
    with Session(engine) as session:
        run = session.get(ExtractionRun, run_id)
        case = session.get(Case, case_id)
        if not run or not case:
            return

    try:
        with Session(engine) as session:
            session.exec(delete(ExtractedField).where(ExtractedField.case_id == case_id))
            session.exec(delete(GapItem).where(GapItem.case_id == case_id))
            session.exec(delete(ChecklistItem).where(ChecklistItem.case_id == case_id))
            session.commit()

        extract_and_map_documents(case_id=case_id)
        evaluate_case(case_id=case_id)

        with Session(engine) as session:
            case = session.get(Case, case_id)
            run = session.get(ExtractionRun, run_id)
            if case:
                case.status = CaseStatus.complete.value
                case.updated_at = datetime.utcnow()
                session.add(case)
            if run:
                run.status = "complete"
                run.finished_at = datetime.utcnow()
                session.add(run)
            session.add(
                AuditEvent(
                    id=new_id("audit"),
                    case_id=case_id,
                    event_type="processing_complete",
                    payload_json=json_dumps({"run_id": run_id}),
                )
            )
            session.commit()
    except Exception as e:  # noqa: BLE001
        logger.exception("Processing failed for case %s: %s", case_id, e)
        with Session(engine) as session:
            case = session.get(Case, case_id)
            run = session.get(ExtractionRun, run_id)
            if case:
                case.status = CaseStatus.failed.value
                case.updated_at = datetime.utcnow()
                session.add(case)
            if run:
                run.status = "failed"
                run.error = repr(e)
                run.finished_at = datetime.utcnow()
                session.add(run)
            session.add(
                AuditEvent(
                    id=new_id("audit"),
                    case_id=case_id,
                    event_type="processing_failed",
                    payload_json=json_dumps({"run_id": run_id, "error": repr(e)}),
                )
            )
            session.commit()

