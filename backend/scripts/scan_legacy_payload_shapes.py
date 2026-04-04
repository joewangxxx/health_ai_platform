import json
import sys
from pathlib import Path

from sqlmodel import Session, select

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import engine
from backend.models import HealthRecord, MedicalDocument, UserProfile
from backend.services.payload_normalization import scan_legacy_payload_shapes


def collect_payload_rows(session: Session):
    rows = []

    for document in session.exec(select(MedicalDocument)).all():
        rows.append(
            {
                "entity": "MedicalDocument",
                "id": document.id,
                "payload": document.ocr_summary,
            }
        )

    for record in session.exec(select(HealthRecord)).all():
        rows.append(
            {
                "entity": "HealthRecord",
                "id": record.id,
                "payload": record.risk_snapshot,
            }
        )

    for profile in session.exec(select(UserProfile)).all():
        rows.append(
            {
                "entity": "UserProfile",
                "id": profile.id,
                "payload": profile.risk_history,
            }
        )

    return rows


def scan_database(session: Session):
    rows = collect_payload_rows(session)
    findings = scan_legacy_payload_shapes(rows)
    return {
        "checked_rows": len(rows),
        "legacy_count": len(findings),
        "findings": findings,
    }


def main() -> int:
    with Session(engine) as session:
        report = scan_database(session)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["legacy_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
