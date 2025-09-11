import logging
import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
try:
    from azure.storage.blob import BlobServiceClient
    from azure.cosmos import CosmosClient, PartitionKey
except Exception:  # pragma: no cover - allow running without Azure SDKs installed
    BlobServiceClient = None  # type: ignore
    CosmosClient = None  # type: ignore
    PartitionKey = None  # type: ignore
from src.models.validation_models import (
    ExcelFileMetadata, ValidationResult, EmailNotification, 
    ChangeTrackingRecord, ValidationStatus
)

logger = logging.getLogger(__name__)

class StorageService:
    """Service for managing storage and tracking using Azure Storage and Cosmos DB"""
    
    def __init__(self):
        self.blob_client = self._initialize_blob_client()
        self.cosmos_client = self._initialize_cosmos_client()
        self.container_name = "excel-files"
        self.database_name = "validation-tracking"
        self.containers = {
            "metadata": "file-metadata",
            "validations": "validation-results", 
            "emails": "email-notifications",
            "tracking": "change-tracking"
        }
        self._ensure_storage_exists()
    
    def _initialize_blob_client(self) -> Optional[BlobServiceClient]:
        """Initialize Azure Blob Storage client"""
        try:
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if not connection_string:
                logger.warning("Azure Storage connection string not configured")
                return None
            
            return BlobServiceClient.from_connection_string(connection_string)
        except Exception as e:
            logger.error(f"Failed to initialize blob client: {str(e)}")
            return None
    
    def _initialize_cosmos_client(self) -> Optional[CosmosClient]:
        """Initialize Azure Cosmos DB client"""
        try:
            connection_string = os.getenv("AZURE_COSMOSDB_CONNECTION_STRING")
            if not connection_string:
                logger.warning("Azure Cosmos DB connection string not configured")
                return None
            
            # Extract endpoint and key from connection string
            parts = connection_string.split(';')
            endpoint = next(part.split('=', 1)[1] for part in parts if part.startswith('AccountEndpoint='))
            key = next(part.split('=', 1)[1] for part in parts if part.startswith('AccountKey='))
            
            return CosmosClient(endpoint, key)
        except Exception as e:
            logger.error(f"Failed to initialize Cosmos client: {str(e)}")
            return None
    
    def _ensure_storage_exists(self):
        """Ensure required storage containers and databases exist"""
        try:
            # Create blob container if it doesn't exist
            if self.blob_client:
                try:
                    self.blob_client.create_container(self.container_name)
                except Exception:
                    pass  # Container might already exist
            
            # Create Cosmos database and containers
            if self.cosmos_client:
                try:
                    database = self.cosmos_client.create_database_if_not_exists(self.database_name)
                    
                    # Create containers with appropriate partition keys
                    database.create_container_if_not_exists(
                        id=self.containers["metadata"],
                        partition_key=PartitionKey(path="/file_id")
                    )
                    
                    database.create_container_if_not_exists(
                        id=self.containers["validations"],
                        partition_key=PartitionKey(path="/file_id")
                    )
                    
                    database.create_container_if_not_exists(
                        id=self.containers["emails"],
                        partition_key=PartitionKey(path="/file_id")
                    )
                    
                    database.create_container_if_not_exists(
                        id=self.containers["tracking"],
                        partition_key=PartitionKey(path="/file_id")
                    )
                    
                except Exception as e:
                    logger.error(f"Error creating Cosmos containers: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error ensuring storage exists: {str(e)}")
    
    def store_file(self, file_data: bytes, file_id: str, filename: str) -> bool:
        """
        Store Excel file in blob storage
        
        Args:
            file_data: Raw file bytes
            file_id: Unique file identifier
            filename: Original filename
            
        Returns:
            True if successful
        """
        if not self.blob_client:
            logger.error("Blob client not initialized")
            return False
        
        try:
            blob_name = f"{file_id}/{filename}"
            blob_client = self.blob_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.upload_blob(file_data, overwrite=True)
            logger.info(f"File stored successfully: {blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing file {file_id}: {str(e)}")
            return False
    
    def store_file_metadata(self, metadata: ExcelFileMetadata) -> bool:
        """
        Store file metadata in Cosmos DB
        
        Args:
            metadata: ExcelFileMetadata object
            
        Returns:
            True if successful
        """
        if not self.cosmos_client:
            logger.error("Cosmos client not initialized")
            return False
        
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client(self.containers["metadata"])
            
            # Convert to dict and add required fields
            item = metadata.model_dump()
            item['id'] = metadata.file_id
            item['timestamp'] = (
                metadata.upload_timestamp if isinstance(metadata.upload_timestamp, datetime) else datetime.now(timezone.utc)
            ).isoformat()
            
            container.create_item(item)
            logger.info(f"Metadata stored for file: {metadata.file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing metadata for {metadata.file_id}: {str(e)}")
            return False
    
    def store_validation_result(self, result: ValidationResult) -> bool:
        """
        Store validation result in Cosmos DB
        
        Args:
            result: ValidationResult object
            
        Returns:
            True if successful
        """
        if not self.cosmos_client:
            logger.error("Cosmos client not initialized")
            return False
        
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client(self.containers["validations"])
            
            # Convert to dict and prepare for storage
            item = result.model_dump()
            item['id'] = result.validation_id
            item['timestamp'] = (
                result.timestamp if isinstance(result.timestamp, datetime) else datetime.now(timezone.utc)
            ).isoformat()
            
            # Convert errors and warnings to serializable format
            item['errors'] = [error.dict() for error in result.errors]
            item['warnings'] = [warning.dict() for warning in result.warnings]
            
            container.create_item(item)
            logger.info(f"Validation result stored: {result.validation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing validation result {result.validation_id}: {str(e)}")
            return False
    
    def store_email_notification(self, notification: EmailNotification) -> bool:
        """
        Store email notification record in Cosmos DB
        
        Args:
            notification: EmailNotification object
            
        Returns:
            True if successful
        """
        if not self.cosmos_client:
            logger.error("Cosmos client not initialized")
            return False
        
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client(self.containers["emails"])
            
            # Convert to dict and prepare for storage
            item = notification.model_dump()
            item['id'] = notification.notification_id
            item['sent_timestamp'] = (
                notification.sent_timestamp if isinstance(notification.sent_timestamp, datetime) else datetime.now(timezone.utc)
            ).isoformat()
            
            if notification.correction_deadline:
                item['correction_deadline'] = notification.correction_deadline.isoformat()
            
            container.create_item(item)
            logger.info(f"Email notification stored: {notification.notification_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing email notification {notification.notification_id}: {str(e)}")
            return False

    def get_email_notification(self, notification_id: str) -> Optional[EmailNotification]:
        """Retrieve an email notification record by id from Cosmos DB."""
        if not self.cosmos_client:
            return None
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client(self.containers["emails"])
            query = "SELECT * FROM c WHERE c.id = @id"
            items = list(
                container.query_items(
                    query=query,
                    parameters=[{"name": "@id", "value": notification_id}],
                    enable_cross_partition_query=True,
                )
            )
            if not items:
                return None
            item = items[0]
            # Normalize timestamps
            if isinstance(item.get("sent_timestamp"), str):
                try:
                    item["sent_timestamp"] = datetime.fromisoformat(item["sent_timestamp"])  # type: ignore
                except Exception:
                    pass
            if isinstance(item.get("correction_deadline"), str):
                try:
                    item["correction_deadline"] = datetime.fromisoformat(item["correction_deadline"])  # type: ignore
                except Exception:
                    pass
            return EmailNotification(**item)
        except Exception as e:
            logger.error(f"Error retrieving email notification {notification_id}: {str(e)}")
            return None
    
    def create_change_tracking_record(self, file_id: str, validation_id: str, 
                                    original_file_hash: str) -> Optional[ChangeTrackingRecord]:
        """
        Create a change tracking record
        
        Args:
            file_id: File identifier
            validation_id: Validation identifier
            original_file_hash: Hash of original file
            
        Returns:
            ChangeTrackingRecord if successful
        """
        try:
            tracking_record = ChangeTrackingRecord(
                tracking_id=f"track_{file_id}_{int(datetime.now().timestamp())}",
                file_id=file_id,
                validation_id=validation_id,
                original_file_hash=original_file_hash
            )
            
            if self._store_tracking_record(tracking_record):
                return tracking_record
            
        except Exception as e:
            logger.error(f"Error creating tracking record for {file_id}: {str(e)}")
        
        return None
    
    def _store_tracking_record(self, record: ChangeTrackingRecord) -> bool:
        """Store change tracking record in Cosmos DB"""
        if not self.cosmos_client:
            return False
        
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client(self.containers["tracking"])
            
            item = record.dict()
            item['id'] = record.tracking_id
            
            if record.change_timestamp:
                item['change_timestamp'] = record.change_timestamp.isoformat()
            
            container.create_item(item)
            return True
            
        except Exception as e:
            logger.error(f"Error storing tracking record {record.tracking_id}: {str(e)}")
            return False
    
    def update_change_tracking(self, tracking_id: str, updated_file_hash: str, 
                             change_description: str = None, file_id: Optional[str] = None) -> bool:
        """
        Update change tracking record with new file information
        
        Args:
            tracking_id: Tracking record identifier
            updated_file_hash: Hash of updated file
            change_description: Description of changes made
            
        Returns:
            True if successful
        """
        if not self.cosmos_client:
            return False
        
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client(self.containers["tracking"])
            
            # Get existing record (prefer direct read with known partition key)
            if file_id:
                existing_item = container.read_item(tracking_id, partition_key=file_id)
            else:
                query = "SELECT * FROM c WHERE c.id = @id"
                items = list(container.query_items(
                    query=query,
                    parameters=[{"name": "@id", "value": tracking_id}],
                    enable_cross_partition_query=True
                ))
                if not items:
                    logger.error(f"Tracking record not found: {tracking_id}")
                    return False
                existing_item = items[0]
            
            # Update with new information
            existing_item['updated_file_hash'] = updated_file_hash
            existing_item['change_timestamp'] = datetime.now().isoformat()
            existing_item['verified'] = True
            
            if change_description:
                existing_item['change_description'] = change_description
            
            container.replace_item(existing_item['id'], existing_item)
            logger.info(f"Change tracking updated: {tracking_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating change tracking {tracking_id}: {str(e)}")
            return False
    
    def get_validation_result(self, validation_id: str) -> Optional[ValidationResult]:
        """
        Retrieve validation result by ID
        
        Args:
            validation_id: Validation identifier
            
        Returns:
            ValidationResult if found
        """
        if not self.cosmos_client:
            return None
        
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client(self.containers["validations"])
            
            # Query by id across partitions to avoid brittle partition key extraction
            query = "SELECT * FROM c WHERE c.id = @id"
            items = list(container.query_items(
                query=query,
                parameters=[{"name": "@id", "value": validation_id}],
                enable_cross_partition_query=True
            ))
            if not items:
                return None
            item = items[0]
            
            # Deserialize to ValidationResult
            return self._deserialize_validation_result(item)
            
        except Exception as e:
            logger.error(f"Error retrieving validation result {validation_id}: {str(e)}")
            return None
    
    def get_file_metadata(self, file_id: str) -> Optional[ExcelFileMetadata]:
        """
        Retrieve file metadata by ID
        
        Args:
            file_id: File identifier
            
        Returns:
            ExcelFileMetadata if found
        """
        if not self.cosmos_client:
            return None
        
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client(self.containers["metadata"])
            
            item = container.read_item(file_id, partition_key=file_id)
            
            # Convert timestamp back to datetime
            item['upload_timestamp'] = datetime.fromisoformat(item['timestamp'])
            
            return ExcelFileMetadata(**item)
            
        except Exception as e:
            logger.error(f"Error retrieving file metadata {file_id}: {str(e)}")
            return None

    def get_latest_validation_for_file(self, file_id: str) -> Optional[ValidationResult]:
        """Get the most recent validation result for a file."""
        if not self.cosmos_client:
            return None
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client(self.containers["validations"])
            # Query within the partition for latest by timestamp
            query = (
                "SELECT TOP 1 * FROM c WHERE c.file_id = @file_id ORDER BY c.timestamp DESC"
            )
            items = list(
                container.query_items(
                    query=query,
                    parameters=[{"name": "@file_id", "value": file_id}],
                    enable_cross_partition_query=False,
                )
            )
            if not items:
                return None
            return self._deserialize_validation_result(items[0])
        except Exception as e:
            logger.error(f"Error retrieving latest validation for {file_id}: {str(e)}")
            return None

    def get_change_history(self, file_id: str, limit: int = 50) -> List[ChangeTrackingRecord]:
        """Retrieve change tracking history for a file."""
        results: List[ChangeTrackingRecord] = []
        if not self.cosmos_client:
            return results
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client(self.containers["tracking"])
            query = (
                "SELECT TOP @limit * FROM c WHERE c.file_id = @file_id ORDER BY c.change_timestamp DESC"
            )
            items = list(
                container.query_items(
                    query=query,
                    parameters=[
                        {"name": "@file_id", "value": file_id},
                        {"name": "@limit", "value": limit},
                    ],
                    enable_cross_partition_query=False,
                )
            )
            for it in items:
                # Some records may not have change_timestamp yet
                if it.get("change_timestamp"):
                    try:
                        it["change_timestamp"] = datetime.fromisoformat(it["change_timestamp"])  # type: ignore
                    except Exception:
                        pass
                results.append(ChangeTrackingRecord(**it))
        except Exception as e:
            logger.error(f"Error retrieving change history for {file_id}: {str(e)}")
        return results

    def get_latest_tracking_for_file(self, file_id: str) -> Optional[ChangeTrackingRecord]:
        """Return the most recent change tracking record for a file, if any."""
        records = self.get_change_history(file_id, limit=1)
        return records[0] if records else None

    def _deserialize_validation_result(self, item: Dict[str, Any]) -> ValidationResult:
        """Convert a stored dict into a ValidationResult model."""
        try:
            # Normalize timestamp
            if isinstance(item.get("timestamp"), str):
                try:
                    item["timestamp"] = datetime.fromisoformat(item["timestamp"])  # type: ignore
                except Exception:
                    pass
            # Convert status string to enum value if needed
            if isinstance(item.get("status"), str):
                status_str = item["status"]
                if status_str.lower() == "passed":
                    item["status"] = ValidationStatus.PASSED
                elif status_str.lower() == "failed":
                    item["status"] = ValidationStatus.FAILED
                elif status_str.lower() == "pending":
                    item["status"] = ValidationStatus.PENDING
                else:
                    item["status"] = ValidationStatus.PENDING
            # Convert errors and warnings dicts to models if necessary
            def map_err(e: Any) -> Any:
                try:
                    return e if isinstance(e, dict) is False else e
                except Exception:
                    return e
            if isinstance(item.get("errors"), list):
                item["errors"] = [map_err(e) for e in item["errors"]]
            if isinstance(item.get("warnings"), list):
                item["warnings"] = [map_err(w) for w in item["warnings"]]
            # Pydantic will coerce dicts into the embedded models
            return ValidationResult(**item)
        except Exception as e:
            logger.error(f"Failed to deserialize ValidationResult {item.get('id')}: {str(e)}")
            # Fallback minimal object to avoid crashing callers
            return ValidationResult(
                file_id=item.get("file_id", "unknown"),
                validation_id=item.get("id", item.get("validation_id", "unknown")),
                status=ValidationStatus.PENDING,
                timestamp=datetime.now(timezone.utc),
                errors=[],
                warnings=[],
                total_errors=item.get("total_errors", 0),
                total_warnings=item.get("total_warnings", 0),
                processed_rows=item.get("processed_rows", 0),
            )

    # ----------------------------
    # Additional helpers for ops
    # ----------------------------

    def update_validation_status(self, validation_id: str, new_status: ValidationStatus) -> bool:
        """Update the status field of a validation record."""
        if not self.cosmos_client:
            return False
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client(self.containers["validations"])
            # Query by id; cross partition
            items = list(
                container.query_items(
                    query="SELECT * FROM c WHERE c.id = @id",
                    parameters=[{"name": "@id", "value": validation_id}],
                    enable_cross_partition_query=True,
                )
            )
            if not items:
                return False
            item = items[0]
            item["status"] = new_status.value if isinstance(new_status, ValidationStatus) else str(new_status)
            container.replace_item(item["id"], item)
            return True
        except Exception as e:
            logger.error(f"Error updating validation status {validation_id}: {str(e)}")
            return False

    def list_failed_validations(self, days_older_than: int = 3, limit: int = 100) -> List[ValidationResult]:
        """Return failed validations older than N days (for reminders)."""
        results: List[ValidationResult] = []
        if not self.cosmos_client:
            return results
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client(self.containers["validations"])
            # ISO instant cutoff
            from datetime import timedelta
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days_older_than)).isoformat()
            query = (
                "SELECT TOP @limit * FROM c WHERE c.status = 'failed' AND c.timestamp < @cutoff"
            )
            items = list(
                container.query_items(
                    query=query,
                    parameters=[
                        {"name": "@limit", "value": limit},
                        {"name": "@cutoff", "value": cutoff},
                    ],
                    enable_cross_partition_query=True,
                )
            )
            for it in items:
                try:
                    results.append(self._deserialize_validation_result(it))
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Error listing failed validations: {str(e)}")
        return results

    def list_email_recipients_for_validation(self, validation_id: str) -> List[str]:
        """Return distinct recipient emails recorded for a validation."""
        recipients: List[str] = []
        if not self.cosmos_client:
            return recipients
        try:
            database = self.cosmos_client.get_database_client(self.database_name)
            container = database.get_container_client(self.containers["emails"])
            items = list(
                container.query_items(
                    query=(
                        "SELECT c.recipient_email FROM c WHERE c.validation_id = @vid"
                    ),
                    parameters=[{"name": "@vid", "value": validation_id}],
                    enable_cross_partition_query=True,
                )
            )
            recipients = sorted({it.get("recipient_email") for it in items if it.get("recipient_email")})  # type: ignore
        except Exception as e:
            logger.error(f"Error listing recipients for validation {validation_id}: {str(e)}")
        return recipients
