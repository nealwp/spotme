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


def parse_track(track: dict):
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
            track = parse_track(item.get("track"))
            if track:
                liked_tracks.append(track)

        if page["next"] is None:
            print("finished pages")
            break

        offset += limit

    return liked_tracks


def is_unavailable(track: Track) -> bool:

    if not track.is_playable:
        return True

    return False


def find_unavailable_liked_tracks(client: spotipy.Spotify) -> List:

    liked_tracks = get_liked_tracks(client)
    unavailable_tracks = [track for track in liked_tracks if is_unavailable(track)]
    return unavailable_tracks


def main() -> None:
    client = connect()

    unavailable_liked_tracks = find_unavailable_liked_tracks(client)
    for unavailable_track in unavailable_liked_tracks:
        print(
            f"{unavailable_track.name} - {[artist + ', ' for artist in unavailable_track.artists]}"
        )


if __name__ == "__main__":
    main()
