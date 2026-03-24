"""Milvus vector search helpers shared by RAG examples.

Lives under ``examples/ray/common/`` (import as ``common.milvus_search`` once
``examples/ray`` is on ``sys.path``).

``data/rag/rag_query.py`` and ``data/rag/rag_ingestion.ipynb`` validation use this
module so search params and embedding truncation stay aligned with
``data/rag/docling_milvus_process.py`` ingestion.

The ingestion RayJob typically zips only ``data/rag/``; that script does **not**
import this module so the cluster job stays self-contained.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from pymilvus import MilvusClient

# Defaults aligned with docling_milvus_process.py
_DEFAULT_MILVUS_HOST = "milvus-milvus.milvus.svc.cluster.local"
_DEFAULT_MILVUS_PORT = 19530
_DEFAULT_MILVUS_DB = "default"
_DEFAULT_COLLECTION = "rag_documents"
_DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_DEFAULT_CHUNK_MAX_TOKENS = 128
# BERT-style models: position limit 512; ingestion uses min(EMBED_MAX_SEQ_LENGTH, 512).
_DEFAULT_EMBED_MAX_SEQ_CAP = 512


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def milvus_http_uri(
    *,
    host: Optional[str] = None,
    port: Optional[Union[int, str]] = None,
) -> str:
    """Build ``http://host:port`` for MilvusClient from env or overrides."""
    h = (
        host
        if host is not None
        else os.environ.get("MILVUS_HOST", _DEFAULT_MILVUS_HOST)
    )
    if port is not None:
        p = int(port)
    else:
        p = _env_int("MILVUS_PORT", _DEFAULT_MILVUS_PORT)
    return f"http://{h}:{p}"


def create_milvus_client(
    *,
    host: Optional[str] = None,
    port: Optional[Union[int, str]] = None,
    db_name: Optional[str] = None,
) -> MilvusClient:
    """Create a Milvus client; kwargs override ``MILVUS_*`` environment variables."""
    from pymilvus import MilvusClient

    uri = milvus_http_uri(host=host, port=port)
    db = (
        db_name
        if db_name is not None
        else os.environ.get("MILVUS_DB", _DEFAULT_MILVUS_DB)
    )
    return MilvusClient(uri=uri, db_name=db)


def _embedding_max_seq_length() -> int:
    """Match docling_milvus_process._create_embedding_fn truncation logic."""
    chunk_default = _env_int("CHUNK_MAX_TOKENS", _DEFAULT_CHUNK_MAX_TOKENS)
    raw = os.environ.get("EMBED_MAX_SEQ_LENGTH")
    if raw is None or raw == "":
        seq = chunk_default
    else:
        seq = int(raw)
    return max(1, min(seq, _DEFAULT_EMBED_MAX_SEQ_CAP))


def load_query_embedding_model(
    model_name: Optional[str] = None,
) -> Any:
    """Load SentenceTransformer with ``max_seq_length`` aligned to ingestion.

    If query and ingest truncate differently, retrieval quality drops even when
    the model id matches.
    """
    from sentence_transformers import SentenceTransformer

    name = model_name or os.environ.get("EMBEDDING_MODEL", _DEFAULT_EMBEDDING_MODEL)
    model = SentenceTransformer(name)
    model.max_seq_length = _embedding_max_seq_length()
    return model


def search_rag_collection(
    query: str,
    *,
    client: MilvusClient,
    embed_model: Any,
    collection_name: Optional[str] = None,
    top_k: Optional[int] = None,
    nprobe: int = 16,
    load_collection: bool = True,
) -> List[Dict[str, Any]]:
    """Embed ``query`` and search Milvus; return context dicts like rag_query used to.

    Each item has keys: ``text``, ``source_file``, ``chunk_index``, ``score``
    (distance from Milvus; lower is more similar for COSINE in many versions).
    """
    coll = (
        collection_name
        if collection_name is not None
        else os.environ.get("MILVUS_COLLECTION", _DEFAULT_COLLECTION)
    )
    k = top_k if top_k is not None else _env_int("TOP_K", 5)

    if load_collection:
        client.load_collection(coll)

    query_embedding = embed_model.encode([query], normalize_embeddings=True).tolist()

    results = client.search(
        collection_name=coll,
        data=query_embedding,
        limit=k,
        output_fields=["source_file", "chunk_index", "text"],
        search_params={"metric_type": "COSINE", "params": {"nprobe": nprobe}},
    )

    contexts: List[Dict[str, Any]] = []
    for hits in results:
        for hit in hits:
            ent = hit["entity"]
            contexts.append({
                "text": ent["text"],
                "source_file": ent["source_file"],
                "chunk_index": ent["chunk_index"],
                "score": hit["distance"],
            })
    return contexts
