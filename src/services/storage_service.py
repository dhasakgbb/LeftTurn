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
            
            # Convert back to ValidationResult object
            # This would need proper deserialization logic
            return ValidationResult(**item)
            
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
