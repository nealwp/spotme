from typing import Any

from track import Track, parse_now_playing, parse_track


def make_track_item(track_payload: dict | None = None, **item_fields: Any) -> dict:
    payload = {
        "added_at": "2023-01-15T10:00:00Z",
        "track": {
            "id": "id-1",
            "uri": "spotify:track:id-1",
            "type": "track",
            "name": "Song Title",
            "artists": [{"name": "Artist One"}, {"name": "Artist Two"}],
            "album": {"name": "Album Name"},
            "external_ids": {"isrc": "USXXX2100001"},
            "external_urls": {"spotify": "https://open.spotify.com/track/id-1"},
            "available_markets": ["US", "GB"],
            "is_playable": True,
        },
    }

    if track_payload is not None:
        payload["track"] = track_payload

    payload.update(item_fields)
    return payload


def make_now_playing_payload() -> dict:
    return {
        "item": {
            "name": "Song Title",
            "artists": [{"name": "Artist One"}],
            "popularity": 42,
            "album": {"name": "Album Name", "release_date": "1999-05-04"},
        }
    }


def test_parse_track_builds_track_from_api_payload():
    track = parse_track(make_track_item())

    assert track.id == "id-1"
    assert track.uri == "spotify:track:id-1"
    assert track.name == "Song Title"
    assert track.artists == ["Artist One", "Artist Two"]
    assert track.album == "Album Name"
    assert track.isrc == "USXXX2100001"
    assert track.spotify_url == "https://open.spotify.com/track/id-1"
    assert track.available_markets == ["US", "GB"]
    assert track.added_at == "2023-01-15T10:00:00Z"
    assert track.is_playable is True


def test_parse_track_returns_none_for_missing_items():
    assert parse_track(None) is None
    assert parse_track({}) is None


def test_parse_track_skips_non_track_types():
    episode = {"id": "ep-1", "uri": "spotify:episode:ep-1", "type": "episode"}
    assert parse_track(make_track_item(episode)) is None


def test_parse_track_requires_id_and_uri():
    no_id = {"id": "", "uri": "spotify:track:x", "type": "track"}
    no_uri = {"id": "x", "uri": "", "type": "track"}
    assert parse_track(make_track_item(no_id)) is None
    assert parse_track(make_track_item(no_uri)) is None


def test_parse_track_falls_back_when_optional_fields_missing():
    sparse = {"id": "id-9", "uri": "spotify:track:id-9", "type": "track"}
    track = parse_track(make_track_item(sparse, added_at="2024-03-04T00:00:00Z"))

    assert track.name == "Unknown Track"
    assert track.artists == []
    assert track.album == "Unknown Album"
    assert track.isrc is None
    assert track.spotify_url == ""
    assert track.available_markets == []


def test_parse_track_is_playable_is_none_when_key_missing():
    sparse = {"id": "id-9", "uri": "spotify:track:id-9", "type": "track"}
    track = parse_track(make_track_item(sparse))

    assert track.is_playable is None


def test_primary_artist_returns_first_artist():
    track = parse_track(make_track_item())
    assert track.primary_artist == "Artist One"


def test_primary_artist_handles_empty_artists():
    track = Track(
        id="id-2",
        uri="spotify:track:id-2",
        name="Orphan Song",
        artists=[],
        album="Album",
        isrc=None,
        spotify_url="",
        available_markets=[],
        added_at="2023-01-15T10:00:00Z",
    )
    assert track.primary_artist == ""


def test_parse_now_playing_extracts_fields():
    playing = parse_now_playing(make_now_playing_payload())

    assert playing.name == "Song Title"
    assert playing.artist == "Artist One"
    assert playing.album["name"] == "Album Name"
    assert playing.popularity == 42


def test_now_playing_str_includes_track_details():
    playing = parse_now_playing(make_now_playing_payload())
    rendered = str(playing)

    assert "Song Title" in rendered
    assert "Artist One" in rendered
    assert "Album Name" in rendered
    assert "1999" in rendered
    assert "\033[32m" in rendered
