import pytest
from src.utils.helpers import (
    validate_email_format,
    generate_file_hash,
    sanitize_filename,
    format_file_size,
    truncate_string,
)
from src.utils.pbi import build_pbi_deeplink

def test_validate_email_format():
    """Test email format validation"""
    valid_emails = [
        'test@example.com',
        'user.name@domain.co.uk',
        'test123@subdomain.example.org'
    ]
    
    invalid_emails = [
        'invalid-email',
        '@example.com',
        'test@',
        'test.example.com',
        ''
    ]
    
    for email in valid_emails:
        assert validate_email_format(email), f"Valid email failed: {email}"
    
    for email in invalid_emails:
        assert not validate_email_format(email), f"Invalid email passed: {email}"

def test_generate_file_hash():
    """Test file hash generation"""
    data1 = b"test data"
    data2 = b"test data"
    data3 = b"different data"
    
    hash1 = generate_file_hash(data1)
    hash2 = generate_file_hash(data2)
    hash3 = generate_file_hash(data3)
    
    # Same data should produce same hash
    assert hash1 == hash2
    
    # Different data should produce different hash
    assert hash1 != hash3

def test_sanitize_filename():
    """Test filename sanitization"""
    test_cases = [
        ('normal_file.xlsx', 'normal_file.xlsx'),
        ('file with spaces.xlsx', 'file_with_spaces.xlsx'),
        ('file@#$%^&*().xlsx', 'file_________.xlsx'),
        ('file-name_123.xlsx', 'file-name_123.xlsx')
    ]
    
    for original, expected in test_cases:
        result = sanitize_filename(original)
        assert result == expected, f"Failed for {original}: got {result}, expected {expected}"

def test_format_file_size():
    """Test file size formatting"""
    test_cases = [
        (0, "0 B"),
        (1024, "1.0 KB"),
        (1024 * 1024, "1.0 MB"),
        (1536, "1.5 KB"),
        (2048 * 1024 * 1024, "2.0 GB")
    ]
    
    for size_bytes, expected in test_cases:
        result = format_file_size(size_bytes)
        assert result == expected, f"Failed for {size_bytes}: got {result}, expected {expected}"

def test_truncate_string():
    """Test string truncation"""
    long_text = "This is a very long string that needs to be truncated"
    
    # Test truncation
    result = truncate_string(long_text, 20)
    assert len(result) <= 20
    assert result.endswith("...")
    
    # Test no truncation needed
    short_text = "Short"
    result = truncate_string(short_text, 20)
    assert result == short_text


def test_build_pbi_deeplink(monkeypatch):
    monkeypatch.setenv("PBI_WORKSPACE_ID", "ws")
    monkeypatch.setenv("PBI_REPORT_ID", "rep")
    url = build_pbi_deeplink({"vw_Variance/Carrier": "X", "vw_Variance/SKU": "812"})
    assert "groups/ws/reports/rep" in url
    assert "filter=" in url

if __name__ == "__main__":
    pytest.main([__file__])
