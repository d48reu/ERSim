# ERSim Render Deploy

ERSim supports a single-service deploy where FastAPI serves both the API/WebSocket layer and the built React frontend.

## What to deploy

- `render.yaml` defines a Docker-based Render web service
- `Dockerfile` builds the frontend, installs the Python package (`pip install -e .`), and **requires** `test_output.json` at the image root (validated during build)
- Feedback is stored in SQLite at `ERSIM_FEEDBACK_DB`

## Required files in the image

- **`test_output.json`** — bundled case pool for `POST /session`. The Docker build runs `test -f /app/test_output.json`; commit this file to the repo (or adjust the Dockerfile to generate/copy it in CI before build).
- **`pyproject.toml`** + `llm.py`, `api/`, `shift/`, `cases/`, `residents/` — installed as the `ersim` package so imports work without `sys.path` hacks.

## Required environment variables

- `ERSIM_BACKEND=openrouter` for hosted inference
- `OPENROUTER_API_KEY=...`
- optional model overrides:
  - `ERSIM_MODEL`
  - `ERSIM_GEN_MODEL`
- `ERSIM_CURATED_DEMO=1`
- `ERSIM_FEEDBACK_DB=/data/ersim_feedback.db`
- optional feedback export gate:
  - `ERSIM_FEEDBACK_EXPORT_TOKEN=...`
- **`ERSIM_CORS_ORIGINS`** (recommended for any cross-origin browser client): comma-separated list, e.g. `https://your-service.onrender.com`. If unset, the API uses `Access-Control-Allow-Origin: *` **without** credentials (fine for same-origin SPA + WebSocket on the same host).

## Frontend API URL

- **Production (this Docker layout):** build the SPA with the default `VITE_API_URL` empty so the browser uses same-origin `/session` and WebSockets.
- **Local dev:** run API on port 8000 and `npm run dev` in `frontend/`; Vite proxies `/session` and `/health` to `localhost:8000` (see `frontend/vite.config.js`). Set `VITE_API_URL` only if you intentionally split origins (then set `ERSIM_CORS_ORIGINS` on the API to match).

## Start command

The container runs:

```bash
python run.py --host 0.0.0.0 --port $PORT
```

## Notes

- The frontend is built into `api/static` during the Docker build.
- WebSockets stay on the same origin as the REST API when `VITE_API_URL` is unset.
- To export feedback locally after pulling the SQLite file:

```bash
python export_feedback.py > feedback.csv
```

- To export from the live service, set `ERSIM_FEEDBACK_EXPORT_TOKEN` and visit:

```text
/feedback/export?token=YOUR_TOKEN
```

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs `pytest` and `npm run build` so refactors stay green.
