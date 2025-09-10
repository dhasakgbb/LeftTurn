#!/bin/bash

# Azure Excel Data Validation Agent Deployment Script

set -e  # Exit on any error

echo "🚀 Starting Azure Excel Data Validation Agent deployment..."

# Configuration
RESOURCE_GROUP=${RESOURCE_GROUP:-"excel-validation-rg"}
LOCATION=${LOCATION:-"eastus"}
FUNCTION_APP_NAME=${FUNCTION_APP_NAME:-"excel-validation-app"}
STORAGE_ACCOUNT_NAME=${STORAGE_ACCOUNT_NAME:-"excelvalidationstorage"}
COSMOSDB_ACCOUNT_NAME=${COSMOSDB_ACCOUNT_NAME:-"excel-validation-cosmos"}
COMMUNICATION_SERVICE_NAME=${COMMUNICATION_SERVICE_NAME:-"excel-validation-communication"}

echo "📋 Configuration:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo "  Function App: $FUNCTION_APP_NAME"
echo "  Storage Account: $STORAGE_ACCOUNT_NAME"
echo "  Cosmos DB Account: $COSMOSDB_ACCOUNT_NAME"
echo "  Communication Service: $COMMUNICATION_SERVICE_NAME"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first."
    exit 1
fi

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

echo "✅ Azure CLI is configured"

# Create resource group
echo "📦 Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create storage account
echo "💾 Creating storage account..."
az storage account create \
    --name $STORAGE_ACCOUNT_NAME \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Standard_LRS

# Get storage connection string
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
    --name $STORAGE_ACCOUNT_NAME \
    --resource-group $RESOURCE_GROUP \
    --query connectionString --output tsv)

echo "✅ Storage account created"

# Create Cosmos DB account
echo "🌍 Creating Cosmos DB account..."
az cosmosdb create \
    --name $COSMOSDB_ACCOUNT_NAME \
    --resource-group $RESOURCE_GROUP \
    --default-consistency-level Eventual \
    --locations regionName=$LOCATION failoverPriority=0 isZoneRedundant=False

# Get Cosmos DB connection string
COSMOSDB_CONNECTION_STRING=$(az cosmosdb keys list \
    --name $COSMOSDB_ACCOUNT_NAME \
    --resource-group $RESOURCE_GROUP \
    --type connection-strings \
    --query "connectionStrings[0].connectionString" --output tsv)

echo "✅ Cosmos DB account created"

# Create Communication Services resource
echo "📧 Creating Communication Services..."
az communication create \
    --name $COMMUNICATION_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --location "Global" \
    --data-location "United States"

# Get Communication Services connection string
COMMUNICATION_CONNECTION_STRING=$(az communication list-key \
    --name $COMMUNICATION_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --query primaryConnectionString --output tsv)

echo "✅ Communication Services created"

# Create Function App
echo "⚡ Creating Function App..."
az functionapp create \
    --resource-group $RESOURCE_GROUP \
    --consumption-plan-location $LOCATION \
    --runtime python \
    --runtime-version 3.9 \
    --functions-version 4 \
    --name $FUNCTION_APP_NAME \
    --storage-account $STORAGE_ACCOUNT_NAME \
    --os-type Linux

echo "✅ Function App created"

# Configure application settings
echo "⚙️  Configuring application settings..."
az functionapp config appsettings set \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        "AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONNECTION_STRING" \
        "AZURE_COSMOSDB_CONNECTION_STRING=$COSMOSDB_CONNECTION_STRING" \
        "AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING=$COMMUNICATION_CONNECTION_STRING" \
        "AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT:-}" \
        "AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY:-}" \
        "AZURE_OPENAI_MODEL=${AZURE_OPENAI_MODEL:-gpt-4.1}" \
        "DEFAULT_SENDER_EMAIL=${DEFAULT_SENDER_EMAIL:-noreply@yourdomain.com}"

echo "✅ Application settings configured"

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Resource Information:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Function App URL: https://$FUNCTION_APP_NAME.azurewebsites.net"
echo "  Storage Account: $STORAGE_ACCOUNT_NAME"
echo "  Cosmos DB Account: $COSMOSDB_ACCOUNT_NAME"
echo "  Communication Service: $COMMUNICATION_SERVICE_NAME"
echo ""
echo "📝 Next Steps:"
echo "1. Configure your Azure OpenAI endpoint and API key in the Function App settings"
echo "2. Set up email domain verification in Communication Services"
echo "3. Deploy your function code using 'func azure functionapp publish $FUNCTION_APP_NAME'"
echo "4. Test the health endpoint: https://$FUNCTION_APP_NAME.azurewebsites.net/api/health"
echo ""
echo "🔗 Useful URLs:"
echo "  Function App: https://portal.azure.com/#resource/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$FUNCTION_APP_NAME"
echo "  Storage Account: https://portal.azure.com/#resource/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT_NAME"
echo "  Cosmos DB: https://portal.azure.com/#resource/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.DocumentDB/databaseAccounts/$COSMOSDB_ACCOUNT_NAME"