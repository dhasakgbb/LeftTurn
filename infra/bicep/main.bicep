@description('Deployment environment tag, e.g., dev/test/prod')
param env string

@description('Azure location, e.g., eastus')
param location string

@description('Base name prefix for resources (letters and numbers only)')
param baseName string
@description('Enable EasyAuth (App Service Authentication) with AAD')
param enableEasyAuth bool = false
@description('AAD tenant Id for EasyAuth')
@secure()
param aadTenantId string = ''
@description('Allowed audience (App registration client ID or Application ID URI)')
param aadAllowedAudience string = ''

@minLength(3)
@maxLength(24)
var storageName = toLower(replace('${baseName}stor', '-', ''))
var funcName    = toLower('${baseName}-func-${env}')
var cosmosName  = toLower(replace('${baseName}-cosmos', '_', ''))
var searchName  = toLower(replace('${baseName}-search', '_', ''))
var commName    = toLower(replace('${baseName}-comm', '_', ''))
var cogName     = toLower(replace('${baseName}-cog', '_', ''))

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' existing = {
  name: resourceGroup().name
}

// Storage account
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

// Cosmos DB account (Serverless)
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: cosmosName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    databaseAccountOfferType: 'Standard'
    enableFreeTier: true
    capabilities: [
      { name: 'EnableServerless' }
    ]
  }
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-04-15' = {
  name: '${cosmos.name}/validation-tracking'
  properties: { resource: { id: 'validation-tracking' } }
}

resource containerMetadata 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  name: '${cosmos.name}/${cosmosDb.name}/file-metadata'
  properties: {
    resource: {
      id: 'file-metadata'
      partitionKey: { paths: ['/file_id'], kind: 'Hash' }
    }
  }
}

resource containerValidations 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  name: '${cosmos.name}/${cosmosDb.name}/validation-results'
  properties: {
    resource: {
      id: 'validation-results'
      partitionKey: { paths: ['/file_id'], kind: 'Hash' }
    }
  }
}

resource containerEmails 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  name: '${cosmos.name}/${cosmosDb.name}/email-notifications'
  properties: {
    resource: {
      id: 'email-notifications'
      partitionKey: { paths: ['/file_id'], kind: 'Hash' }
    }
  }
}

resource containerTracking 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  name: '${cosmos.name}/${cosmosDb.name}/change-tracking'
  properties: {
    resource: {
      id: 'change-tracking'
      partitionKey: { paths: ['/file_id'], kind: 'Hash' }
    }
  }
}

// Communication Services (Email)
resource comm 'Microsoft.Communication/communicationServices@2023-03-31' = {
  name: commName
  location: 'Global'
  properties: {
    dataLocation: 'United States'
  }
}

// Cognitive Services: Document Intelligence (Form Recognizer)
resource cog 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: cogName
  location: location
  kind: 'FormRecognizer'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: toLower('${baseName}${env}docint')
  }
}

// Azure AI Search (control plane)
resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchName
  location: location
  sku: { name: 'basic' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
  }
}

// Function App Plan (Consumption) and App
resource plan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: '${baseName}-plan-${env}'
  location: location
  sku: { name: 'Y1', tier: 'Dynamic' }
  kind: 'linux'
}

resource func 'Microsoft.Web/sites@2022-03-01' = {
  name: funcName
  location: location
  kind: 'functionapp,linux'
  properties: {
    serverFarmId: plan.id
    siteConfig: {
      linuxFxVersion: 'Python|3.10'
      authSettingsV2: enableEasyAuth ? {
        platform: { enabled: true }
        globalValidation: { requireAuthentication: true }
        identityProviders: {
          azureActiveDirectory: {
            enabled: true
            registration: { openIdIssuer: 'https://login.microsoftonline.com/${aadTenantId}/v2.0' }
            validation: { allowedAudiences: [ aadAllowedAudience ] }
          }
        }
        login: { tokenStore: { enabled: true } }
      } : null
      appSettings: [
        { name: 'AzureWebJobsStorage', value: storage.listKeys().keys[0].value }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'AZURE_STORAGE_CONNECTION_STRING', value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=core.windows.net' }
        { name: 'AZURE_COSMOSDB_CONNECTION_STRING', value: listKeys(cosmos.id, '2023-04-15').primaryMasterKey }
        { name: 'AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING', value: listKeys(comm.id, '2023-03-31').primaryConnectionString }
      ]
    }
    httpsOnly: true
  }
}

// API Management (optional)
@description('Deploy API Management (APIM) and import Function App endpoints')
param enableApim bool = false
@description('APIM SKU (Consumption or Developer recommended for dev)')
param apimSkuName string = 'Consumption'

resource apim 'Microsoft.ApiManagement/service@2023-05-01-preview' = if (enableApim) {
  name: '${baseName}-apim-${env}'
  location: location
  sku: { name: apimSkuName, capacity: 0 }
  properties: {
    publisherName: 'leftturn'
    publisherEmail: 'admin@example.com'
  }
}


output functionAppName string = func.name
output storageAccountName string = storage.name
output cosmosAccountName string = cosmos.name
output searchServiceName string = search.name
output communicationServiceName string = comm.name
output cognitiveServicesName string = cog.name
