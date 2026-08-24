# AGENTS.md

## Project overview

spotme is a small personal Python CLI for managing a Spotify library and playback. It is built on [spotipy](https://spotipy.readthedocs.io/), packaged as a single `spotme/` package with an installable console script, and published on PyPI as `spotme-cli` (the plain name was taken; the import package and command remain `spotme`). Tests live in `tests/`, and the only CI is the tag-triggered publish workflow.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Credentials live in `~/.config/spotme/.env` (copy from `.env.example`) with `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET` from the Spotify developer dashboard. `SPOTIPY_REDIRECT_URI` defaults to `http://127.0.0.1:8888/callback`. A `.env` in the current directory is also loaded and wins over the config dir. The first command run triggers an OAuth browser flow; tokens are cached at `~/.cache/spotme/token`.

## Testing

```bash
python -m pytest
```

Tests run offline — spotipy clients are mocked with `MagicMock`, so no credentials or network calls are involved. Tests import `spotme.cli` directly via a session-scoped `cli` fixture; conftest adds the repo root to `sys.path` so the suite also works before `pip install -e .`. Tests that exercise `write_env_file` patch `spotme.auth.CONFIG_DIR` (not the cli module) since the auth functions read that global at call time.

## Releasing

Bump `version` in `pyproject.toml`, commit, then push a `v*` tag — `.github/workflows/publish.yml` runs the test matrix and publishes to PyPI via trusted publishing (no tokens stored in the repo). Requires a one-time "pending publisher" entry on pypi.org: owner `nealwp`, repo `spotme`, workflow `publish.yml`, project name `spotme-cli`.

## Running

```bash
spotme <command>
```

or `python -m spotme <command>` from a checkout. Commands: `init`, `unavailable`, `duplicates`, `next`, `pause`, `play`, `start`, `devices`, `activate`, `playing`. Library commands (`unavailable`, `duplicates`) page through all liked songs; playback commands require an active Spotify device.

## Code layout

- `spotme/cli.py` — CLI entry point. argparse with subparsers dispatching to functions that each take a `spotipy.Spotify` client.
- `spotme/__main__.py` — thin shim so `python -m spotme` works.
- `spotme/track.py` — `Track` / `NowPlaying` dataclasses plus defensive parsers (`parse_track`, `parse_now_playing`) for raw API payloads.
- `spotme/auth.py` — env var loading (`dotenv`), token cache path, OAuth scope, and client construction.
- `pyproject.toml` — packaging metadata, dependencies, `[project.scripts]` entry point (`spotme = "spotme.cli:main"`), `dev` extra with pytest.

## Conventions

- Python 3.10+ syntax (`X | None` unions), type hints on function signatures.
- Parse API responses defensively with `.get()` and fallbacks; never assume nested keys exist.
- CLI output is lowercase, casual plain text printed to stdout.

## Gotchas

- Destructive actions (e.g., `remove_tracks` in the duplicates flow) are intentionally commented out in `spotme/cli.py` — do not re-enable them without being asked.
- The Spotify API caps saved-track deletes at 40 per request (`remove_tracks` handles this via `chunked`). Liked-songs pagination uses a limit of 50.
- Duplicate removal keeps the oldest track per `(normalized name, primary artist)` group.
- Quirks captured by tests: `parse_track` yields `is_playable=None` (not `False`) when the key is absent despite the dataclass default, and `NowPlaying.__str__` assumes `album["release_date"]` exists.
- The `start` command is interactive: it prints a numbered device list and prompts for a pick, with `browser` as the last option. Choosing `browser` opens the web player, then polls (`DEVICE_POLL_ATTEMPTS` × `DEVICE_POLL_INTERVAL_SECONDS`, ~30s) for a device whose id wasn't in the pre-open list. Blank input or `q` cancels; invalid picks re-prompt. Browser autoplay policy may block the first remote play until the user interacts with the tab.
- The `init` command dispatches before `connect()` is called — it must never trigger the OAuth flow since its purpose is setting up credentials beforehand. It prompts for client id/secret (required) and redirect uri (defaults to `DEFAULT_REDIRECT_URI`), and asks before overwriting an existing config file.
- `devices()` and `current_playback()` need `user-read-playback-state` (missing from SCOPE until 0.1.1 — caused 401 "Permissions missing" on fresh installs). Changing `SCOPE` does not affect already-cached tokens: delete `~/.cache/spotme/token` to force re-consent.
