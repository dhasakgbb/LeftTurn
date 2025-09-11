
import src.functions.agent_gateway as gw


class _FakeFabric:
    def __init__(self, *args, **kwargs):
        pass

    def run_sql_params(self, sql, params):
        # Return a small rowset
        return [{"carrier": params.get("@carrier", ""), "variance": 123.45}]


class _Req:
    def __init__(self, body: dict, params=None, headers=None, route=None):
        self._body = body
        self.params = params or {}
        self.headers = headers or {}
        self.route_params = route or {}

    def get_json(self):
        return self._body


def test_agent_ask_returns_pbi_link(monkeypatch):
    # Configure Power BI env vars so gateway can emit a deeplink
    monkeypatch.setenv("PBI_WORKSPACE_ID", "WS")
    monkeypatch.setenv("PBI_REPORT_ID", "RP")
    # Configure Fabric so orchestrator builds structured agent
    monkeypatch.setenv("FABRIC_ENDPOINT", "https://fabric.test")
    monkeypatch.setenv("FABRIC_TOKEN", "T")

    # Patch FabricDataAgent in the gateway module to avoid real HTTP
    monkeypatch.setattr(gw, "FabricDataAgent", lambda *a, **k: _FakeFabric())

    payload, agent_name = gw.handle_agent_query(
        "How much were we overbilled last quarter for carrier: Acme?",
        "domain",
        None,
        {},
        {},
    )
    assert payload.get("powerBiLink")


def test_agent_ask_pbi_date_column_env(monkeypatch):
    # Configure Power BI env vars so gateway can emit a deeplink
    monkeypatch.setenv("PBI_WORKSPACE_ID", "WS")
    monkeypatch.setenv("PBI_REPORT_ID", "RP")
    monkeypatch.setenv("PBI_DATE_COLUMN", "Dates/Date")
    # Configure Fabric so orchestrator builds structured agent
    monkeypatch.setenv("FABRIC_ENDPOINT", "https://fabric.test")
    monkeypatch.setenv("FABRIC_TOKEN", "T")

    # Patch FabricDataAgent in the gateway module to avoid real HTTP
    monkeypatch.setattr(gw, "FabricDataAgent", lambda *a, **k: _FakeFabric())

    payload, agent_name = gw.handle_agent_query(
        "How much were we overbilled last quarter for carrier: Acme?",
        "domain",
        None,
        {},
        {},
    )
    link = payload.get("powerBiLink")
    from urllib.parse import urlparse, parse_qs, unquote
    q = parse_qs(urlparse(link).query)
    flt = unquote(q["filter"][0])
    assert "Dates/Date ge" in flt and "Dates/Date le" in flt
