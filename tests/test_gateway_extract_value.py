from src.functions.agent_gateway import _extract_value


def test_extract_value_variants():
    q = "carrier: Acme service level=2Day sku 812"
    assert _extract_value(q, "carrier") == "Acme"
    assert _extract_value(q, "service level") == "2Day"
    assert _extract_value(q, "sku") == "812"

