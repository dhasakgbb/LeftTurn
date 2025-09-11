"""
Approved, parameterized SQL templates for Fabric queries.
Add new keys and keep them read-only.
"""

VARIANCE_SUMMARY = """
SELECT
  Carrier AS carrier,
  SUM(Variance) AS variance
FROM vw_Variance
WHERE ShipDate BETWEEN @from AND @to
GROUP BY Carrier
ORDER BY variance DESC
"""

TEMPLATES = {
    "variance_summary": VARIANCE_SUMMARY,
    "variance_by_service": """
SELECT
  ServiceLevel,
  SUM(Variance) AS variance
FROM vw_Variance
WHERE ShipDate BETWEEN @from AND @to
  AND (@carrier IS NULL OR Carrier = @carrier)
GROUP BY ServiceLevel
ORDER BY variance DESC
""",
    "variance_by_sku": """
SELECT
  SKU,
  SUM(Variance) AS variance
FROM vw_Variance
WHERE ShipDate BETWEEN @from AND @to
  AND (@carrier IS NULL OR Carrier = @carrier)
GROUP BY SKU
ORDER BY variance DESC
""",
    "variance_by_carrier_service": """
SELECT
  Carrier,
  ServiceLevel,
  SUM(Variance) AS variance
FROM vw_Variance
WHERE ShipDate BETWEEN @from AND @to
  AND (@carrier IS NULL OR Carrier = @carrier)
GROUP BY Carrier, ServiceLevel
ORDER BY variance DESC
""",
    "on_time_rate": """
SELECT
  CASE WHEN COUNT(*) = 0 THEN 0.0 ELSE
    CAST(SUM(CASE WHEN OnTime = 1 THEN 1 ELSE 0 END) AS FLOAT) / CAST(COUNT(*) AS FLOAT)
  END AS on_time_rate
FROM vw_FactShipment
WHERE ShipDate BETWEEN @from AND @to
  AND (@carrier IS NULL OR Carrier = @carrier)
""",
    "variance_trend_by_carrier": """
SELECT
  DATEFROMPARTS(YEAR(ShipDate), MONTH(ShipDate), 1) AS Month,
  Carrier,
  SUM(Variance) AS variance
FROM vw_Variance
WHERE ShipDate BETWEEN @from AND @to
  AND (@carrier IS NULL OR Carrier = @carrier)
GROUP BY DATEFROMPARTS(YEAR(ShipDate), MONTH(ShipDate), 1), Carrier
ORDER BY Month, Carrier
""",
    "variance_trend_by_sku": """
SELECT
  DATEFROMPARTS(YEAR(ShipDate), MONTH(ShipDate), 1) AS Month,
  SKU,
  SUM(Variance) AS variance
FROM vw_Variance
WHERE ShipDate BETWEEN @from AND @to
  AND (@carrier IS NULL OR Carrier = @carrier)
  AND (@sku IS NULL OR SKU = @sku)
GROUP BY DATEFROMPARTS(YEAR(ShipDate), MONTH(ShipDate), 1), SKU
ORDER BY Month, SKU
""",
    "fuel_surcharge_series": """
SELECT
  EffectiveDate,
  Percent
FROM vw_FuelSurcharge
WHERE EffectiveDate BETWEEN @from AND @to
  AND (@carrier IS NULL OR Carrier = @carrier)
ORDER BY EffectiveDate
""",
}
