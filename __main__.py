from collections import defaultdict
from typing import List
from track import Track, parse_track, parse_now_playing
from auth import connect
import time
import json
import spotipy
import argparse


def get_liked_tracks(client: spotipy.Spotify) -> List[Track]:
    liked_tracks = []
    offset = 0
    limit = 50

    while True:
        page: dict | None = client.current_user_saved_tracks(limit=limit, offset=offset)

        if not page:
            break

        for item in page["items"]:
            track = parse_track(item)
            if track:
                liked_tracks.append(track)

        if page["next"] is None:
            break

        offset += limit

    return liked_tracks


def find_unavailable_liked_tracks(liked_tracks: List[Track]) -> List:
    unavailable_tracks = [track for track in liked_tracks if not track.is_playable]
    return unavailable_tracks


def normalize(value: str) -> str:
    if not value:
        return ""

    return " ".join(value.lower().strip().split())


def find_duplicate_liked_tracks(liked_tracks: List[Track]) -> dict:
    duplicates_by_key = defaultdict(list)

    for track in liked_tracks:
        key = (normalize(track.name), normalize(track.primary_artist))
        if not key[0] or not key[1]:
            continue
        duplicates_by_key[key].append(track)

    duplicate_groups = {
        key: tracks for key, tracks in duplicates_by_key.items() if len(tracks) > 1
    }

    return duplicate_groups


def get_duplicate_liked_tracks_to_remove(duplicate_groups: dict[tuple, list[Track]]):
    duplicate_tracks_to_remove = []

    for _, tracks in duplicate_groups.items():
        sorted_tracks = sorted(tracks, key=lambda track: track.added_at)
        tracks_to_remove = sorted_tracks[1:]
        for track in tracks_to_remove:
            if track.id:
                duplicate_tracks_to_remove.append(track.id)

    duplicate_tracks_to_remove = list(dict.fromkeys(duplicate_tracks_to_remove))

    return duplicate_tracks_to_remove


def chunked(items, size):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def remove_tracks(client: spotipy.Spotify, track_ids: List[str]):
    # spotify API limits deletes to 40 per request
    for batch in chunked(track_ids, 40):
        client.current_user_saved_tracks_delete(tracks=batch)


def write_liked_tracks_to_markdown(tracks: list[Track], output_path: str):
    with open(output_path, "w", encoding="utf-8") as file:
        file.write("# Spotify Liked Songs\n\n")
        file.write(f"Total tracks: {len(tracks)}\n\n")

        for index, track in enumerate(tracks, start=1):
            artists = ", ".join(track.artists)

            file.write(f"## {index}. {track.name}\n\n")
            file.write(f"- Artist: {artists}\n")
            file.write(f"- Primary artist: {track.primary_artist}\n")
            file.write(f"- Album: {track.album}\n")
            file.write(f"- Added: {track.added_at}\n")
            file.write(f"- Spotify ID: `{track.id}`\n\n")


def create_liked_songs_report(liked_songs):
    write_liked_tracks_to_markdown(liked_songs, "liked_tracks.md")


def skip_song(client: spotipy.Spotify):
    client.next_track()
    time.sleep(1)
    current = client.currently_playing()
    if current is None:
        print("hmm, looks like nothing is playing")
        return

    current_track = parse_now_playing(current)
    if current_track is None:
        print("hmm, something went wrong parsing the track")
        return

    print(f'now playing: "{current_track.name}" - {current_track.artist}')
    return


def pause_playback(client: spotipy.Spotify):
    client.pause_playback()


def start_playback(client: spotipy.Spotify):
    current_playback = client.current_playback()
    if not current_playback:
        print("no active device")
        return
    client.start_playback()


def list_devices(client: spotipy.Spotify):
    devices = client.devices()
    print(json.dumps(devices, indent=4))


def activate_device(client: spotipy.Spotify):
    response = client.devices()

    if not response:
        print("no available devices")
        return

    devices: list = response.get("devices", [])

    if len(devices) < 1:
        print("no available devices")
        return

    computer = [device for device in devices if device.get("type") == "Computer"][0]
    client.transfer_playback(device_id=computer.get("id"))


def type_text(text: str, delay: float = 0.02) -> None:
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)

    print()


def now_playing(client: spotipy.Spotify):
    current = client.currently_playing()
    if current is None:
        print("hmm, looks like nothing is playing")
        return

    current_track = parse_now_playing(current)
    type_text(str(current_track))


def main() -> None:

    parser = argparse.ArgumentParser(
        prog="spotme",
        description="tool for managing my spotify playlists",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "unavailable",
        help="Find unavailable tracks in your liked songs",
    )

    subparsers.add_parser(
        "duplicates",
        help="Find duplicate tracks in your liked songs",
    )

    subparsers.add_parser(
        "next",
        help="skip to the next song in the queue",
    )

    subparsers.add_parser(
        "pause",
        help="pause playback",
    )

    subparsers.add_parser(
        "play",
        help="start playback",
    )

    subparsers.add_parser(
        "devices",
        help="list devices",
    )

    subparsers.add_parser(
        "activate",
        help="activate a device",
    )

    subparsers.add_parser(
        "playing",
        help="show what's currently playing",
    )

    args = parser.parse_args()

    client = connect()

    if args.command == "unavailable":
        liked_songs = get_liked_tracks(client)

        unavailable_liked_tracks = find_unavailable_liked_tracks(
            liked_tracks=liked_songs
        )

        print("==== UNAVAILABLE TRACKS ====")
        for unavailable_track in unavailable_liked_tracks:
            print(
                f"{unavailable_track.name} - {[artist + ', ' for artist in unavailable_track.artists]}"
            )
        return

    if args.command == "duplicates":
        liked_songs = get_liked_tracks(client)
        duplicate_groups = find_duplicate_liked_tracks(liked_tracks=liked_songs)
        print("==== DUPLICATE TRACKS ====")

        for key, tracks in duplicate_groups.items():
            print(f"- {key[0]} - {key[1]}")
            for track in tracks:
                print(f"\t - {track.name} : {track.id}")

        print("")

        duplicate_tracks_to_remove = get_duplicate_liked_tracks_to_remove(
            duplicate_groups
        )

        print(f"will remove {len(duplicate_tracks_to_remove)} tracks from liked songs")

        if len(duplicate_tracks_to_remove) > 0:
            pass
            # remove_tracks(client, duplicate_tracks_to_remove)
        else:
            pass
            # print("no duplicate tracks found")
        if False:
            create_liked_songs_report(liked_songs)

    if args.command == "next":
        skip_song(client)

    if args.command == "pause":
        pause_playback(client)

    if args.command == "play":
        start_playback(client)

    if args.command == "devices":
        list_devices(client)

    if args.command == "activate":
        activate_device(client)

    if args.command == "playing":
        now_playing(client)


if __name__ == "__main__":
    main()
