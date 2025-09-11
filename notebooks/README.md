Fabric notebooks for ingestion and contract entity extraction.

- `carrier_unstructured.ipynb` — parses PDFs with Azure Document Intelligence and writes RateCard/Surcharge to Delta tables.
- `carrier_structured.ipynb` — structured carrier feeds (invoices/tracking/rating) consolidation.
- `erp_structured.ipynb` — ERP entities (orders/SKUs/customers).

Attach to a Lakehouse before run and set necessary environment variables (see notebook cells).

