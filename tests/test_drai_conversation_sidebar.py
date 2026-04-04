from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DRAI_FILE = REPO_ROOT / "frontend" / "src" / "views" / "chat" / "DrAI.vue"


def test_drai_sidebar_supports_search_archive_and_pin_controls():
    source = DRAI_FILE.read_text(encoding="utf-8")

    assert "conversationSearch" in source
    assert "showArchived" in source
    assert "toggleConversationArchive" in source
    assert "toggleConversationPin" in source
    assert "'unpin'" in source
    assert "'pin'" in source
    assert "'restore'" in source
    assert "'archive'" in source


def test_drai_sidebar_uses_backend_grouping_metadata_and_manual_rename():
    source = DRAI_FILE.read_text(encoding="utf-8")

    assert "group_key" in source
    assert "group_label" in source
    assert "activeRenameConversationId" in source
    assert "renameConversation" in source
    assert "axios.patch" in source
    assert "{ title }" in source
    assert "trim()" in source


def test_drai_chat_view_supports_suggestion_cards_and_tool_stream_events():
    source = DRAI_FILE.read_text(encoding="utf-8")

    assert "suggestionCard" in source
    assert "'tool_start'" in source
    assert "'tool_done'" in source


def test_drai_chat_view_supports_optional_c3_evidence_panel():
    source = DRAI_FILE.read_text(encoding="utf-8")

    assert "evidencePanel" in source
    assert "evidence_panel" in source
    assert "activeEvidencePanelKey" in source
    assert "toggleEvidencePanelSection" in source
    assert "msg.evidencePanel.chips" in source
    assert "msg.evidencePanel.sections" in source
    assert "@click=\"toggleEvidencePanelSection" in source


def test_drai_c3_evidence_panel_keeps_frozen_section_fields_and_single_expand_state():
    source = DRAI_FILE.read_text(encoding="utf-8")

    assert "section.label" in source
    assert "section.summary" in source
    assert "section.key_facts" in source
    assert "section.decision_basis" in source
    assert "section.source_refs" in source
    assert "msg.activeEvidencePanelKey === section.label" in source
    assert "msg.activeEvidencePanelKey = section.label" in source
    assert "msg.activeEvidencePanelKey = null" in source
