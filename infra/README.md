Infrastructure-as-Code (IaC)

This folder contains Bicep and Terraform templates plus helper scripts to provision the core resources used by this solution inside your Azure tenant.

What it creates
- Storage account (Blob) for file landing and Function App storage
- Cosmos DB account + database + containers
- Azure Communication Services (Email)
- Azure AI Search service
- Azure Cognitive Services (Document Intelligence / Form Recognizer)
- Azure Function App (Linux, Python)
- Optional: Microsoft Fabric workspace via AzAPI (preview)
- Optional: App Service Authentication (EasyAuth) and API Management (APIM) for JWT auth and rate limiting

Quick start (Bicep)
1) Ensure Azure CLI is logged in: `az login`
2) Deploy resource group-level template:
   az deployment sub create \
     --name leftturn-bicep-$(date +%s) \
     --location eastus \
     --template-file infra/bicep/main.bicep \
     --parameters env=dev location=eastus baseName=leftturn${RANDOM} enableEasyAuth=false enableApim=false

Quick start (Terraform)
1) cd infra/terraform
2) terraform init
3) terraform apply -var 'env=dev' -var 'location=eastus' -var 'base_name=leftturn'

Seed assets
- Search data-plane: run `infra/scripts/seed_search.sh` to create data source (Blob), skillset (PII redaction + optional embeddings), index, and indexer (scheduled).
- Fabric SQL views: use files in `fabric/sql/` in your Fabric workspace SQL endpoint.
- Notebooks: import `notebooks/*.ipynb` into Microsoft Fabric.

APIM & EasyAuth
- EasyAuth: set `enableEasyAuth=true` and pass `aadTenantId` and `aadAllowedAudience` parameters to enforce AAD on the Function App.
- APIM: set `enableApim=true`. Use policy templates in `infra/apim/policies/` (global.xml) for JWT validation and rate limiting.

Embeddings for Search
- To populate vector embeddings automatically, set these before running `infra/scripts/seed_search.sh`:
  - `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_EMBED_DEPLOYMENT`

Notes
- Some resources (Search index, skillset) use data-plane APIs; ARM cannot create them directly, so we provide scripts.
- Microsoft Fabric ARM/TF support uses preview resource providers. AzAPI is used in Terraform to call RP if enabled.
