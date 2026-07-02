from collections import defaultdict
import os
import sys
from typing import List, Optional

import spotipy
from dataclasses import dataclass
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth


@dataclass
class Track:
    id: str
    uri: str
    name: str
    artists: List[str]
    album: str
    isrc: Optional[str]
    spotify_url: str
    is_playable: Optional[bool]
    available_markets: list
    added_at: str

    @property
    def primary_artist(self) -> str:
        if not self.artists:
            return ""
        return self.artists[0]


def get_required_env_var(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def create_spotify_client() -> spotipy.Spotify:
    load_dotenv()

    scope = "user-read-private user-library-read playlist-read-private playlist-modify-private"

    client_id = get_required_env_var("SPOTIPY_CLIENT_ID")
    client_secret = get_required_env_var("SPOTIPY_CLIENT_SECRET")
    redirect_uri = get_required_env_var("SPOTIPY_REDIRECT_URI")

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        open_browser=True,
    )

    return spotipy.Spotify(auth_manager=auth_manager)


def connect() -> spotipy.Spotify:
    spotify = create_spotify_client()

    user: dict | None = spotify.current_user()

    if not user:
        print("spotify connection failed. check your environment variables")
        sys.exit(1)

    return spotify


def parse_track(item: dict):
    if not item:
        return None

    track = item.get("track")

    if not track:
        return None

    if track.get("type") != "track":
        return None

    if not track.get("id") or not track.get("uri"):
        return None

    album = track.get("album") or {}
    external_ids = track.get("external_ids") or {}
    external_urls = track.get("external_urls") or {}
    available_markets = track.get("available_markets") or []

    return Track(
        id=track["id"],
        uri=track["uri"],
        name=track.get("name", "Unknown Track"),
        artists=[artist.get("name") for artist in track.get("artists", [])],
        album=album.get("name", "Unknown Album"),
        isrc=external_ids.get("isrc"),
        spotify_url=external_urls.get("spotify", ""),
        is_playable=track.get("is_playable"),
        available_markets=available_markets,
        added_at=item["added_at"],
    )


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


def is_unavailable(track: Track) -> bool:

    if not track.is_playable:
        return True

    return False


def find_unavailable_liked_tracks(liked_tracks: List[Track]) -> List:
    unavailable_tracks = [track for track in liked_tracks if is_unavailable(track)]
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
        print(f"index is at {index}")
        yield items[index : index + size]


def remove_tracks(client: spotipy.Spotify, track_ids: List[str]):
    # spotify API limits deletes to 40 per request
    for batch in chunked(track_ids, 40):
        client.current_user_saved_tracks_delete(tracks=batch)


def main() -> None:
    client = connect()

    liked_songs = get_liked_tracks(client)

    unavailable_liked_tracks = find_unavailable_liked_tracks(liked_tracks=liked_songs)

    print("==== UNAVAILABLE TRACKS ====")
    for unavailable_track in unavailable_liked_tracks:
        print(
            f"{unavailable_track.name} - {[artist + ', ' for artist in unavailable_track.artists]}"
        )

    print("")

    duplicate_groups = find_duplicate_liked_tracks(liked_tracks=liked_songs)
    print("==== DUPLICATE TRACKS ====")

    for key, tracks in duplicate_groups.items():
        print(f"- {key[0]} - {key[1]}")
        for track in tracks:
            print(f"\t - {track.name} : {track.id}")

    print("")

    duplicate_tracks_to_remove = get_duplicate_liked_tracks_to_remove(duplicate_groups)
    print(f"will remove {len(duplicate_tracks_to_remove)} tracks from liked songs")
    if len(duplicate_tracks_to_remove) > 0:
        remove_tracks(client, duplicate_tracks_to_remove)
    else:
        print("no duplicate tracks found")


if __name__ == "__main__":
    main()
