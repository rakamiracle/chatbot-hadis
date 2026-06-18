#!/bin/bash

echo "=== Running Chatbot Hadis Tests ==="

# Unit tests
echo -e "\n📦 Unit Tests..."
pytest tests/test_pdf_processor.py -v
pytest tests/test_chunker.py -v
pytest tests/test_embedding_service.py -v
pytest tests/test_text_cleaner.py -v

# Integration tests
echo -e "\n🔗 Integration Tests..."
pytest tests/test_integration_upload.py -v
pytest tests/test_integration_chat.py -v

# Evaluation
echo -e "\n📊 Evaluation Tests..."
pytest tests/test_evaluation.py -v

# A/B Testing
echo -e "\n🔬 A/B Tests..."
pytest tests/test_ab_testing.py -v

# Performance
echo -e "\n⚡ Performance Tests..."
pytest tests/test_performance.py -v

echo -e "\n✅ All tests completed!"
