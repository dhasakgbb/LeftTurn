import pytest

from src.services.fabric_data_agent import FabricDataAgent


def test_run_sql_blocks_non_select():
    agent = FabricDataAgent("https://fake")
    with pytest.raises(PermissionError):
        agent.run_sql("DELETE FROM t")


def test_run_sql_params_blocks_non_select():
    agent = FabricDataAgent("https://fake")
    with pytest.raises(PermissionError):
        agent.run_sql_params("UPDATE t SET x=@x", {"@x": 1})

