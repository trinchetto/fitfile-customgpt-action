# fitfile-customgpt-action

A CustomGPT Action that parses and produces FIT files (see: https://developer.garmin.com/fit/overview/)

This repository uses [`uv`](https://github.com/astral-sh/uv) for dependency management and isolates the
Python package inside the `fitfile_customgpt_action/` directory. The package exposes a FastAPI service
that acts as a tool endpoint for CustomGPT workflows: it can parse FIT binaries into JSON-friendly
structures and build FIT binaries from lists of FIT profile messages through `fit-tool`.

## Project layout

```
fitfile_customgpt_action/
├── pyproject.toml      # uv-managed project metadata & tooling config
├── uv.lock             # locked dependency graph
├── src/fitfile_customgpt_action/
│   ├── app.py          # FastAPI factory and ASGI app instance
│   ├── cli.py          # uvicorn entry-point for local execution
│   ├── models.py       # Pydantic models shared by the API
│   ├── routes.py       # REST endpoints
│   ├── services.py     # FIT parsing/building helpers that wrap fit-tool
│   └── message_registry.py  # Discovers fit-tool profile messages at runtime
└── tests/              # Pytest scaffolding (fixtures only for now)
```

## Getting started

1. Make sure `uv` is available in your shell (e.g. `pipx install uv`).
2. Install the project with development dependencies:
   ```bash
   cd fitfile_customgpt_action
   uv sync --dev
   ```
3. Run the ASGI server:
   ```bash
   uv run fitfile-customgpt-action --host 127.0.0.1 --port 8000
   ```
4. Explore the OpenAPI docs at `http://127.0.0.1:8000/fit/docs`.

## API surface

| Endpoint        | Description                                                                                           |
|-----------------|-------------------------------------------------------------------------------------------------------|
| `GET /fit/healthz` | Liveness/readiness probe.                                                                            |
| `POST /fit/parse`  | Accepts a FIT binary upload (multipart/form-data) and returns structured metadata plus every record. |
| `POST /fit/produce`| Takes a JSON payload describing FIT messages/fields and streams back a generated FIT file.          |

Example payload for `/fit/produce`:

```json
{
  "messages": [
    {
      "name": "file_id",
      "fields": [
        {"name": "type", "value": 4},
        {"name": "manufacturer", "value": 1}
      ]
    },
    {
      "name": "record",
      "fields": [
        {"name": "timestamp", "value": 1234567890},
        {"name": "heart_rate", "value": 142}
      ]
    }
  ]
}
```

The service discovers every FIT profile message exposed by `fit-tool`, so you can mix and match any
message supported by the Garmin FIT profile.

## Tooling

- **Linting / formatting**: `uv run pre-commit run --all-files ruff ruff-format`
- **Static typing**: `uv run pre-commit run --all-files mypy`
- **Testing scaffold**: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest` (skipped placeholder test only)
- **Hooks**: configure with `pre-commit install` to run Ruff + mypy before each commit

## Continuous Integration

`.github/workflows/ci.yml` runs on pushes/PRs and executes the full toolchain:

1. `uv sync --dev`
2. `pre-commit run --all-files ruff ruff-format mypy`
3. `pytest`

This ensures consistent quality gates locally and in CI/CD.
