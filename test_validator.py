"""
Test script untuk Query Validator
Jalankan: python test_validator.py
"""

from app.services.query_validator import query_validator

def test_validator():
    print("=" * 60)
    print("🧪 Testing Query Validator")
    print("=" * 60)
    
    test_cases = [
        # Test Case 1: Critical - Hukum
        {
            "query": "Apa hukum pacaran dalam Islam?",
            "expected_severity": "critical"
        },
        # Test Case 2: High - Nikah
        {
            "query": "Syarat nikah menurut hadis",
            "expected_severity": "high"
        },
        # Test Case 3: Medium - Boleh
        {
            "query": "Apakah boleh mendengarkan musik?",
            "expected_severity": "medium"
        },
        # Test Case 4: Medical
        {
            "query": "Pengobatan dengan madu untuk sakit lambung",
            "expected_severity": None  # Will have medical disclaimer
        },
        # Test Case 5: Normal - No sensitivity
        {
            "query": "Hadis tentang kebersihan",
            "expected_severity": None
        },
        # Test Case 6: Invalid - Too short
        {
            "query": "ab",
            "expected_severity": None
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'─' * 60}")
        print(f"Test #{i}: {test['query']}")
        print(f"{'─' * 60}")
        
        result = query_validator.validate_query(test['query'])
        
        print(f"✓ Valid: {result['is_valid']}")
        print(f"✓ Sensitive: {result['is_sensitive']}")
        print(f"✓ Severity: {result['severity']}")
        print(f"✓ Topics detected: {result['topics_detected']}")
        
        if result.get('error'):
            print(f"❌ Error: {result['error']}")
        
        if result['disclaimer']:
            print(f"\n📋 Disclaimer:")
            print(result['disclaimer'])
        
        # Validate expectation
        if test['expected_severity']:
            if result['severity'] == test['expected_severity']:
                print(f"\n✅ PASSED - Severity matches expected: {test['expected_severity']}")
            else:
                print(f"\n❌ FAILED - Expected {test['expected_severity']}, got {result['severity']}")
        elif not result['is_sensitive']:
            print(f"\n✅ PASSED - No sensitivity detected as expected")
        else:
            print(f"\n⚠️  Sensitivity detected but not expected")
    
    # Print statistics
    print(f"\n{'=' * 60}")
    print("📊 Validation Statistics")
    print(f"{'=' * 60}")
    stats = query_validator.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print(f"\n{'=' * 60}")
    print("✅ Testing Complete!")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    test_validator()
