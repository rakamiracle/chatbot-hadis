"""
Debug Cache Script
Usage: python scripts/debug_cache.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.query_cache import query_cache

def debug_cache():
    print("=" * 70)
    print("🔍 CACHE DEBUG TOOL")
    print("=" * 70)
    
    stats = query_cache.get_stats()
    
    print(f"\n📊 Cache Statistics:")
    print(f"{'─' * 70}")
    for key, value in stats.items():
        print(f"  {key:.<50} {value}")
    
    print(f"\n📋 Cache Entries (First 20):")
    print(f"{'─' * 70}")
    
    if len(query_cache.cache) == 0:
        print("  (No cache entries)")
    else:
        for i, (key, value) in enumerate(list(query_cache.cache.items())[:20], 1):
            print(f"\n  [{i}] Key: {key[:60]}...")
            print(f"      Timestamp: {value['timestamp']}")
            
            if 'embedding' in value:
                emb_len = len(value['embedding'])
                print(f"      Type: Embedding ({emb_len} dimensions)")
            elif 'results' in value:
                results_count = len(value['results'])
                print(f"      Type: Results ({results_count} chunks)")
            
            if 'session_id' in value:
                print(f"      Session: {value['session_id'][:8]}...")
    
    print(f"\n🎯 Common Patterns:")
    print(f"{'─' * 70}")
    for pattern, embedding in query_cache.common_patterns.items():
        status = "✅ Cached" if embedding else "❌ Not cached"
        print(f"  {pattern:.<20} {status}")
    
    print(f"\n{'=' * 70}")
    print("✅ Debug Complete")
    print(f"{'=' * 70}\n")

if __name__ == "__main__":
    debug_cache()