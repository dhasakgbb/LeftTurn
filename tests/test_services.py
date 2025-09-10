import pytest
import pandas as pd
from src.services.excel_service import ExcelService
from src.services.validation_service import ValidationService
from src.models.validation_models import ValidationRule

@pytest.fixture
def excel_service():
    return ExcelService()

@pytest.fixture
def validation_service():
    return ValidationService()

@pytest.fixture
def sample_excel_data():
    """Create sample Excel data for testing"""
    data = {
        'name': ['John Doe', 'Jane Smith', 'Bob Johnson'],
        'email': ['john@example.com', 'invalid-email', 'bob@example.com'],
        'age': [30, 25, 35],
        'score': [85, 95, 75]
    }
    return pd.DataFrame(data)

def test_excel_service_clean_dataframe(excel_service, sample_excel_data):
    """Test DataFrame cleaning functionality"""
    # Add some messy data
    messy_data = sample_excel_data.copy()
    messy_data.loc[3] = [None, None, None, None]  # Empty row
    messy_data['name'] = messy_data['name'].astype(str) + '  '  # Add whitespace
    
    cleaned_df = excel_service._clean_dataframe(messy_data)
    
    # Check that empty row was removed
    assert len(cleaned_df) == 3
    
    # Check that whitespace was stripped
    assert not any(name.endswith('  ') for name in cleaned_df['name'])

def test_validation_service_email_validation(validation_service, sample_excel_data):
    """Test email validation"""
    result = validation_service.validate_data(sample_excel_data, "test_file")
    
    # Should find one invalid email
    email_errors = [error for error in result.errors if 'email' in error.column.lower()]
    assert len(email_errors) > 0

def test_validation_rule_creation():
    """Test ValidationRule model"""
    rule = ValidationRule(
        rule_id="test_rule",
        rule_name="Test Rule",
        description="Test description",
        rule_type="format",
        parameters={"pattern": r"^test$"},
        severity="error"
    )
    
    assert rule.rule_id == "test_rule"
    assert rule.severity == "error"

def test_excel_service_email_extraction(excel_service, sample_excel_data):
    """Test email extraction from DataFrame"""
    emails = excel_service.extract_email_column(sample_excel_data, "email")
    
    # Should extract valid emails only
    valid_emails = ['john@example.com', 'bob@example.com']
    for email in valid_emails:
        assert email in emails
    
    # Invalid email should not be included
    assert 'invalid-email' not in emails

if __name__ == "__main__":
    pytest.main([__file__])