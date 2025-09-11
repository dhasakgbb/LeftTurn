Tools and helpers for packaging and deployment.

- `generate_manifests.py` — writes Teams manifest (manifest.json) and an environment‑specific OpenAPI (leftturn.generated.yaml). Requires APP_HOSTNAME, APP_ID_URI, TEAMS_BOT_APP_ID.
- `commit_folder_descriptions.sh` — optional helper to split commits by folder so GitHub shows clean per‑folder “descriptions”.
- `setup_cloud.sh`, `run_tests.sh` — optional cloud helpers (if present).
- `fabric_register_views.py` — executes DDL in `fabric/sql/*.sql` via ODBC. Requires `FABRIC_ODBC_CONNECTION_STRING` and `pyodbc` installed. Use `make register-views`.
