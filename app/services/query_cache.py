from typing import Optional, List, Dict
import hashlib
import json
from datetime import datetime, timedelta

class QueryCache:
    """Cache untuk query embeddings dan results"""
    
    def __init__(self, ttl_minutes: int = 60):
        self.cache: Dict[str, Dict] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _hash_query(self, query: str) -> str:
        """Generate hash dari query"""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def get_embedding(self, query: str) -> Optional[List[float]]:
        """Get cached embedding"""
        key = self._hash_query(query)
        if key in self.cache:
            entry = self.cache[key]
            if datetime.utcnow() - entry['timestamp'] < self.ttl:
                return entry['embedding']
            else:
                del self.cache[key]
        return None
    
    def set_embedding(self, query: str, embedding: List[float]):
        """Cache embedding"""
        key = self._hash_query(query)
        self.cache[key] = {
            'embedding': embedding,
            'timestamp': datetime.utcnow()
        }
    
    def get_results(self, query: str, filters: Dict = None) -> Optional[List[Dict]]:
        """Get cached search results"""
        key = self._hash_query(query + json.dumps(filters or {}, sort_keys=True))
        if key in self.cache:
            entry = self.cache[key]
            if datetime.utcnow() - entry['timestamp'] < self.ttl:
                return entry['results']
            else:
                del self.cache[key]
        return None
    
    def set_results(self, query: str, results: List[Dict], filters: Dict = None):
        """Cache search results"""
        key = self._hash_query(query + json.dumps(filters or {}, sort_keys=True))
        self.cache[key] = {
            'results': results,
            'timestamp': datetime.utcnow()
        }
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()

# Global cache instance
query_cache = QueryCache(ttl_minutes=30)