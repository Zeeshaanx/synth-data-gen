"""
PostgreSQL persistence layer — completely optional.
If DATABASE_URL is not set or DB is unreachable, every function silently
no-ops and the app continues working on in-memory JOB_STORE as before.
"""
import os, json, logging, asyncio
from typing import Optional, List, Dict, Any

log = logging.getLogger(__name__)

try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False

DATABASE_URL: Optional[str] = os.environ.get("DATABASE_URL")
_pool = None

async def init_pool():
    global _pool
    if not HAS_ASYNCPG or not DATABASE_URL:
        log.warning("PostgreSQL disabled (no DATABASE_URL or asyncpg missing)")
        return
    try:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10, command_timeout=30)
        async with _pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id            BIGSERIAL PRIMARY KEY,
                    job_id        TEXT NOT NULL UNIQUE,
                    job_type      TEXT NOT NULL DEFAULT 'create',
                    status        TEXT NOT NULL DEFAULT 'processing',
                    model_provider TEXT,
                    model_id      TEXT,
                    num_records   INTEGER,
                    result        JSONB,
                    error_message TEXT,
                    csv_filename  TEXT,
                    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
            """)
        log.info("PostgreSQL ready")
    except Exception as e:
        log.error(f"PostgreSQL unavailable (non-fatal): {e}")
        _pool = None

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

def _fire(coro):
    """Fire-and-forget — never raises, never blocks."""
    async def _run():
        try: await coro
        except Exception as e: log.error(f"DB write failed (non-fatal): {e}")
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running(): asyncio.ensure_future(_run())
    except Exception: pass

def insert_job(job_id, job_type, model_provider, model_id, num_records):
    if not _pool: return
    _fire(_insert(job_id, job_type, model_provider, model_id, num_records))

async def _insert(job_id, job_type, model_provider, model_id, num_records):
    async with _pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO jobs(job_id,job_type,model_provider,model_id,num_records) "
            "VALUES($1,$2,$3,$4,$5) ON CONFLICT(job_id) DO NOTHING",
            job_id, job_type, model_provider, model_id, num_records)

def update_completed(job_id, result, csv_filename):
    if not _pool: return
    _fire(_update_done(job_id, 'completed', result, None, csv_filename))

def update_failed(job_id, error):
    if not _pool: return
    _fire(_update_done(job_id, 'failed', None, error, None))

async def _update_done(job_id, status, result, error, csv_filename):
    async with _pool.acquire() as conn:
        await conn.execute(
            "UPDATE jobs SET status=$2,result=$3::jsonb,error_message=$4,csv_filename=$5,updated_at=NOW() WHERE job_id=$1",
            job_id, status, json.dumps(result) if result else None, error, csv_filename)

async def list_jobs(limit=200) -> List[Dict[str, Any]]:
    if not _pool: return []
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT job_id,job_type,status,model_provider,model_id,num_records,"
            "csv_filename,error_message,created_at,updated_at FROM jobs ORDER BY created_at DESC LIMIT $1", limit)
    return [dict(r) for r in rows]
