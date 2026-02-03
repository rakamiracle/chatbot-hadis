#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import asyncio
import inspect
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, List, Optional, Sequence, Tuple

import psycopg2


# =========================
# Helpers
# =========================

def chunked(items: Sequence[Any], size: int) -> Iterable[List[Any]]:
    if size <= 0:
        raise ValueError("batch_size harus > 0")
    for i in range(0, len(items), size):
        yield list(items[i : i + size])


def confirm(prompt: str) -> bool:
    while True:
        ans = input(prompt).strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Jawab 'yes' atau 'no'.")


# =========================
# Embedding method discovery
# =========================

CANDIDATE_METHODS = (
    "generate_embeddings_batch",
    "generate_embedding",
    "generate_embeddings",
    "embed",
    "encode",
    "create_embeddings",
)


def _find_embedding_callable(svc: Any) -> Tuple[str, Callable[..., Any]]:
    for name in CANDIDATE_METHODS:
        fn = getattr(svc, name, None)
        if callable(fn):
            return name, fn
    available = [m for m in dir(svc) if not m.startswith("_")]
    raise AttributeError(
        "Tidak menemukan method embedding di EmbeddingService. "
        f"Coba tambahkan salah satu: {', '.join(CANDIDATE_METHODS)}. "
        f"Method yang ada: {available}"
    )


def _to_list_of_list(x: Any) -> List[List[float]]:
    if x is None:
        raise ValueError("Embedding output None")

    if isinstance(x, list):
        if len(x) == 0:
            return []
        if isinstance(x[0], list):
            return x  # type: ignore[return-value]
        if isinstance(x[0], (int, float)):
            return [x]  # type: ignore[return-value]

    tolist = getattr(x, "tolist", None)
    if callable(tolist):
        out = tolist()
        if isinstance(out, list) and out and isinstance(out[0], (int, float)):
            return [out]
        return out

    detach = getattr(x, "detach", None)
    if callable(detach):
        y = x.detach()
        cpu = getattr(y, "cpu", None)
        if callable(cpu):
            y = y.cpu()
        tolist2 = getattr(y, "tolist", None)
        if callable(tolist2):
            out = tolist2()
            if isinstance(out, list) and out and isinstance(out[0], (int, float)):
                return [out]
            return out

    raise TypeError(f"Tidak bisa mengkonversi embedding output type={type(x)} jadi list[list[float]].")


def generate_embeddings_safe(svc: Any, texts: List[str]) -> List[List[float]]:
    method_name, fn = _find_embedding_callable(svc)

    tried_errors: List[str] = []
    candidates: List[Tuple[str, Callable[[], Any]]] = [
        (f"{method_name}(texts)", lambda: fn(texts)),
        (f"{method_name}(texts=texts)", lambda: fn(texts=texts)),
        (f"{method_name}(input=texts)", lambda: fn(input=texts)),
        # common batch signature variants:
        (f"{method_name}(texts, batch_size=len(texts))", lambda: fn(texts, batch_size=len(texts))),
    ]

    last_exc: Optional[BaseException] = None
    for sig, call in candidates:
        try:
            out = call()
            if inspect.isawaitable(out):
                out = asyncio.run(out)
            return _to_list_of_list(out)
        except TypeError as e:
            last_exc = e
            tried_errors.append(f"{sig} -> {e}")

    raise TypeError(
        "Gagal memanggil method embedding dengan signature yang dicoba:\n"
        + "\n".join(tried_errors)
        + (f"\nLast error: {last_exc}" if last_exc else "")
    )


# =========================
# Postgres (hadis_chunks.embedding vector(512))
# =========================

@dataclass
class ChunkRow:
    chunk_id: int
    text: str


def _get_db_conn():
    """
    Set env var DATABASE_URL, contoh:
    export DATABASE_URL="postgresql://user:pass@localhost:5432/chatbot_hadis"
    """
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL belum diset. Contoh: export DATABASE_URL='postgresql://user:pass@host:5432/db'")
    return psycopg2.connect(dsn)


def fetch_chunks_for_doc_ids(doc_ids: List[int]) -> List[ChunkRow]:
    with _get_db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, chunk_text
            FROM public.hadis_chunks
            WHERE document_id = ANY(%s)
            ORDER BY document_id, chunk_index, id
            """,
            (doc_ids,),
        )
        rows = cur.fetchall()
        return [ChunkRow(chunk_id=r[0], text=r[1]) for r in rows]


def _vector_literal(vec: List[float]) -> str:
    # pgvector literal: '[0.1, 0.2, ...]'
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


def update_embeddings(chunk_ids: List[int], embeddings: List[List[float]]) -> None:
    if len(chunk_ids) != len(embeddings):
        raise ValueError("chunk_ids dan embeddings harus sama panjang")

    data = [( _vector_literal(e), cid) for cid, e in zip(chunk_ids, embeddings)]

    with _get_db_conn() as conn, conn.cursor() as cur:
        cur.executemany(
            """
            UPDATE public.hadis_chunks
            SET embedding = %s::vector
            WHERE id = %s
            """,
            data,
        )
        conn.commit()


# =========================
# Main
# =========================

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Simple Embeddings Regeneration (hadis_chunks)")
    p.add_argument("--doc-ids", required=True, help="Comma-separated doc IDs, contoh: 8,16,17")
    p.add_argument("--batch-size", type=int, default=32, help="Batch size (default: 32)")
    p.add_argument("--dry-run", action="store_true", help="Tidak menulis ke DB")
    p.add_argument("--no-confirm", action="store_true", help="Lewati prompt konfirmasi")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    doc_ids = [int(x.strip()) for x in args.doc_ids.split(",") if x.strip()]

    print("🔄 SIMPLE EMBEDDINGS REGENERATION")
    print("=" * 60)
    print(f"📋 Processing documents: {doc_ids}")

    try:
        from app.services.embedding_service import EmbeddingService  # type: ignore
    except Exception as e:
        print("❌ Gagal import EmbeddingService (app.services.embedding_service).")
        print(f"   Error: {e}")
        return 2

    try:
        svc = EmbeddingService()
        method_name, _ = _find_embedding_callable(svc)
        print(f"✅ EmbeddingService loaded (method terdeteksi: {method_name})")
    except Exception as e:
        print(f"❌ EmbeddingService tidak valid: {e}")
        return 2

    try:
        chunks = fetch_chunks_for_doc_ids(doc_ids)
    except Exception as e:
        print(f"❌ Gagal fetch chunks dari DB: {e}")
        return 2

    total = len(chunks)
    print(f"📊 Total chunks to process: {total}")
    if total == 0:
        print("✅ Tidak ada chunk. Selesai.")
        return 0

    if not args.no_confirm:
        if not confirm(f"\n❓ Regenerate embeddings for {total:,} chunks? (yes/no): "):
            print("❎ Dibatalkan.")
            return 0

    processed = 0
    failed = 0
    t0 = time.time()

    print("\n🔧 Processing...")
    for batch_idx, batch in enumerate(chunked(chunks, args.batch_size), start=1):
        texts = [c.text for c in batch]
        ids = [c.chunk_id for c in batch]
        try:
            embs = generate_embeddings_safe(svc, texts)
            if len(embs) != len(texts):
                raise ValueError(f"Jumlah embedding ({len(embs)}) != jumlah teks ({len(texts)})")

            if not args.dry_run:
                update_embeddings(ids, embs)

            processed += len(batch)
            if batch_idx == 1 and embs:
                print(f"   Batch {batch_idx}: {len(batch)} chunks ✅ (dim={len(embs[0])})")
            else:
                print(f"   Batch {batch_idx}: {len(batch)} chunks ✅")
        except Exception as e:
            failed += len(batch)
            print(f"   ❌ Batch {batch_idx} error: {e}")

    dt = time.time() - t0
    print("\n✅ Complete!")
    print(f"📊 Processed: {processed}")
    print(f"❌ Failed: {failed}")
    print(f"⏱️  Time: {dt:.1f}s")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
