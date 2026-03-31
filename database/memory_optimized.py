# backend/database/memory_optimized.py
import os
import gc
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    
    # Memory-optimized engine for 512MB RAM
    engine = create_engine(
        DATABASE_URL,
        pool_size=1,              # Single connection to save memory
        max_overflow=2,           # Allow 2 extra connections during spikes
        pool_recycle=900,         # Recycle every 15 minutes
        pool_pre_ping=True,       # Check connections before use
        echo=False,               # No query logging
        connect_args={
            "connect_timeout": 5,
            "read_timeout": 10,
            "write_timeout": 10,
            "charset": "utf8mb4"
        }
    )
    
    SessionLocal = sessionmaker(bind=engine)
    
    @contextmanager
    def get_db_connection():
        """Context manager for database connections with automatic cleanup"""
        conn = None
        try:
            conn = engine.connect()
            yield conn
        finally:
            if conn:
                conn.close()
                gc.collect()  # Force garbage collection
    
    def query_optimized(sql: str, params: dict = None, fetch: str = "all"):
        """
        Memory-optimized query function
        fetch="all"  → list of dicts
        fetch="one"  → single dict or None
        fetch=None   → no return (INSERT/UPDATE/DELETE)
        """
        with get_db_connection() as conn:
            result = conn.execute(text(sql), params or {})
            conn.commit()
            
            if fetch == "one":
                row = result.fetchone()
                return dict(row._mapping) if row else None
            elif fetch == "all":
                rows = result.fetchall()
                # Convert to simple dicts to reduce memory
                return [dict(r._mapping) for r in rows]
            return None
    
    def cleanup_connections():
        """Force cleanup of database connections"""
        engine.dispose()
        gc.collect()
        
else:
    def query_optimized(sql: str, params: dict = None, fetch: str = "all"):
        raise RuntimeError("DATABASE_URL not configured")
    
    def cleanup_connections():
        pass
