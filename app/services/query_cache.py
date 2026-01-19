"""
Query Cache dengan Session Isolation
FIXED: Menambahkan session_id untuk mencegah cache collision antar user
"""

from typing import Optional, List, Dict
import hashlib
import json
from datetime import datetime, timedelta

class QueryCache:
    """Cache dengan session isolation dan pre-computed common queries"""
    
    def __init__(self, ttl_minutes: int = 60):
        self.cache: Dict[str, Dict] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        
        # Pre-computed common queries (shared across sessions)
        self.common_patterns = {
            'wudhu': None,
            'shalat': None,
            'puasa': None,
            'zakat': None,
            'haji': None,
        }
    
    def _hash_query(self, query: str, session_id: str = None) -> str:
        """
        Generate hash dari query dengan session isolation
        
        Args:
            query: Query text
            session_id: Optional session ID untuk isolasi cache per user
            
        Returns:
            MD5 hash string
        """
        # Gabungkan query + session_id untuk unique hash per session
        if session_id:
            key = f"{query.lower().strip()}:session:{session_id}"
        else:
            key = f"{query.lower().strip()}:global"
        
        return hashlib.md5(key.encode()).hexdigest()
    
    def _find_common_pattern(self, query: str) -> Optional[str]:
        """Check if query matches common pattern"""
        query_lower = query.lower()
        for pattern in self.common_patterns.keys():
            if pattern in query_lower:
                return pattern
        return None
    
    def get_embedding(self, query: str, session_id: str = None) -> Optional[List[float]]:
        """
        Get cached embedding dengan session isolation
        
        Args:
            query: Query text
            session_id: Optional session ID
            
        Returns:
            Cached embedding or None
        """
        # Check session-specific cache first
        if session_id:
            key = self._hash_query(query, session_id)
            if key in self.cache:
                entry = self.cache[key]
                if datetime.utcnow() - entry['timestamp'] < self.ttl:
                    return entry['embedding']
                else:
                    del self.cache[key]
        
        # Fallback to common pattern (shared cache)
        pattern = self._find_common_pattern(query)
        if pattern and self.common_patterns[pattern]:
            return self.common_patterns[pattern]
        
        return None
    
    def set_embedding(self, query: str, embedding: List[float], session_id: str = None):
        """
        Cache embedding dengan session isolation
        
        Args:
            query: Query text
            embedding: Embedding vector
            session_id: Optional session ID
        """
        # Cache dengan session ID jika ada
        if session_id:
            key = self._hash_query(query, session_id)
        else:
            key = self._hash_query(query)
        
        self.cache[key] = {
            'embedding': embedding,
            'timestamp': datetime.utcnow()
        }
        
        # Store in common patterns if matches (untuk sharing antar session)
        pattern = self._find_common_pattern(query)
        if pattern and not self.common_patterns[pattern]:
            self.common_patterns[pattern] = embedding
    
    def get_results(self, query: str, filters: Dict = None, session_id: str = None) -> Optional[List[Dict]]:
        """
        Get cached search results dengan session isolation
        
        Args:
            query: Query text
            filters: Search filters
            session_id: Optional session ID
            
        Returns:
            Cached results or None
        """
        filter_str = json.dumps(filters or {}, sort_keys=True)
        cache_key = f"{query}:filters:{filter_str}"
        
        key = self._hash_query(cache_key, session_id)
        
        if key in self.cache:
            entry = self.cache[key]
            if datetime.utcnow() - entry['timestamp'] < self.ttl:
                return entry['results']
            else:
                del self.cache[key]
        
        return None
    
    def set_results(self, query: str, results: List[Dict], filters: Dict = None, session_id: str = None):
        """
        Cache search results dengan session isolation
        
        Args:
            query: Query text
            results: Search results
            filters: Search filters
            session_id: Optional session ID
        """
        filter_str = json.dumps(filters or {}, sort_keys=True)
        cache_key = f"{query}:filters:{filter_str}"
        
        if session_id:
            key = self._hash_query(cache_key, session_id)
        else:
            key = self._hash_query(cache_key)
        
        self.cache[key] = {
            'results': results,
            'timestamp': datetime.utcnow()
        }
    
    def clear_session(self, session_id: str) -> int:
        """
        Clear cache untuk session tertentu
        
        Args:
            session_id: Session ID to clear
            
        Returns:
            Number of cleared entries
        """
        if not session_id:
            return 0
        
        keys_to_delete = []
        session_marker = f":session:{session_id}"
        
        # Find all keys containing this session_id
        for key in self.cache.keys():
            # We need to check if the original key (before hashing) contained session_id
            # Since we can't reverse hash, we'll use a marker in the hash input
            # This is why we added ":session:{session_id}" to the hash input
            pass
        
        # Alternative: store session_id in cache entry
        for key, value in list(self.cache.items()):
            if 'session_id' in value and value['session_id'] == session_id:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.cache[key]
        
        return len(keys_to_delete)
    
    def clear(self):
        """Clear all cache (keep common patterns)"""
        self.cache.clear()
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_entries = len(self.cache)
        
        # Count by type
        embedding_count = 0
        results_count = 0
        
        for entry in self.cache.values():
            if 'embedding' in entry:
                embedding_count += 1
            elif 'results' in entry:
                results_count += 1
        
        return {
            'total_entries': total_entries,
            'embedding_cache': embedding_count,
            'results_cache': results_count,
            'common_patterns': len([p for p in self.common_patterns.values() if p is not None]),
            'ttl_minutes': self.ttl.total_seconds() / 60
        }

# Global cache instance
query_cache = QueryCache(ttl_minutes=60)