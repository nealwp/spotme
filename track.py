from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Track:
    id: str
    uri: str
    name: str
    artists: List[str]
    album: str
    isrc: Optional[str]
    spotify_url: str
    available_markets: list
    added_at: str
    is_playable: Optional[bool] = False

    @property
    def primary_artist(self) -> str:
        if not self.artists:
            return ""
        return self.artists[0]


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


@dataclass
class NowPlaying:
    name: str
    artist: str
    album: str
    popularity: int


def parse_now_playing(now_playing: dict):
    item = now_playing.get("item")
    album = item.get("album")
    artist = [artist.get("name") for artist in item.get("artists", [])][0]
    popularity = item.get("popularity")
    return NowPlaying(
        name=item.get("name"),
        album=album,
        artist=artist,
        popularity=popularity,
    )
