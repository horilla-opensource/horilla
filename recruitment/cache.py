"""
recruitment/cache.py
"""

import time
from threading import Lock


class ThreadSafeCache:
    def __init__(self):
        self.cache = {}
        self.lock = Lock()

    def set(self, session_key, data, timeout=None):
        expire_at = time.time() + timeout if timeout else None
        with self.lock:
            self.cache[session_key] = (data, expire_at)

    def get(self, session_key):
        with self.lock:
            if session_key in self.cache:
                data, expire_at = self.cache[session_key]
                if expire_at is None or expire_at > time.time():
                    return data
                else:
                    del self.cache[session_key]
            return None

    def delete(self, session_key):
        with self.lock:
            if session_key in self.cache:
                del self.cache[session_key]


# Instantiate the thread-safe cache
thread_safe_cache = ThreadSafeCache()
