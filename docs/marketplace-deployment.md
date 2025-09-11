# Marketplace Deployment

This package enables provisioning LeftTurn resources through Azure's Commercial Marketplace as a managed application.

## Customer deployment
1. Locate the **LeftTurn** offer in Azure Marketplace and select **Create**.
2. Provide a *Workspace Name* (3–24 alphanumeric characters).
3. Optionally enable **EasyAuth** and supply the AAD tenant ID and allowed audience.
4. Review the summary and create the resources.

The template provisions the Function App, Storage, Cosmos DB, Communication Services, Cognitive Services, Search, and optional API Management resources required by LeftTurn.

## Publisher workflow
For maintainers publishing updates:

```bash
cd infra/managedapp
./package.sh        # build mainTemplate.json and package zip
export OFFER_ID=<partner center offer id>
./publish.sh        # uploads package using Partner Center CLI
```

Complete the offer submission in [Azure Partner Center](https://partner.microsoft.com/) to make the offer available to customers.
