import responses

from src.services.fabric_data_agent import FabricDataAgent
import src.services.fabric_data_agent as fmod


def test_fabric_odbc_param_binding_order(monkeypatch):
    # Fake pyodbc connection/execute that records inputs and returns rows
    class _Cursor:
        def __init__(self):
            self.last = None
            self.description = [("col1",), ("col2",)]

        def execute(self, sql, params):
            # SQL should be stripped to ? placeholders in the original order
            self.last = (sql, tuple(params))

        def fetchall(self):
            return [(1, "a"), (2, "b")]

    class _Conn:
        def cursor(self):
            return _Cursor()

        def close(self):
            pass

    class _Pyodbc:
        def connect(self, cstr, autocommit=False):  # type: ignore[override]
            assert "Driver=" in cstr or cstr
            return _Conn()

    monkeypatch.setenv("FABRIC_SQL_MODE", "odbc")
    monkeypatch.setenv("FABRIC_ODBC_CONNECTION_STRING", "Driver=Fake;Server=fabric;")
    monkeypatch.setattr(fmod, "pyodbc", _Pyodbc())

    agent = FabricDataAgent("https://facade.ignore", token="T")
    sql = (
        "SELECT * FROM t WHERE carrier = @carrier AND invoice_date BETWEEN @from AND @to"
    )
    rows = agent.run_sql_params(sql, {"@carrier": "C1", "@from": "2024-01-01", "@to": "2024-01-31"})
    # Should return list of dicts
    assert rows == [{"col1": 1, "col2": "a"}, {"col1": 2, "col2": "b"}]


def test_fabric_http_run_sql_params(monkeypatch):
    with responses.RequestsMock() as rsps:
        rsps.add(
            "POST",
            "https://fabric.test/sql",
            json={"rows": [{"k": 1}]},
        )
        agent = FabricDataAgent("https://fabric.test", token="T")
        out = agent.run_sql_params("SELECT 1 WHERE x=@x", {"@x": 1})
        assert out == [{"k": 1}]
