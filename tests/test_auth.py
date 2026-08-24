from spotme import auth


def test_scope_includes_all_playback_scopes():
    scopes = set(auth.SCOPE.split())

    assert "user-read-playback-state" in scopes
    assert "user-modify-playback-state" in scopes
    assert "user-read-currently-playing" in scopes
