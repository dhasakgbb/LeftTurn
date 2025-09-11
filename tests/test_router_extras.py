from src.agents.router import classify


def test_router_variance_by_service():
    out = classify("Variance by service level last quarter")
    assert out["tool"] == "sql" and out["name"] == "variance_by_service"


def test_router_on_time_rate():
    out = classify("What is the on-time rate for Acme?")
    assert out["tool"] == "sql" and out["name"] == "on_time_rate"

