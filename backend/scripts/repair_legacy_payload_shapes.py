import json
import sys
from pathlib import Path

from sqlmodel import Session

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import engine
from backend.services.payload_normalization import repair_legacy_payload_rows


def repair_database(session: Session):
    return repair_legacy_payload_rows(session)


def main() -> int:
    with Session(engine) as session:
        report = repair_database(session)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
