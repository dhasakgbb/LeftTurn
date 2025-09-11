from urllib.parse import urlparse, parse_qs, unquote
from src.utils.pbi import build_pbi_deeplink


def test_build_pbi_deeplink_with_filters(monkeypatch):
    monkeypatch.setenv("PBI_WORKSPACE_ID", "WSID")
    monkeypatch.setenv("PBI_REPORT_ID", "RID")

    url = build_pbi_deeplink({
        "vw_Variance/Carrier": "Acme",
        "vw_Variance/SKU": "812",
    })

    assert url is not None
    assert url.startswith("https://app.powerbi.com/groups/WSID/reports/RID/ReportSection")
    # Parse query to assert contents without worrying about encoding
    q = parse_qs(urlparse(url).query)
    assert "filter" in q
    flt = unquote(q["filter"][0])
    assert "vw_Variance/Carrier eq 'Acme'" in flt
    assert "vw_Variance/SKU eq '812'" in flt


def test_build_pbi_deeplink_returns_base_without_filters(monkeypatch):
    monkeypatch.setenv("PBI_WORKSPACE_ID", "WSID")
    monkeypatch.setenv("PBI_REPORT_ID", "RID")
    url = build_pbi_deeplink({})
    assert url == "https://app.powerbi.com/groups/WSID/reports/RID/ReportSection"


def test_build_pbi_deeplink_with_expressions(monkeypatch):
    monkeypatch.setenv("PBI_WORKSPACE_ID", "WSID")
    monkeypatch.setenv("PBI_REPORT_ID", "RID")

    url = build_pbi_deeplink(
        {"vw_Variance/Carrier": "Acme"},
        expressions=[
            "vw_Variance/ShipDate ge '2024-01-01'",
            "vw_Variance/ShipDate le '2024-01-31'",
        ],
    )

    q = parse_qs(urlparse(url).query)
    flt = unquote(q["filter"][0])
    assert "ShipDate ge '2024-01-01'" in flt and "ShipDate le '2024-01-31'" in flt
