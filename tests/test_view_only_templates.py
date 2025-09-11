import pytest

from src.agents.structured_data_agent import StructuredDataAgent


class _DummyFabric:
    def run_sql_params(self, sql, params):  # pragma: no cover - not executed
        return []


def test_structured_agent_blocks_non_view_templates():
    templates = {
        "bad": "SELECT * FROM dbo.FactInvoice WHERE Carrier=@carrier"
    }
    agent = StructuredDataAgent(_DummyFabric(), templates=templates)
    with pytest.raises(PermissionError):
        agent.query("bad", {"@carrier": "X"})

