-- Row-Level Security template for carrier-level filtering in Fabric Warehouse

-- Map AAD users (by SID) to CarrierId values they can access
CREATE TABLE IF NOT EXISTS dbo.UserCarrierAccess (
    UserSid VARBINARY(85) NOT NULL,
    CarrierId NVARCHAR(64) NOT NULL
);

-- Inline table-valued function used by the security policy
CREATE OR ALTER FUNCTION dbo.fn_rls_carrier (@CarrierId NVARCHAR(64))
RETURNS TABLE
WITH SCHEMABINDING
AS
RETURN SELECT 1 AS fn_access
WHERE EXISTS (
    SELECT 1
    FROM dbo.UserCarrierAccess u
    WHERE u.UserSid = SUSER_SID() AND u.CarrierId = @CarrierId
);

-- Apply to core fact tables. Adjust column names to match your schema.
-- Example assumes column 'Carrier' exists on these tables.
CREATE SECURITY POLICY IF NOT EXISTS dbo.CarrierRlsPolicy
ADD FILTER PREDICATE dbo.fn_rls_carrier(Carrier) ON dbo.FactInvoice,
ADD FILTER PREDICATE dbo.fn_rls_carrier(Carrier) ON dbo.FactShipment,
ADD FILTER PREDICATE dbo.fn_rls_carrier(Carrier) ON dbo.RatingOutput,
ADD FILTER PREDICATE dbo.fn_rls_carrier(Carrier) ON dbo.RateCard,
ADD FILTER PREDICATE dbo.fn_rls_carrier(CarrierId) ON dbo.Surcharge
WITH (STATE = ON);

