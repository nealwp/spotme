import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

from track import Track


def make_track(
    id: str = "id-1",
    name: str = "Song",
    artists: tuple = ("Artist",),
    added_at: str = "2024-01-01T00:00:00Z",
    is_playable: bool = True,
) -> Track:
    return Track(
        id=id,
        uri=f"spotify:track:{id}",
        name=name,
        artists=list(artists),
        album="Album",
        isrc=None,
        spotify_url="",
        available_markets=["US"],
        added_at=added_at,
        is_playable=is_playable,
    )


def make_liked_item(item_id: str) -> dict:
    return {
        "added_at": "2024-01-01T00:00:00Z",
        "track": {
            "id": item_id,
            "uri": f"spotify:track:{item_id}",
            "type": "track",
            "name": f"Song {item_id}",
            "artists": [{"name": "Artist"}],
            "album": {"name": "Album"},
            "external_ids": {},
            "external_urls": {},
            "available_markets": ["US"],
            "is_playable": True,
        },
    }


def make_now_playing_payload(name: str = "Song Title", artist: str = "Artist") -> dict:
    return {
        "item": {
            "name": name,
            "artists": [{"name": artist}],
            "popularity": 42,
            "album": {"name": "Album Name", "release_date": "1999-05-04"},
        }
    }


def make_client(**returns: Any) -> MagicMock:
    client = MagicMock()
    for attribute, value in returns.items():
        getattr(client, attribute).return_value = value
    return client


def test_normalize_lowercases_and_collapses_whitespace(cli):
    assert cli.normalize("  Foo   BAR \n baz ") == "foo bar baz"


def test_normalize_handles_empty_values(cli):
    assert cli.normalize("") == ""
    assert cli.normalize(None) == ""


def test_chunked_splits_with_remainder(cli):
    assert list(cli.chunked(list(range(7)), 3)) == [[0, 1, 2], [3, 4, 5], [6]]


def test_chunked_handles_empty_input(cli):
    assert list(cli.chunked([], 3)) == []


def test_find_unavailable_filters_unplayable_tracks(cli):
    playable = make_track(id="keep", is_playable=True)
    unplayable = make_track(id="drop", is_playable=False)

    result = cli.find_unavailable_liked_tracks([playable, unplayable])

    assert result == [unplayable]


def test_find_duplicates_groups_by_normalized_key(cli):
    first = make_track(id="1", name="Song   LIVE ", added_at="2024-01-01T00:00:00Z")
    second = make_track(id="2", name=" song live ", added_at="2020-05-05T00:00:00Z")

    groups = cli.find_duplicate_liked_tracks([first, second])

    assert list(groups.keys()) == [("song live", "artist")]
    assert groups[("song live", "artist")] == [first, second]


def test_find_duplicates_excludes_singletons(cli):
    tracks = [make_track(id=str(i), name=f"Song {i}") for i in range(3)]

    assert cli.find_duplicate_liked_tracks(tracks) == {}


def test_find_duplicates_ignores_blank_names_or_artists(cli):
    blank_name = make_track(id="1", name="")
    blank_artists = make_track(id="2", artists=())

    assert cli.find_duplicate_liked_tracks([blank_name, blank_artists]) == {}


def test_get_removals_keeps_oldest_per_group(cli):
    older = make_track(id="older", added_at="2019-01-01T00:00:00Z")
    newer = make_track(id="newer", added_at="2024-01-01T00:00:00Z")

    removals = cli.get_duplicate_liked_tracks_to_remove({("song", "artist"): [newer, older]})

    assert removals == ["newer"]


def test_get_removals_dedupes_ids_across_groups(cli):
    kept_one = make_track(id="keep-one", added_at="2000-01-01T00:00:00Z")
    kept_two = make_track(id="keep-two", added_at="2000-01-01T00:00:00Z", artists=("Other",))
    shared_newest = make_track(id="shared", added_at="2024-01-01T00:00:00Z")
    shared_other_artist = make_track(
        id="shared", added_at="2024-01-01T00:00:00Z", name="Song Two", artists=("Other",)
    )

    removals = cli.get_duplicate_liked_tracks_to_remove(
        {
            ("song", "artist"): [kept_one, shared_newest],
            ("song two", "other"): [kept_two, shared_other_artist],
        }
    )

    assert removals == ["shared"]


def test_get_removals_skips_tracks_without_id(cli):
    no_id_old = make_track(id="", added_at="2019-01-01T00:00:00Z")
    no_id_mid = make_track(id="", added_at="2020-01-01T00:00:00Z")
    with_id = make_track(id="real", added_at="2021-01-01T00:00:00Z")

    removals = cli.get_duplicate_liked_tracks_to_remove(
        {("song", "artist"): [no_id_old, no_id_mid, with_id]}
    )

    assert removals == ["real"]


def test_get_liked_tracks_follows_pagination(cli):
    client = make_client()
    page_one = {"items": [make_liked_item("a")], "next": "/page/2"}
    page_two = {"items": [make_liked_item("b"), None], "next": None}
    client.current_user_saved_tracks.side_effect = [page_one, page_two]

    tracks = cli.get_liked_tracks(client)

    assert [t.id for t in tracks] == ["a", "b"]
    assert client.current_user_saved_tracks.call_args_list == [
        ((), {"limit": 50, "offset": 0}),
        ((), {"limit": 50, "offset": 50}),
    ]


def test_get_liked_tracks_returns_empty_on_no_response(cli):
    client = make_client(current_user_saved_tracks=None)

    assert cli.get_liked_tracks(client) == []


def test_remove_tracks_chunks_deletes_to_api_limit(cli):
    client = MagicMock()
    track_ids = [str(i) for i in range(95)]

    cli.remove_tracks(client, track_ids)

    calls = client.current_user_saved_tracks_delete.call_args_list
    assert len(calls) == 3
    assert [len(call.kwargs["tracks"]) for call in calls] == [40, 40, 15]


def test_write_liked_tracks_report(tmp_path, cli):
    tracks = [
        make_track(id="id-a", name="First", artists=("One", "Two")),
        make_track(id="id-b", name="Second"),
    ]
    output_path = tmp_path / "report.md"

    cli.write_liked_tracks_to_markdown(tracks, str(output_path))

    content = output_path.read_text(encoding="utf-8")
    assert "# Spotify Liked Songs" in content
    assert "Total tracks: 2" in content
    assert "## 1. First" in content
    assert "- Artist: One, Two" in content
    assert "- Spotify ID: `id-b`" in content


def test_start_playback_requires_active_device(cli, capsys):
    client = make_client(current_playback=None)

    cli.start_playback(client)

    client.start_playback.assert_not_called()
    assert "no active device" in capsys.readouterr().out


def test_start_playback_starts_when_device_active(cli):
    client = make_client(current_playback={"device": {"id": "pc"}})

    cli.start_playback(client)

    client.start_playback.assert_called_once_with()


def test_pause_playback_delegates_to_client(cli):
    client = MagicMock()

    cli.pause_playback(client)

    client.pause_playback.assert_called_once_with()


def test_start_lists_devices_and_transfers_to_selected(cli, capsys, monkeypatch):
    browser_open = MagicMock()
    monkeypatch.setattr(cli.webbrowser, "open", browser_open)
    monkeypatch.setattr("builtins.input", lambda *_: "2")
    client = make_client(
        devices={
            "devices": [
                {"id": "pc-1", "type": "Computer", "name": "Desktop"},
                {"id": "speaker-1", "type": "Speaker", "name": "Kitchen Speaker"},
            ]
        }
    )

    cli.start(client)

    client.transfer_playback.assert_called_once_with(device_id="speaker-1", force_play=True)
    browser_open.assert_not_called()
    out = capsys.readouterr().out
    assert "1. Desktop (computer)" in out
    assert "2. Kitchen Speaker (speaker)" in out
    assert "3. browser" in out


def test_start_browser_option_opens_web_player_and_transfers_to_new_device(cli, capsys, monkeypatch):
    monkeypatch.setattr(cli.time, "sleep", lambda *_: None)
    browser_open = MagicMock()
    monkeypatch.setattr(cli.webbrowser, "open", browser_open)
    monkeypatch.setattr("builtins.input", lambda *_: "2")
    client = make_client()
    client.devices.side_effect = [
        {"devices": [{"id": "pc-1", "type": "Computer", "name": "Desktop"}]},
        {"devices": [{"id": "pc-1", "type": "Computer", "name": "Desktop"}]},
        {
            "devices": [
                {"id": "pc-1", "type": "Computer", "name": "Desktop"},
                {"id": "web-1", "type": "Computer", "name": "Web Player"},
            ]
        },
    ]

    cli.start(client)

    browser_open.assert_called_once_with(cli.WEB_PLAYER_URL)
    client.transfer_playback.assert_called_once_with(device_id="web-1", force_play=True)
    out = capsys.readouterr().out
    assert "opening the web player" in out
    assert 'playing on "Web Player"' in out


def test_start_browser_gives_up_when_no_new_device_appears(cli, capsys, monkeypatch):
    monkeypatch.setattr(cli.time, "sleep", lambda *_: None)
    monkeypatch.setattr(cli.webbrowser, "open", MagicMock())
    monkeypatch.setattr("builtins.input", lambda *_: "1")
    client = make_client(devices={"devices": []})

    cli.start(client)

    assert client.devices.call_count == 1 + cli.DEVICE_POLL_ATTEMPTS
    client.transfer_playback.assert_not_called()
    assert "gave up" in capsys.readouterr().out


def test_start_reprompts_on_invalid_selection(cli, capsys, monkeypatch):
    answers = iter(["banana", "9", "1"])
    monkeypatch.setattr(cli.webbrowser, "open", MagicMock())
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    client = make_client(
        devices={"devices": [{"id": "pc-1", "type": "Computer", "name": "Desktop"}]}
    )

    cli.start(client)

    out = capsys.readouterr().out
    assert "pick a number from the list" in out
    assert "pick a number between 1 and 2" in out
    client.transfer_playback.assert_called_once_with(device_id="pc-1", force_play=True)


def test_start_cancels_on_blank_input(cli, capsys, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "")
    client = make_client(
        devices={"devices": [{"id": "pc-1", "type": "Computer", "name": "Desktop"}]}
    )

    cli.start(client)

    client.transfer_playback.assert_not_called()
    assert "nevermind" in capsys.readouterr().out


def test_skip_song_prints_next_track(cli, capsys):
    client = MagicMock()
    client.currently_playing.return_value = make_now_playing_payload("Next Song", "Next Artist")

    cli.skip_song(client)

    out = capsys.readouterr().out
    assert 'now playing: "Next Song" - Next Artist' in out


def test_skip_song_reports_nothing_playing(cli, capsys):
    client = make_client(next_track=None, currently_playing=None)

    cli.skip_song(client)

    assert "nothing is playing" in capsys.readouterr().out


def test_activate_device_transfers_to_computer(cli):
    client = make_client(
        devices={"devices": [{"id": "phone-1", "type": "Smartphone"}, {"id": "pc-1", "type": "Computer"}]}
    )

    cli.activate_device(client)

    client.transfer_playback.assert_called_once_with(device_id="pc-1")


def test_activate_device_reports_no_devices(cli, capsys):
    client = make_client(devices={"devices": []})

    cli.activate_device(client)

    client.transfer_playback.assert_not_called()
    assert "no available devices" in capsys.readouterr().out


def test_now_playing_prints_current_track(cli, capsys, monkeypatch):
    monkeypatch.setattr(cli.time, "sleep", lambda *_: None)
    client = make_client(currently_playing=make_now_playing_payload())

    cli.now_playing(client)

    out = capsys.readouterr().out
    assert "Song Title" in out
    assert "Artist" in out


@pytest.mark.parametrize(
    "command,method_name",
    [
        ("pause", "pause_playback"),
        ("play", "start_playback"),
        ("start", "transfer_playback"),
        ("devices", "devices"),
        ("playing", "currently_playing"),
        ("next", "next_track"),
    ],
)
def test_main_dispatches_playback_commands(cli, monkeypatch, command, method_name):
    client = MagicMock()
    client.current_playback.return_value = {"device": {"id": "pc"}}
    client.devices.return_value = {"devices": [{"id": "pc", "type": "Computer"}]}
    client.currently_playing.return_value = None
    monkeypatch.setattr(cli, "connect", lambda: client)
    monkeypatch.setattr("builtins.input", lambda *_: "1")
    monkeypatch.setattr(sys, "argv", ["spotme", command])

    cli.main()

    getattr(client, method_name).assert_called_once()


@pytest.mark.parametrize("command", ["unavailable", "duplicates"])
def test_main_library_commands_fetch_saved_tracks(cli, monkeypatch, command):
    client = make_client(current_user_saved_tracks=None)
    monkeypatch.setattr(cli, "connect", lambda: client)
    monkeypatch.setattr(sys, "argv", ["spotme", command])

    cli.main()

    client.current_user_saved_tracks.assert_called_once_with(limit=50, offset=0)


def test_main_rejects_unknown_command(cli, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["spotme", "bogus"])

    with pytest.raises(SystemExit) as exit_info:
        cli.main()

    assert exit_info.value.code == 2
