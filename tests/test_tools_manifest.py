import os
from pathlib import Path

from tools import generate_manifests as gen


def test_generate_manifests(tmp_path, monkeypatch):
    # Point to a temp copy of the repo docs/teams
    root = Path(__file__).resolve().parents[1]
    # Ensure env set
    monkeypatch.setenv("APP_HOSTNAME", "myapp.azurewebsites.net")
    monkeypatch.setenv("APP_ID_URI", "api://11111111-1111-1111-1111-111111111111")
    monkeypatch.setenv("TEAMS_BOT_APP_ID", "22222222-2222-2222-2222-222222222222")
    monkeypatch.setenv("APP_VERSION", "1.2.3")

    gen.main()

    manifest = root / "teams" / "manifest" / "manifest.json"
    assert manifest.exists()
    text = manifest.read_text()
    assert "2222-2222" in text and "myapp.azurewebsites.net" in text

    openapi = root / "docs" / "openapi" / "leftturn.generated.yaml"
    assert openapi.exists()
    otext = openapi.read_text()
    assert "myapp.azurewebsites.net" in otext and "api://11111111-1111-1111-1111-111111111111" in otext

