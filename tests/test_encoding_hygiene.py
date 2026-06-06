from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _chars(codepoints: list[int]) -> str:
    return "".join(chr(value) for value in codepoints)


def test_high_priority_text_surfaces_do_not_keep_known_mojibake():
    bad_snippets = {
        "backend/main.py": [
            # Garbled registration and admin status strings captured in the phase-1 inventory.
            [0x9422, 0x3126, 0x57DB, 0x935A, 0x5D85, 0x51E1, 0x701B, 0x6A3A, 0x6E6A],
            [0x7487, 0x30E9, 0x5056, 0x7EE0, 0x535E, 0x51E1, 0x741A],
            [0x7035, 0x55D9, 0x721C, 0x95C0, 0x57AE, 0x5BB3],
            [0x6D93, 0x6751, 0x7C25, 0x59AF],
            [0x94FE, 0x5D85, 0x59DF, 0x7ED4],
        ],
        "backend/services/chat_service.py": [
            # Garbled completion text for recent_metric_anomaly_lookup.
            [0x93B8, 0x56E8, 0x7223, 0x5BEE, 0x509A, 0x7236],
        ],
        "tests/test_chat_agent_service.py": [
            # Garbled Chinese fallback assertion; should read as a human-readable refusal.
            [0x6D93, 0x5D88, 0x5158],
        ],
    }

    failures = []
    for relative_path, snippets in bad_snippets.items():
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        for codepoints in snippets:
            snippet = _chars(codepoints)
            if snippet in text:
                failures.append(f"{relative_path}: {snippet.encode('unicode_escape').decode('ascii')}")
        for char in text:
            if 0xE000 <= ord(char) <= 0xF8FF:
                failures.append(f"{relative_path}: private-use char U+{ord(char):04X}")
                break

    assert failures == []
