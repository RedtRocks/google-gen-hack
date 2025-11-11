"""
Azure Blob Storage Service for Legal Document Demystifier
Handles file uploads, downloads, and management in Azure Blob Storage
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
import logging

logger = logging.getLogger(__name__)


class AzureStorageService:
    """Service for managing file storage in Azure Blob Storage"""
    
    def __init__(self):
        """Initialize Azure Blob Storage client"""
        self.connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "documents")
        
        if not self.connection_string:
            logger.warning("AZURE_STORAGE_CONNECTION_STRING not set. File storage disabled.")
            self.blob_service_client = None
            return
        
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
            # Ensure container exists
            self._ensure_container_exists()
            logger.info(f"Azure Blob Storage initialized. Container: {self.container_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Azure Blob Storage: {str(e)}")
            self.blob_service_client = None
    
    def _ensure_container_exists(self):
        """Create container if it doesn't exist"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            if not container_client.exists():
                container_client.create_container()
                logger.info(f"Created container: {self.container_name}")
        except Exception as e:
            logger.error(f"Error ensuring container exists: {str(e)}")
    
    def is_enabled(self) -> bool:
        """Check if storage service is enabled"""
        return self.blob_service_client is not None
    
    def upload_file(
        self, 
        file_content: bytes, 
        filename: str, 
        content_type: str = "application/pdf",
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to Azure Blob Storage
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            content_type: MIME type of the file
            metadata: Additional metadata to store with the file
        
        Returns:
            Dictionary with upload details (blob_name, url, size, etc.)
        """
        if not self.is_enabled():
            raise Exception("Azure Storage is not configured")
        
        try:
            # Generate unique blob name
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            file_extension = os.path.splitext(filename)[1]
            blob_name = f"{timestamp}_{unique_id}_{filename}"
            
            # Prepare metadata
            blob_metadata = {
                "original_filename": filename,
                "upload_timestamp": datetime.utcnow().isoformat(),
                "content_type": content_type,
                "file_size": str(len(file_content))
            }
            if metadata:
                blob_metadata.update(metadata)
            
            # Upload to blob storage
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_settings={
                    "content_type": content_type
                },
                metadata=blob_metadata
            )
            
            # Get blob properties
            properties = blob_client.get_blob_properties()
            
            result = {
                "blob_name": blob_name,
                "url": blob_client.url,
                "size": len(file_content),
                "content_type": content_type,
                "created_at": properties.creation_time.isoformat(),
                "metadata": blob_metadata
            }
            
            logger.info(f"File uploaded successfully: {blob_name} ({len(file_content)} bytes)")
            return result
            
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise
    
    def download_file(self, blob_name: str) -> bytes:
        """
        Download a file from Azure Blob Storage
        
        Args:
            blob_name: Name of the blob to download
        
        Returns:
            File content as bytes
        """
        if not self.is_enabled():
            raise Exception("Azure Storage is not configured")
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            download_stream = blob_client.download_blob()
            file_content = download_stream.readall()
            
            logger.info(f"File downloaded successfully: {blob_name}")
            return file_content
            
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            raise
    
    def get_file_url(self, blob_name: str, expiry_hours: int = 24) -> str:
        """
        Get a temporary SAS URL for accessing a file
        
        Args:
            blob_name: Name of the blob
            expiry_hours: Hours until the URL expires
        
        Returns:
            Temporary URL with SAS token
        """
        if not self.is_enabled():
            raise Exception("Azure Storage is not configured")
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.blob_service_client.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=self.blob_service_client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
            )
            
            # Construct URL with SAS token
            sas_url = f"{blob_client.url}?{sas_token}"
            return sas_url
            
        except Exception as e:
            logger.error(f"Error generating SAS URL: {str(e)}")
            raise
    
    def list_files(self, prefix: str = "", max_results: int = 100) -> List[Dict[str, Any]]:
        """
        List files in the container
        
        Args:
            prefix: Filter files by prefix
            max_results: Maximum number of files to return
        
        Returns:
            List of file information dictionaries
        """
        if not self.is_enabled():
            raise Exception("Azure Storage is not configured")
        
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            
            blobs = container_client.list_blobs(
                name_starts_with=prefix,
                include=['metadata']
            )
            
            files = []
            for blob in blobs:
                if len(files) >= max_results:
                    break
                
                files.append({
                    "name": blob.name,
                    "size": blob.size,
                    "created_at": blob.creation_time.isoformat(),
                    "content_type": blob.content_settings.content_type if blob.content_settings else None,
                    "metadata": blob.metadata
                })
            
            logger.info(f"Listed {len(files)} files")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise
    
    def delete_file(self, blob_name: str) -> bool:
        """
        Delete a file from Azure Blob Storage
        
        Args:
            blob_name: Name of the blob to delete
        
        Returns:
            True if deleted successfully
        """
        if not self.is_enabled():
            raise Exception("Azure Storage is not configured")
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.delete_blob()
            logger.info(f"File deleted successfully: {blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            raise
    
    def get_file_metadata(self, blob_name: str) -> Dict[str, Any]:
        """
        Get metadata for a specific file
        
        Args:
            blob_name: Name of the blob
        
        Returns:
            File metadata dictionary
        """
        if not self.is_enabled():
            raise Exception("Azure Storage is not configured")
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            properties = blob_client.get_blob_properties()
            
            return {
                "name": blob_name,
                "size": properties.size,
                "content_type": properties.content_settings.content_type,
                "created_at": properties.creation_time.isoformat(),
                "last_modified": properties.last_modified.isoformat(),
                "metadata": properties.metadata
            }
            
        except Exception as e:
            logger.error(f"Error getting file metadata: {str(e)}")
            raise


# Global storage service instance
storage_service = AzureStorageService()
