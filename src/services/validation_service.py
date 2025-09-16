from __future__ import annotations

try:  # pragma: no cover
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover
    pd = None  # type: ignore
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
try:
    from azure.ai.inference import ChatCompletionsClient
    from azure.ai.inference.models import SystemMessage, UserMessage
    from azure.core.credentials import AzureKeyCredential
except Exception:  # pragma: no cover - allow running without Azure SDKs installed
    ChatCompletionsClient = None  # type: ignore
    SystemMessage = None  # type: ignore
    UserMessage = None  # type: ignore
    AzureKeyCredential = None  # type: ignore
from src.models.validation_models import ValidationRule, ValidationError, ValidationResult, ValidationStatus

logger = logging.getLogger(__name__)

class ValidationService:
    """Service for data validation using Azure AI"""
    
    def __init__(self):
        self.ai_client = self._initialize_ai_client()
        self.default_rules = self._get_default_validation_rules()

    @staticmethod
    def _require_pandas():
        if pd is None:  # pragma: no cover
            raise RuntimeError("pandas is required for ValidationService. Install it with 'pip install pandas'.")
    
    def _initialize_ai_client(self) -> Optional[ChatCompletionsClient]:
        """Initialize Azure AI client"""
        try:
            if ChatCompletionsClient is None or AzureKeyCredential is None:
                logger.warning("Azure OpenAI SDK not available; AI suggestions disabled")
                return None
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            
            if not endpoint or not api_key:
                logger.warning("Azure OpenAI credentials not configured")
                return None
            
            return ChatCompletionsClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(api_key)
            )
        except Exception as e:
            logger.error(f"Failed to initialize AI client: {str(e)}")
            return None
    
    def _get_default_validation_rules(self) -> List[ValidationRule]:
        """Get default validation rules"""
        return [
            ValidationRule(
                rule_id="email_format",
                rule_name="Email Format Validation",
                description="Validate email format",
                rule_type="format",
                parameters={
                    "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                    "columns": ["email"]
                },
                severity="error"
            ),
            ValidationRule(
                rule_id="required_fields",
                rule_name="Required Fields",
                description="Check for required field completion",
                rule_type="custom",
                parameters={"required_columns": []},
                severity="error"
            ),
            ValidationRule(
                rule_id="data_consistency",
                rule_name="Data Consistency",
                description="Check for data consistency across rows",
                rule_type="custom",
                parameters={},
                severity="warning"
            )
        ]
    
    def validate_data(self, df: pd.DataFrame, file_id: str, 
                     custom_rules: List[ValidationRule] = None) -> ValidationResult:
        """
        Validate DataFrame using specified rules
        
        Args:
            df: DataFrame to validate
            file_id: Unique file identifier
            custom_rules: Custom validation rules
            
        Returns:
            ValidationResult object
        """
        self._require_pandas()
        validation_id = f"val_{file_id}_{int(datetime.now(timezone.utc).timestamp())}"
        
        # Combine default and custom rules
        rules = self.default_rules.copy()
        if custom_rules:
            rules.extend(custom_rules)
        
        errors = []
        warnings = []
        
        # Apply each validation rule
        for rule in rules:
            rule_errors = self._apply_validation_rule(df, rule)
            
            for error in rule_errors:
                if error.severity == "error":
                    errors.append(error)
                else:
                    warnings.append(error)
        
        # Use AI for intelligent validation if available
        if self.ai_client and len(errors) > 0:
            ai_suggestions = self._get_ai_suggestions(df, errors)
            for i, error in enumerate(errors):
                if i < len(ai_suggestions):
                    error.suggested_correction = ai_suggestions[i]
        
        # Determine overall status
        status = ValidationStatus.FAILED if errors else ValidationStatus.PASSED
        
        result = ValidationResult(
            file_id=file_id,
            validation_id=validation_id,
            status=status,
            timestamp=datetime.now(timezone.utc),
            errors=errors,
            warnings=warnings,
            total_errors=len(errors),
            total_warnings=len(warnings),
            processed_rows=len(df)
        )
        
        logger.info(f"Validation completed: {len(errors)} errors, {len(warnings)} warnings")
        return result
    
    def _apply_validation_rule(self, df: pd.DataFrame, rule: ValidationRule) -> List[ValidationError]:
        """Apply a single validation rule to the DataFrame"""
        errors = []
        
        try:
            if rule.rule_type == "format":
                errors.extend(self._validate_format(df, rule))
            elif rule.rule_type == "range":
                errors.extend(self._validate_range(df, rule))
            elif rule.rule_type == "data_type":
                errors.extend(self._validate_data_type(df, rule))
            elif rule.rule_type == "custom":
                errors.extend(self._validate_custom(df, rule))
            
        except Exception as e:
            logger.error(f"Error applying validation rule {rule.rule_id}: {str(e)}")
        
        return errors
    
    def _validate_format(self, df: pd.DataFrame, rule: ValidationRule) -> List[ValidationError]:
        """Validate format using regex patterns"""
        errors = []
        pattern = rule.parameters.get("pattern", "")
        columns = rule.parameters.get("columns", df.columns)
        
        for col in columns:
            if col in df.columns:
                for idx, value in df[col].items():
                    if pd.notna(value):
                        import re
                        if not re.match(pattern, str(value)):
                            errors.append(ValidationError(
                                row=idx + 1,
                                column=col,
                                value=value,
                                rule_id=rule.rule_id,
                                message=f"Value does not match expected format: {rule.description}",
                                severity=rule.severity
                            ))
        
        return errors
    
    def _validate_range(self, df: pd.DataFrame, rule: ValidationRule) -> List[ValidationError]:
        """Validate numeric ranges"""
        errors = []
        min_val = rule.parameters.get("min")
        max_val = rule.parameters.get("max")
        columns = rule.parameters.get("columns", [])
        
        for col in columns:
            if col in df.columns:
                for idx, value in df[col].items():
                    if pd.notna(value):
                        try:
                            num_val = float(value)
                            if min_val is not None and num_val < min_val:
                                errors.append(ValidationError(
                                    row=idx + 1,
                                    column=col,
                                    value=value,
                                    rule_id=rule.rule_id,
                                    message=f"Value {num_val} is below minimum {min_val}",
                                    severity=rule.severity
                                ))
                            elif max_val is not None and num_val > max_val:
                                errors.append(ValidationError(
                                    row=idx + 1,
                                    column=col,
                                    value=value,
                                    rule_id=rule.rule_id,
                                    message=f"Value {num_val} is above maximum {max_val}",
                                    severity=rule.severity
                                ))
                        except ValueError:
                            errors.append(ValidationError(
                                row=idx + 1,
                                column=col,
                                value=value,
                                rule_id=rule.rule_id,
                                message=f"Value is not numeric: {value}",
                                severity=rule.severity
                            ))
        
        return errors
    
    def _validate_data_type(self, df: pd.DataFrame, rule: ValidationRule) -> List[ValidationError]:
        """Validate data types"""
        errors = []
        expected_type = rule.parameters.get("expected_type")
        columns = rule.parameters.get("columns", [])
        
        for col in columns:
            if col in df.columns:
                for idx, value in df[col].items():
                    if pd.notna(value):
                        if expected_type == "int" and not isinstance(value, int):
                            try:
                                int(value)
                            except (ValueError, TypeError):
                                errors.append(ValidationError(
                                    row=idx + 1,
                                    column=col,
                                    value=value,
                                    rule_id=rule.rule_id,
                                    message=f"Expected integer, got {type(value).__name__}",
                                    severity=rule.severity
                                ))
        
        return errors
    
    def _validate_custom(self, df: pd.DataFrame, rule: ValidationRule) -> List[ValidationError]:
        """Apply custom validation logic"""
        errors = []
        
        if rule.rule_id == "required_fields":
            required_columns = rule.parameters.get("required_columns", [])
            for col in required_columns:
                if col in df.columns:
                    null_rows = df[col].isna()
                    for idx in df[null_rows].index:
                        errors.append(ValidationError(
                            row=idx + 1,
                            column=col,
                            value=None,
                            rule_id=rule.rule_id,
                            message=f"Required field is empty",
                            severity=rule.severity
                        ))
        
        return errors
    
    def _get_ai_suggestions(self, df: pd.DataFrame, errors: List[ValidationError]) -> List[str]:
        """Get AI-powered suggestions for corrections"""
        if not self.ai_client:
            return []
        
        suggestions = []
        
        try:
            # Prepare context for AI
            context = f"Data validation errors found in Excel file with {len(df)} rows and {len(df.columns)} columns."
            error_summary = "\n".join([
                f"Row {error.row}, Column {error.column}: {error.message} (Value: {error.value})"
                for error in errors[:5]  # Limit to first 5 errors
            ])
            
            prompt = f"""
            {context}
            
            Errors found:
            {error_summary}
            
            Please provide specific correction suggestions for each error. 
            Keep suggestions concise and actionable.
            """
            
            model = os.getenv("AZURE_OPENAI_MODEL", "gpt-4.1")
            
            response = self.ai_client.complete(
                messages=[
                    SystemMessage("You are a data validation expert. Provide specific, actionable suggestions for correcting data validation errors."),
                    UserMessage(prompt)
                ],
                temperature=0.3,
                model=model
            )
            
            if response.choices:
                suggestion_text = response.choices[0].message.content
                # Split suggestions by lines and clean up
                suggestions = [s.strip() for s in suggestion_text.split('\n') if s.strip()]
            
        except Exception as e:
            logger.error(f"Error getting AI suggestions: {str(e)}")
        
        return suggestions
