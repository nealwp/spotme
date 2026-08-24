# spotme

A small command-line tool for managing my Spotify library and playback — find unavailable or duplicate tracks in your liked songs, control playback, and see what's playing.

Built on [spotipy](https://spotipy.readthedocs.io/).

## Requirements

- Python 3.10+
- A [Spotify developer app](https://developer.spotify.com/dashboard) (client ID + secret)
- Spotify Premium (required by Spotify for playback control)

## Setup

Install from [PyPI](https://pypi.org/project/spotme-cli/) with [pipx](https://pipx.pypa.io/) (recommended):

```bash
pipx install spotme-cli
```

It's published as `spotme-cli` because the plain `spotme` name was already taken on PyPI — the command you run is still `spotme`.

To install from a local checkout instead:

```bash
pipx install .
```

Or set up a development environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

### Credentials

The quickest way is to run the setup command and answer the prompts:

```bash
spotme init
```

That writes `~/.config/spotme/.env` for you. To do it manually, copy the example config and add your keys from the [Spotify developer dashboard](https://developer.spotify.com/dashboard):

```bash
mkdir -p ~/.config/spotme
cp .env.example ~/.config/spotme/.env
```

Fill in `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET`. Keep `SPOTIPY_REDIRECT_URI` as `http://127.0.0.1:8888/callback`, and make sure that URI is added to your app's redirect URIs in the Spotify dashboard.

A `.env` in the current directory also works and takes precedence — handy while developing.

## Usage

```bash
spotme <command>
```

From a repo checkout without installing, `python -m spotme <command>` works too.

| Command | Description |
|---|---|
| `init` | set up spotify credentials |
| `playing` | show what's currently playing |
| `start` | launch spotify and start playback |
| `play` | start playback |
| `pause` | pause playback |
| `next` | skip to the next track |
| `devices` | list available devices |
| `activate` | transfer playback to the computer |
| `unavailable` | find unavailable tracks in liked songs |
| `duplicates` | find duplicate tracks in liked songs |

The first command you run opens a browser window for OAuth login; tokens are cached at `~/.cache/spotme/token`.

Library commands (`unavailable`, `duplicates`) page through all of your liked songs and can take a moment on large libraries. Playback commands (`play`, `pause`, `next`, `playing`) require an active Spotify device.

`start` shows a numbered list of your available devices to pick from, plus a `browser` option at the end. Choosing `browser` opens the [Spotify web player](https://open.spotify.com), waits for it to register as a new device, then starts playback there. Note that browser autoplay policies may require one manual click in the tab before the first remote play goes through. Any Spotify Connect device (e.g. the desktop app or a headless daemon like [spotifyd](https://github.com/Spotifyd/spotifyd)) shows up in the list automatically. Enter nothing or `q` to cancel.

## Testing

Tests use [pytest](https://docs.pytest.org/) and mock the Spotify API — no credentials or network needed:

```bash
pip install -e '.[dev]'
python -m pytest
```
