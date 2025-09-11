import hashlib
import re
import logging
from typing import List, Dict, Any
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

def generate_file_hash(file_data: bytes) -> str:
    """
    Generate MD5 hash for file data
    
    Args:
        file_data: Raw file bytes
        
    Returns:
        MD5 hash string
    """
    return hashlib.md5(file_data).hexdigest()

def validate_email_format(email: str) -> bool:
    """
    Validate email format using regex
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid email format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip().lower()))

def extract_emails_from_text(text: str) -> List[str]:
    """
    Extract email addresses from text using regex
    
    Args:
        text: Text to search for emails
        
    Returns:
        List of unique email addresses found
    """
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(pattern, str(text))
    return list(set(email.lower() for email in emails if validate_email_format(email)))

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing special characters
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove special characters but keep dots and underscores
    sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
    return sanitized.strip()

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    size = size_bytes
    i = 0
    
    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"

def generate_unique_id(prefix: str = "") -> str:
    """
    Generate unique identifier with timestamp
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        Unique identifier string
    """
    timestamp = int(datetime.now().timestamp() * 1000)  # Include milliseconds
    if prefix:
        return f"{prefix}_{timestamp}"
    return str(timestamp)

def safe_get_dict_value(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Safely get value from dictionary with nested key support
    
    Args:
        data: Dictionary to search
        key: Key to look for (supports dot notation for nested keys)
        default: Default value if key not found
        
    Returns:
        Value if found, default otherwise
    """
    try:
        if '.' in key:
            keys = key.split('.')
            value = data
            for k in keys:
                value = value[k]
            return value
        else:
            return data.get(key, default)
    except (KeyError, TypeError):
        return default

def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length allowed
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def extract_param_value(text: str, key: str) -> str | None:
    """Extract a value for a given key from free text.

    Supports forms like:
    - "key: value"
    - "key=value"
    - "key value"
    Value may be quoted or unquoted; hyphens and dots are allowed.
    Returns None when not found.
    """
    import re
    try:
        pattern = rf"{re.escape(key)}[:=\s]+(?:(['\"])(.*?)\1|([\w\-.]+))"
        m = re.search(pattern, text, re.IGNORECASE)
        if not m:
            return None
        return (m.group(2) or m.group(3))
    except Exception:
        return None

def parse_azure_connection_string(connection_string: str) -> Dict[str, str]:
    """
    Parse Azure connection string into components
    
    Args:
        connection_string: Azure connection string
        
    Returns:
        Dictionary with connection components
    """
    components = {}
    
    try:
        parts = connection_string.split(';')
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                components[key] = value
    except Exception as e:
        logger.error(f"Error parsing connection string: {str(e)}")
    
    return components

def validate_azure_config() -> Dict[str, bool]:
    """
    Validate that required Azure configuration is present
    
    Returns:
        Dictionary with validation results for each service
    """
    import os
    
    config_status = {
        'storage': bool(os.getenv('AZURE_STORAGE_CONNECTION_STRING')),
        'cosmosdb': bool(os.getenv('AZURE_COSMOSDB_CONNECTION_STRING')),
        'communication': bool(os.getenv('AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING')),
        'openai': bool(os.getenv('AZURE_OPENAI_ENDPOINT') and os.getenv('AZURE_OPENAI_API_KEY'))
    }
    
    return config_status


def validate_stack_readiness() -> Dict[str, Any]:
    """Return a consolidated readiness map for major integrations.

    This is used by readiness/health endpoints to give operators a quick
    view of which components are configured. It avoids making network calls
    and only checks presence of required environment variables.
    """
    import os

    def _tf(v: str | None) -> bool:
        return bool(v and v.strip())

    fabric = {
        "endpoint": _tf(os.getenv("FABRIC_ENDPOINT")),
        "token": _tf(os.getenv("FABRIC_TOKEN")),
    }
    search = {
        "endpoint": _tf(os.getenv("SEARCH_ENDPOINT")),
        "index": _tf(os.getenv("SEARCH_INDEX")),
        "apiKey": _tf(os.getenv("SEARCH_API_KEY")),
        "apiVersion": _tf(os.getenv("SEARCH_API_VERSION")),
        "semantic": os.getenv("SEARCH_USE_SEMANTIC", "false"),
        "hybrid": os.getenv("SEARCH_HYBRID", "false"),
    }
    graph = {
        "endpoint": _tf(os.getenv("GRAPH_ENDPOINT")),
        "token": _tf(os.getenv("GRAPH_TOKEN")),
    }
    power_bi = {
        "workspace": _tf(os.getenv("PBI_WORKSPACE_ID")),
        "report": _tf(os.getenv("PBI_REPORT_ID")),
        "dateColumn": os.getenv("PBI_DATE_COLUMN", "vw_Variance/ShipDate"),
    }
    storage = {
        "blob": _tf(os.getenv("AZURE_STORAGE_CONNECTION_STRING")),
        "cosmos": _tf(os.getenv("AZURE_COSMOSDB_CONNECTION_STRING")),
        "comm": _tf(os.getenv("AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING")),
    }
    openai = {
        "endpoint": _tf(os.getenv("AZURE_OPENAI_ENDPOINT")),
        "apiKey": _tf(os.getenv("AZURE_OPENAI_API_KEY")),
        "embedDeployment": os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", ""),
    }

    return {
        "fabric": fabric,
        "search": search,
        "graph": graph,
        "powerBi": power_bi,
        "storage": storage,
        "openai": openai,
        "ready": all([
            fabric["endpoint"],
            search["endpoint"],
            search["index"],
        ]),
    }

def log_function_execution(func_name: str, start_time: datetime, 
                          end_time: datetime, success: bool, 
                          additional_info: Dict[str, Any] = None):
    """
    Log function execution details
    
    Args:
        func_name: Name of the function
        start_time: Execution start time
        end_time: Execution end time
        success: Whether execution was successful
        additional_info: Additional information to log
    """
    execution_time = (end_time - start_time).total_seconds()
    status = "SUCCESS" if success else "FAILED"
    
    log_message = f"Function {func_name} {status} - Duration: {execution_time:.3f}s"
    
    if additional_info:
        info_str = ", ".join([f"{k}: {v}" for k, v in additional_info.items()])
        log_message += f" - {info_str}"
    
    if success:
        logger.info(log_message)
    else:
        logger.error(log_message)

def get_correlation_id(req) -> str:
    """Retrieve or generate a correlation ID from an HTTP request."""
    try:
        cid = req.headers.get('x-correlation-id')  # type: ignore[attr-defined]
        if cid and isinstance(cid, str) and len(cid) >= 8:
            return cid
        logger.warning("Missing or invalid correlation ID; generating a new one.")
    except Exception as e:
        logger.warning(f"Failed to retrieve correlation ID: {e}; generating a new one.")
    return str(uuid.uuid4())

class ConfigurationError(Exception):
    """Custom exception for configuration errors."""

class ValidationError(Exception):
    """Custom exception for validation errors."""

class StorageError(Exception):
    """Custom exception for storage errors."""

class EmailError(Exception):
    """Custom exception for email errors."""
