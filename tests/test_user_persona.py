from pathlib import Path

import server.user_persona as persona_store


def test_upsert_and_get_user_persona(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(persona_store, "PERSONA_PATH", tmp_path / "user_personas.json")

    saved = persona_store.upsert_user_persona(
        "user_mason",
        display_name="墨白",
        style_prompt="简洁直接，先结论后步骤。",
        claude_api_key="sk-ant-demo",
    )
    loaded = persona_store.get_user_persona("user_mason")

    assert loaded is not None
    assert loaded.display_name == "墨白"
    assert loaded.style_prompt.startswith("简洁直接")
    assert loaded.claude_api_key == "sk-ant-demo"
    assert saved.updated_at == loaded.updated_at


def test_upsert_user_persona_requires_one_api_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(persona_store, "PERSONA_PATH", tmp_path / "user_personas.json")
    try:
        persona_store.upsert_user_persona(
            "user_mason",
            display_name="墨白",
            style_prompt="简洁直接",
        )
        assert False, "expected ValueError when no API key is provided"
    except ValueError as exc:
        assert "至少填写一个模型 API Key" in str(exc)

