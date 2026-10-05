# ArchScope V4

A research-first architecture discovery prototype inspired by common architecture-library workflows, without copying any publisher's branding or proprietary catalogue.

## Run

Python 3.10+

```bash
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Live search

Copy `.env.example` to `.env` and set:

```text
BRAVE_API_KEY=your_key
```

Then run the app. Without the key, the local demonstration catalogue still works.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `BRAVE_API_KEY` | — | Enables live web/image search |
| `PORT` | `5000` | HTTP port |
| `FLASK_DEBUG` | `0` | `1` enables the Flask debug reloader |
| `SEARCH_CACHE_TTL` | `300` | Seconds to cache live search results |
| `SEARCH_RATE_LIMIT` | `20` | Searches allowed per client per minute |

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/test_api.py        # API tests
node tests/frontend.test.js     # frontend behaviour tests
```

## Features

- Project-first demo catalogue with filtering
- Project detail + asset grouping
- Parallel live web/image search (Brave) with TTL cache and per-client rate limiting
- Drawing/photo/detail classification (word-boundary matching)
- Local research board in browser storage: save, remove, import/export JSON
- Source links open in a new tab; output is HTML-escaped (XSS-safe)

## Deploy

`render.yaml` defines a free Render web service (`gunicorn app:app`).
Pushes to `master` need a manual `render deploys create <service-id>` until the
Render GitHub app is connected.

## Next production steps

- PostgreSQL project/asset schema with real, attributable assets (currently demo placeholders)
- PDF ingestion + page extraction
- Vision model classification
- OCR for drawing labels/dimensions
- Licensed/open image handling
- User accounts and cloud boards
