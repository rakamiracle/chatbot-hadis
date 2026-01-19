"""
Clear Cache Script
Usage: python scripts/clear_cache.py [--session SESSION_ID]
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.query_cache import query_cache

def main():
    parser = argparse.ArgumentParser(description='Clear query cache')
    parser.add_argument('--session', type=str, help='Clear cache for specific session ID')
    parser.add_argument('--all', action='store_true', help='Clear all cache')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🗑️  CACHE CLEANER")
    print("=" * 70)
    
    if args.all:
        print("\n⚠️  Clearing ALL cache...")
        query_cache.clear()
        print("✅ All cache cleared!")
    
    elif args.session:
        print(f"\n🔍 Clearing cache for session: {args.session[:8]}...")
        cleared = query_cache.clear_session(args.session)
        print(f"✅ Cleared {cleared} entries for session {args.session[:8]}...")
    
    else:
        print("\n❌ No action specified!")
        print("Usage:")
        print("  python scripts/clear_cache.py --all           # Clear all cache")
        print("  python scripts/clear_cache.py --session UUID  # Clear specific session")
        return
    
    # Show stats after clearing
    stats = query_cache.get_stats()
    print(f"\n📊 Cache Stats After Clear:")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Embedding cache: {stats['embedding_cache']}")
    print(f"  Results cache: {stats['results_cache']}")
    
    print(f"\n{'=' * 70}")
    print("✅ Done!")
    print(f"{'=' * 70}\n")

if __name__ == "__main__":
    main()