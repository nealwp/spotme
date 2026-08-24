# spotme

A small command-line tool for managing my Spotify library and playback — find unavailable or duplicate tracks in your liked songs, control playback, and see what's playing.

Built on [spotipy](https://spotipy.readthedocs.io/).

## Requirements

- Python 3.10+
- A [Spotify developer app](https://developer.spotify.com/dashboard) (client ID + secret)
- Spotify Premium (required by Spotify for playback control)

## Setup

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the example env file and add your credentials:

```bash
cp .env.example .env
```

Fill in `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET`. Keep `SPOTIPY_REDIRECT_URI` as `http://127.0.0.1:8888/callback`, and make sure that URI is added to your app's redirect URIs in the Spotify dashboard.

## Usage

Run from the repo root:

```bash
python __main__.py <command>
```

| Command | Description |
|---|---|
| `playing` | show what's currently playing |
| `play` | start playback |
| `pause` | pause playback |
| `next` | skip to the next track |
| `devices` | list available devices |
| `activate` | transfer playback to the computer |
| `unavailable` | find unavailable tracks in liked songs |
| `duplicates` | find duplicate tracks in liked songs |

The first command you run opens a browser window for OAuth login; tokens are cached locally in `.cache`.

Library commands (`unavailable`, `duplicates`) page through all of your liked songs and can take a moment on large libraries. Playback commands (`play`, `pause`, `next`, `playing`) require an active Spotify device.
