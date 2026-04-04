import json
import sys
from pathlib import Path

from sqlmodel import Session, select

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import engine
from backend.models import ChatConversation
from backend.services.conversation_service import conversation_service


def repair_conversation_titles(session: Session):
    conversations = list(session.exec(select(ChatConversation)).all())
    repaired_conversation_ids = []

    for conversation in conversations:
        if conversation_service.repair_legacy_title(session=session, conversation=conversation):
            repaired_conversation_ids.append(conversation.id)

    if repaired_conversation_ids:
        session.commit()

    return {
        "checked_count": len(conversations),
        "repaired_count": len(repaired_conversation_ids),
        "skipped_count": len(conversations) - len(repaired_conversation_ids),
        "repaired_conversation_ids": repaired_conversation_ids,
    }


def main() -> int:
    with Session(engine) as session:
        report = repair_conversation_titles(session)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
