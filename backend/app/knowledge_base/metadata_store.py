"""Metadata Store — Postgres/SQLite with in-memory fallback."""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_FALLBACK: dict[str, dict] = {}  # chunk_id -> metadata dict

def _pg_conn():
    try:
        import psycopg2  # type: ignore
        from app.config import settings
        if settings.mock_llm:
            raise RuntimeError("mock uses fallback")
        conn = psycopg2.connect(settings.postgres_url)  # type: ignore
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS kb_metadata (
                    chunk_id TEXT PRIMARY KEY,
                    source_document TEXT, section TEXT, subsection TEXT, clause TEXT, entity TEXT, obligation_type TEXT, legal_principle TEXT, citation TEXT, page INT, text TEXT
                )
            """)
            conn.commit()
        return conn
    except Exception as e:
        logger.debug("postgres fallback %s", e)
        return None

def upsert(metadatas: List[Dict[str, Any]], texts: List[str]):
    conn = _pg_conn()
    if conn is None:
        for m, t in zip(metadatas, texts):
            _FALLBACK[m["chunk_id"]] = {**m, "text": t}
        logger.info("metadata upsert fallback n=%d", len(metadatas))
        return
    try:
        with conn.cursor() as cur:
            for m, t in zip(metadatas, texts):
                cur.execute("""
                    INSERT INTO kb_metadata (chunk_id, source_document, section, subsection, clause, entity, obligation_type, legal_principle, citation, page, text)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (chunk_id) DO UPDATE SET source_document=EXCLUDED.source_document, section=EXCLUDED.section, clause=EXCLUDED.clause
                """, (m["chunk_id"], m["source_document"], m.get("section"), m.get("subsection"), m.get("clause"), m.get("entity"), m.get("obligation_type"), m.get("legal_principle"), m.get("citation"), m.get("page"), t))
            conn.commit()
        logger.info("metadata upsert postgres n=%d", len(metadatas))
    except Exception as e:
        logger.warning("metadata upsert fallback %s", e)
        for m, t in zip(metadatas, texts):
            _FALLBACK[m["chunk_id"]] = {**m, "text": t}
    finally:
        try: conn.close()
        except Exception: pass

def filter(where: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Simple equality filter
    conn = _pg_conn()
    if conn is None:
        out=[]
        for rec in _FALLBACK.values():
            if all(rec.get(k) == v for k,v in where.items()):
                out.append(rec)
        return out
    try:
        with conn.cursor() as cur:
            # Build WHERE
            clauses = " AND ".join(f"{k}=%s" for k in where.keys())
            q = f"SELECT * FROM kb_metadata WHERE {clauses}" if where else "SELECT * FROM kb_metadata"
            cur.execute(q, tuple(where.values()))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as e:
        logger.warning("metadata filter fallback %s", e)
        return [r for r in _FALLBACK.values() if all(r.get(k)==v for k,v in where.items())]
    finally:
        try: conn.close()
        except Exception: pass

def get(chunk_id: str) -> Dict[str, Any] | None:
    return _FALLBACK.get(chunk_id)

def reset_for_tests():
    _FALLBACK.clear()
