from src.agents.router import classify


def test_router_variance_by_service():
    out = classify("Variance by service level last quarter")
    assert out["tool"] == "sql" and out["name"] == "variance_by_service"


def test_router_on_time_rate():
    out = classify("What is the on-time rate for Acme?")
    assert out["tool"] == "sql" and out["name"] == "on_time_rate"


def test_router_variance_trend_by_carrier():
    out = classify("Show variance trend by month over time for carriers")
    assert out["tool"] == "sql" and out["name"] == "variance_trend_by_carrier"


def test_router_variance_trend_by_sku():
    out = classify("Show variance trend by month for SKU 812")
    assert out["tool"] == "sql" and out["name"] == "variance_trend_by_sku"
