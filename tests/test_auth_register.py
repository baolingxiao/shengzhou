from pathlib import Path

import server.auth as auth_store


def test_register_user_creates_local_user(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(auth_store, "AUTH_USERS_PATH", tmp_path / "auth_users.json")
    user = auth_store.register_user("new_user", "Password#2026")
    assert user.username == "new_user"
    assert user.role == "user"

    check = auth_store.authenticate("new_user", "Password#2026")
    assert check is not None
    assert check.role == "user"


def test_register_user_rejects_duplicate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(auth_store, "AUTH_USERS_PATH", tmp_path / "auth_users.json")
    auth_store.register_user("dup_user", "Password#2026")
    try:
        auth_store.register_user("dup_user", "Password#2026")
        assert False, "expected duplicate username error"
    except ValueError as exc:
        assert "用户名已存在" in str(exc)


def test_default_developer_username_is_daijinxin(monkeypatch) -> None:
    monkeypatch.delenv("JARVIS_AUTH_USER", raising=False)
    monkeypatch.delenv("JARVIS_AUTH_PASSWORD", raising=False)
    auth_store._admin_usernames.cache_clear()

    direct = auth_store.authenticate("戴金鑫", "jarvis")
    assert direct is not None
    assert direct.role == "developer"
    assert direct.username == "戴金鑫"

    legacy = auth_store.authenticate("admin", "jarvis")
    assert legacy is not None
    assert legacy.role == "developer"
    assert legacy.username == "戴金鑫"

