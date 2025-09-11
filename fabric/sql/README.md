SQL assets for Microsoft Fabric (Warehouse SQL endpoint).

Contents
- `create_views_carrier.sql` — curated views (e.g., vw_Variance, vw_FuelSurcharge).
- `create_tables_contracts.sql` — canonical tables for contract entities (RateCard, Surcharge, ContractDocument/Clause).
- `rls_carrier.sql` — row‑level security policy template filtering by Carrier.

Usage
1) Run `create_tables_contracts.sql` to seed tables (Delta managed tables).
2) Run `create_views_carrier.sql` to create curated views used by agents and BI.
3) Apply `rls_carrier.sql` and populate `dbo.UserCarrierAccess` with AAD SIDs.

