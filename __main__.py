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
    available_market_count: int


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


def get_liked_tracks():
    return []


def is_unavailable(track: Track) -> bool:
    return not track.is_playable or track.available_market_count == 0


def find_unavailable_liked_tracks(client: spotipy.Spotify) -> List:

    liked_tracks = get_liked_tracks()
    unavailable_tracks = [track for track in liked_tracks if is_unavailable(track)]
    return unavailable_tracks


def main() -> None:
    client = connect()

    unavailable_liked_tracks = find_unavailable_liked_tracks(client)
    print(unavailable_liked_tracks)


if __name__ == "__main__":
    main()
