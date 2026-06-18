#!/bin/bash
# Quick fix untuk masalah 2 menit response time

echo "🚀 Quick Fix: Optimizing Chatbot Performance"
echo "=============================================="
echo ""

# 1. Check Ollama model
echo "1️⃣ Checking Ollama model..."
CURRENT_MODEL=$(grep "OLLAMA_MODEL" .env 2>/dev/null | cut -d'=' -f2)
echo "   Current model: $CURRENT_MODEL"

if [[ "$CURRENT_MODEL" == *"mistral"* ]] && [[ "$CURRENT_MODEL" != *"q4"* ]]; then
    echo "   ⚠️  WARNING: Using full-size model (slow!)"
    echo "   Recommendation: Use quantized model for 3-5x speedup"
    echo ""
    echo "   Run this to switch to faster model:"
    echo "   ollama pull mistral:7b-instruct-q4_0"
    echo "   Then update .env: OLLAMA_MODEL=mistral:7b-instruct-q4_0"
fi

echo ""

# 2. Add HNSW index
echo "2️⃣ Adding HNSW index for faster vector search..."
python scripts/add_vector_index.py
echo ""

# 3. Restart app
echo "3️⃣ Changes applied to LLM service:"
echo "   ✓ Timeout reduced: 25s → 10s (fail fast)"
echo "   ✓ Max tokens reduced: 200 → 100 (faster generation)"
echo "   ✓ Context window reduced: 1024 → 512 (less processing)"
echo "   ✓ Chunks reduced: 3 → 2 (less context to process)"
echo ""

echo "4️⃣ Next steps:"
echo "   1. Restart your FastAPI server"
echo "   2. Test with a query"
echo "   3. Run: python scripts/diagnose_performance.py"
echo ""

echo "✅ Quick fix applied!"
echo ""
echo "Expected improvements:"
echo "   - LLM timeout at 10s (no more 2-minute waits)"
echo "   - Faster generation with reduced tokens"
echo "   - Fallback response if LLM is too slow"
