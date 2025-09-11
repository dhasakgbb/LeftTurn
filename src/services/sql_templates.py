"""
Approved, parameterized SQL templates for Fabric queries.
Add new keys and keep them read-only.
"""

VARIANCE_SUMMARY = """
SELECT
  carrier_id,
  SUM(billed_total - rated_total) AS variance
FROM curated_fact_invoice
WHERE invoice_date BETWEEN @from AND @to
GROUP BY carrier_id
ORDER BY variance DESC
"""

TEMPLATES = {
    "variance_summary": VARIANCE_SUMMARY,
    "variance_by_service": """
SELECT
  service_level,
  SUM(billed_total - rated_total) AS variance
FROM curated_fact_invoice
WHERE invoice_date BETWEEN @from AND @to
  AND (@carrier IS NULL OR carrier_id = @carrier)
GROUP BY service_level
ORDER BY variance DESC
""",
    "on_time_rate": """
SELECT
  CASE WHEN COUNT(*) = 0 THEN 0.0 ELSE
    CAST(SUM(CASE WHEN on_time = 1 THEN 1 ELSE 0 END) AS FLOAT) / CAST(COUNT(*) AS FLOAT)
  END AS on_time_rate
FROM curated_fact_shipment
WHERE ship_date BETWEEN @from AND @to
  AND (@carrier IS NULL OR carrier_id = @carrier)
""",
    "fuel_surcharge_series": """
SELECT
  effective_date,
  percent
FROM curated_fuel_surcharge
WHERE effective_date BETWEEN @from AND @to
  AND (@carrier IS NULL OR carrier_id = @carrier)
ORDER BY effective_date
""",
}
