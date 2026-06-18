import pytest
from app.services.text_cleaner import HadisTextCleaner

@pytest.fixture
def cleaner():
    return HadisTextCleaner()

def test_clean_basic_text(cleaner):
    """Test basic text cleaning"""
    text = "  Ini   adalah    hadis  \n\n\n dengan   spasi   berlebih  "
    
    cleaned = cleaner.clean(text)
    
    assert cleaned == "Ini adalah hadis dengan spasi berlebih"

def test_clean_arabic_diacritics(cleaner):
    """Test remove Arabic harakat"""
    text = "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
    
    cleaned = cleaner.clean(text, preserve_arabic=True)
    
    # Should remove diacritics
    assert len(cleaned) < len(text)
    assert 'بسم' in cleaned  # Base letters preserved

def test_normalize_hadis_numbering(cleaner):
    """Test normalisasi nomor hadis"""
    text = "HR. Bukhari No: 123"
    
    normalized = cleaner.normalize_hadis_numbering(text)
    
    assert "Hadis 123" in normalized
