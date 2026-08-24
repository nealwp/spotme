# AGENTS.md

## Project overview

spotme is a small personal Python CLI for managing a Spotify library and playback. It is built on [spotipy](https://spotipy.readthedocs.io/) and runs entirely from flat modules at the repo root — tests live in `tests/`, there is no CI configured.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET` (from the Spotify developer dashboard). `SPOTIPY_REDIRECT_URI` defaults to `http://127.0.0.1:8888/callback`. The first command run triggers an OAuth browser flow; tokens are cached in `.cache`.

## Testing

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Tests run offline — spotipy clients are mocked with `MagicMock`, so no credentials or network calls are involved. `tests/conftest.py` adds the repo root to `sys.path` (modules import as siblings) and loads `__main__.py` by file path into a session-scoped `cli` fixture, since `__main__` cannot be imported by name inside pytest.

## Running

Run from the repo root so sibling-module imports resolve:

```bash
python __main__.py <command>
```

Commands: `unavailable`, `duplicates`, `next`, `pause`, `play`, `devices`, `activate`, `playing`. Library commands (`unavailable`, `duplicates`) page through all liked songs; playback commands require an active Spotify device.

## Code layout

- `__main__.py` — CLI entry point. argparse with subparsers dispatching to functions that each take a `spotipy.Spotify` client.
- `track.py` — `Track` / `NowPlaying` dataclasses plus defensive parsers (`parse_track`, `parse_now_playing`) for raw API payloads.
- `auth.py` — env var loading (`dotenv`), OAuth scope definition, and client construction.

## Conventions

- Python 3.10+ syntax (`X | None` unions), type hints on function signatures.
- Parse API responses defensively with `.get()` and fallbacks; never assume nested keys exist.
- CLI output is lowercase, casual plain text printed to stdout.

## Gotchas

- Destructive actions (e.g., `remove_tracks` in the duplicates flow) are intentionally commented out in `__main__.py` — do not re-enable them without being asked.
- The Spotify API caps saved-track deletes at 40 per request (`remove_tracks` handles this via `chunked`). Liked-songs pagination uses a limit of 50.
- Duplicate removal keeps the oldest track per `(normalized name, primary artist)` group.
- Quirks captured by tests: `parse_track` yields `is_playable=None` (not `False`) when the key is absent despite the dataclass default, and `NowPlaying.__str__` assumes `album["release_date"]` exists.
- The `start` command is interactive: it prints a numbered device list and prompts for a pick, with `browser` as the last option. Choosing `browser` opens the web player, then polls (`DEVICE_POLL_ATTEMPTS` × `DEVICE_POLL_INTERVAL_SECONDS`, ~30s) for a device whose id wasn't in the pre-open list. Blank input or `q` cancels; invalid picks re-prompt. Browser autoplay policy may block the first remote play until the user interacts with the tab.
