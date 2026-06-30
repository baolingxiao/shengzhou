from server.auth import AuthUser
from server.auth_session import issue_access_token, parse_access_token, session_id_for_username


def test_access_token_roundtrip() -> None:
    token = issue_access_token(AuthUser(username="user_mason", role="user"), ttl_seconds=3600)
    session = parse_access_token(token)
    assert session is not None
    assert session.username == "user_mason"
    assert session.role == "user"
    assert session.is_admin is False


def test_session_id_for_username_sanitizes() -> None:
    sid = session_id_for_username("mason@example.com")
    assert sid.startswith("user-")
    assert "@" not in sid

