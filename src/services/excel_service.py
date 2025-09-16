from __future__ import annotations

import os
import hashlib
import io
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime, timezone

try:  # pragma: no cover
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover
    pd = None  # type: ignore

from src.models.validation_models import ExcelFileMetadata
from src.utils.helpers import validate_email_format

logger = logging.getLogger(__name__)

class ExcelService:
    """Service for handling Excel file operations"""
    
    def __init__(self):
        # Load supported types from env, default to xlsx only (openpyxl)
        env_types = os.getenv('SUPPORTED_FILE_TYPES', 'xlsx')
        self.supported_formats = [f".{ext.strip().lower()}" for ext in env_types.split(',') if ext.strip()]

    @staticmethod
    def _require_pandas():
        if pd is None:  # pragma: no cover - exercised when pandas missing
            raise RuntimeError("pandas is required for Excel operations. Install it with 'pip install pandas'.")
    
    def parse_excel_file(self, file_data: bytes, filename: str) -> Tuple[Dict[str, pd.DataFrame], ExcelFileMetadata]:
        """
        Parse Excel file and return dataframes with metadata
        
        Args:
            file_data: Raw file bytes
            filename: Original filename
            
        Returns:
            Tuple of (sheet_data_dict, metadata)
        """
        self._require_pandas()
        try:
            # Create file-like object from bytes
            file_buffer = io.BytesIO(file_data)
            
            # Read all sheets
            sheets_dict = pd.read_excel(file_buffer, sheet_name=None, engine='openpyxl')
            
            # Calculate metadata
            total_rows = sum(len(df) for df in sheets_dict.values())
            total_columns = sum(len(df.columns) for df in sheets_dict.values())
            
            # Generate file ID from hash
            file_hash = hashlib.md5(file_data).hexdigest()
            file_id = f"excel_{file_hash}_{int(datetime.now(timezone.utc).timestamp())}"
            
            metadata = ExcelFileMetadata(
                file_id=file_id,
                filename=filename,
                upload_timestamp=datetime.now(timezone.utc),
                file_size=len(file_data),
                sheet_names=list(sheets_dict.keys()),
                total_rows=total_rows,
                total_columns=total_columns
            )
            
            logger.info(f"Successfully parsed Excel file: {filename} with {len(sheets_dict)} sheets")
            return sheets_dict, metadata
            
        except Exception as e:
            logger.error(f"Error parsing Excel file {filename}: {str(e)}")
            raise ValueError(f"Failed to parse Excel file: {str(e)}")
    
    def extract_data_for_validation(self, sheets_dict: Dict[str, pd.DataFrame], 
                                  target_sheet: str = None) -> pd.DataFrame:
        """
        self._require_pandas()
        Extract data from specific sheet or first sheet for validation
        
        Args:
            sheets_dict: Dictionary of sheet names to DataFrames
            target_sheet: Specific sheet name to extract (optional)
            
        Returns:
            DataFrame for validation
        """
        try:
            if target_sheet and target_sheet in sheets_dict:
                df = sheets_dict[target_sheet]
            else:
                # Use first sheet if no target specified
                df = list(sheets_dict.values())[0]
            
            # Clean the dataframe
            df = self._clean_dataframe(df)
            
            logger.info(f"Extracted data: {len(df)} rows, {len(df.columns)} columns")
            return df
            
        except Exception as e:
            logger.error(f"Error extracting data for validation: {str(e)}")
            raise ValueError(f"Failed to extract validation data: {str(e)}")
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean dataframe by removing empty rows and standardizing column names
        
        Args:
            df: Input DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        self._require_pandas()
        # Strip whitespace from string columns
        string_columns = df.select_dtypes(include=['object']).columns
        df[string_columns] = df[string_columns].astype(str).apply(lambda x: x.str.strip())
        
        # Replace common null-like strings with actual NaN
        df = df.replace({'nan': pd.NA, 'None': pd.NA, '': pd.NA})
        
        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]
        
        # Remove completely empty rows after cleaning
        df = df.dropna(how='all')

        return df
    
    def get_file_hash(self, file_data: bytes) -> str:
        """
        Generate MD5 hash of file content
        
        Args:
            file_data: Raw file bytes
            
        Returns:
            MD5 hash string
        """
        return hashlib.md5(file_data).hexdigest()
    
    def validate_file_format(self, filename: str) -> bool:
        """
        Validate if file format is supported
        
        Args:
            filename: Name of the file
            
        Returns:
            True if supported format
        """
        return any(filename.lower().endswith(fmt) for fmt in self.supported_formats)
    
    def extract_email_column(self, df: pd.DataFrame, email_field: str = "email") -> List[str]:
        """
        Extract email addresses from specified column
        
        Args:
            df: DataFrame to extract from
            email_field: Column name containing emails
            
        Returns:
            List of unique email addresses
        """
        try:
            if email_field not in df.columns:
                logger.warning(f"Email field '{email_field}' not found in data")
                return []
            
            # Extract unique, non-null email addresses
            emails = df[email_field].dropna().unique().tolist()
            
            # Validate with shared helper
            valid_emails = []
            for email in emails:
                email_str = str(email).strip().lower()
                if validate_email_format(email_str):
                    valid_emails.append(email_str)
            
            logger.info(f"Extracted {len(valid_emails)} valid email addresses")
            return valid_emails
            
        except Exception as e:
            logger.error(f"Error extracting email column: {str(e)}")
            return []
