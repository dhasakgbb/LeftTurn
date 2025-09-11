-- Curated views for logistics analytics in Microsoft Fabric

CREATE OR ALTER VIEW vw_FactInvoice AS
SELECT * FROM dbo.FactInvoice;

CREATE OR ALTER VIEW vw_FactShipment AS
SELECT * FROM dbo.FactShipment;

CREATE OR ALTER VIEW vw_Variance AS
SELECT 
    i.InvoiceId,
    i.Carrier,
    i.ServiceLevel,
    i.SKU,
    i.ShipDate,
    i.BilledAmount,
    r.RatedAmount,
    (i.BilledAmount - r.RatedAmount) AS Variance,
    r.Reason
FROM dbo.FactInvoice i
LEFT JOIN dbo.RatingOutput r
  ON r.InvoiceLineId = i.InvoiceLineId;

CREATE OR ALTER VIEW vw_FuelSurcharge AS
SELECT Carrier, EffectiveDate, Percent
FROM dbo.FuelTable;
