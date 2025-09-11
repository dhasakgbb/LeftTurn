-- Canonical tables for contract entities extracted from Document Intelligence

CREATE TABLE IF NOT EXISTS dbo.ContractDocument (
    DocumentId NVARCHAR(64) NOT NULL,
    CarrierId NVARCHAR(64) NOT NULL,
    File NVARCHAR(256) NOT NULL,
    EffectiveDate DATE NULL,
    PRIMARY KEY (DocumentId)
);

CREATE TABLE IF NOT EXISTS dbo.ContractClause (
    DocumentId NVARCHAR(64) NOT NULL,
    ClauseId NVARCHAR(64) NULL,
    Page INT NULL,
    Text NVARCHAR(MAX) NOT NULL
);

CREATE TABLE IF NOT EXISTS dbo.RateCard (
    CarrierId NVARCHAR(64) NOT NULL,
    ServiceLevel NVARCHAR(64) NOT NULL,
    Zone NVARCHAR(8) NULL,
    WeightFrom DECIMAL(10,2) NULL,
    WeightTo DECIMAL(10,2) NULL,
    Rate DECIMAL(18,6) NOT NULL,
    EffectiveDate DATE NULL
);

CREATE TABLE IF NOT EXISTS dbo.Surcharge (
    CarrierId NVARCHAR(64) NOT NULL,
    Name NVARCHAR(128) NOT NULL,
    AmountType NVARCHAR(16) NOT NULL, -- 'percent' | 'flat'
    Value DECIMAL(18,6) NOT NULL,
    MinCharge DECIMAL(18,6) NULL,
    EffectiveDate DATE NULL
);

-- Optional: Fuel table already referenced by curated view
CREATE TABLE IF NOT EXISTS dbo.FuelTable (
    CarrierId NVARCHAR(64) NOT NULL,
    EffectiveDate DATE NOT NULL,
    Percent DECIMAL(9,6) NOT NULL
);

-- Helpful views
CREATE OR ALTER VIEW vw_ContractRates AS
SELECT CarrierId, ServiceLevel, Zone, WeightFrom, WeightTo, Rate, EffectiveDate
FROM dbo.RateCard;

CREATE OR ALTER VIEW vw_ContractSurcharges AS
SELECT CarrierId, Name, AmountType, Value, MinCharge, EffectiveDate
FROM dbo.Surcharge;

CREATE OR ALTER VIEW vw_ContractClauses AS
SELECT d.CarrierId, c.ClauseId, c.Page, c.Text, d.File, d.EffectiveDate
FROM dbo.ContractClause c
JOIN dbo.ContractDocument d ON d.DocumentId = c.DocumentId;

