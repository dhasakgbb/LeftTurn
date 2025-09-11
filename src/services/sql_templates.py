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
}
