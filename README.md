# Azure Excel Data Validation Agent

This project implements an intelligent Azure-based agent that processes Excel files, validates data, sends email notifications for corrections, and tracks changes.

## Architecture

The agent uses the following Azure services:

- **Azure Functions**: Serverless execution for processing Excel files and validation
- **Azure AI Services**: Intelligent data validation and analysis using GPT models
- **Azure Communication Services**: Email notifications and lookups
- **Azure Storage**: State tracking and change validation
- **Azure Cosmos DB**: Metadata and tracking storage

## Workflow

1. Customer uploads Excel sheet
2. Agent validates data using AI-powered validation rules
3. If correct: No action taken
4. If incorrect: Agent looks up email and sends notification
5. Agent tracks and validates when changes are made

## Development Setup

### Prerequisites
- Python 3.9+
- Azure CLI
- Azure Functions Core Tools v4
- An Azure subscription

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and configure your Azure settings:

```bash
cp .env.example .env
```

### Running Locally

```bash
func start
```

## Deployment

Deploy to Azure using the provided deployment script:

```bash
./deploy.sh
```

## Project Structure

```
├── .github/
│   └── copilot-instructions.md
├── src/
│   ├── functions/
│   │   ├── excel_processor/
│   │   ├── data_validator/
│   │   ├── email_sender/
│   │   └── change_tracker/
│   ├── services/
│   │   ├── excel_service.py
│   │   ├── validation_service.py
│   │   ├── email_service.py
│   │   └── storage_service.py
│   ├── models/
│   │   └── validation_models.py
│   └── utils/
│       └── helpers.py
├── tests/
├── requirements.txt
├── host.json
├── local.settings.json
├── function_app.py
├── .env.example
└── README.md
```

## Configuration

The agent requires the following environment variables:

- `AZURE_STORAGE_CONNECTION_STRING`: Connection string for Azure Storage
- `AZURE_COSMOSDB_CONNECTION_STRING`: Connection string for Cosmos DB
- `AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING`: Connection string for Communication Services
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key
- `AZURE_OPENAI_MODEL`: Model name (e.g., gpt-4.1)

Optional configuration (with defaults):

- `SUPPORTED_FILE_TYPES`: Comma-separated list of allowed file extensions (without the dot). Default: `xlsx`.
- `MAX_FILE_SIZE_MB`: Maximum upload size in megabytes for `/api/process`. Default: `50`.
- `DEFAULT_SENDER_EMAIL`: Sender address for email notifications. Default: `noreply@yourdomain.com`.

Notes:

- Only `.xlsx` is supported by default. Legacy `.xls` is not enabled because the configured reader uses `openpyxl`.
- Requests exceeding `MAX_FILE_SIZE_MB` return HTTP 413 (Payload Too Large).
- Timestamps in responses, storage records, and emails are UTC.

## License

MIT License
