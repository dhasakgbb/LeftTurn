import os

from src.services import obo as obo_mod


def test_exchange_obo_for_graph_success(monkeypatch):
    class _FakeCCA:
        def __init__(self, client_id=None, client_credential=None, authority=None):
            self.client_id = client_id

        def acquire_token_on_behalf_of(self, token, scopes=None):
            assert token == "USER_TOKEN"
            assert scopes and scopes[0].endswith("/.default")
            return {"access_token": "GRAPH_OBO"}

    monkeypatch.setenv("AAD_TENANT_ID", "t")
    monkeypatch.setenv("AAD_CLIENT_ID", "c")
    monkeypatch.setenv("AAD_CLIENT_SECRET", "s")
    monkeypatch.setenv("OBO_ENABLED", "true")
    monkeypatch.setattr(obo_mod, "msal", type("_M", (), {"ConfidentialClientApplication": _FakeCCA}))

    out = obo_mod.exchange_obo_for_graph("USER_TOKEN")
    assert out == "GRAPH_OBO"


def test_exchange_obo_for_graph_missing_env_returns_none(monkeypatch):
    # Unset env to trigger graceful None
    for k in ["AAD_TENANT_ID", "AAD_CLIENT_ID", "AAD_CLIENT_SECRET"]:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(obo_mod, "msal", type("_M", (), {"ConfidentialClientApplication": object}))
    out = obo_mod.exchange_obo_for_graph("USER_TOKEN")
    assert out is None

