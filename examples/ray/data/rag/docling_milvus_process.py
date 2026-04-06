"""RAG ingestion pipeline: parse PDFs, chunk, embed, insert into Milvus.

3-stage Ray Data pipeline submitted as a RayJob to an existing RayCluster:
  Stage 1: DoclingChunkActor              -- parse PDFs + chunk (CPU, parallel)
  Stage 2: SentenceTransformersEmbeddingActor -- embed with sentence-transformers (CPU, parallel)
  Stage 3: MilvusWriteActor               -- insert vectors into Milvus (I/O, parallel)

Execution model (important for dashboards):
  Ray Data runs these operators in *dependency order*. Downstream stages can start
  as soon as upstream blocks exist (pipelining), but Docling is usually the long
  pole: you will see mostly Docling work until most PDFs are chunked, then a burst
  of embedding, then Milvus inserts. If NUM_EMBED_ACTORS is 1, embedding is
  effectively serial and looks like "parsing only" for almost the whole run.

All configuration is read from environment variables set by the notebook.
"""

import io
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import logfire
import ray

# Configure logfire for the driver process
logfire.configure(
    service_name="rag-driver",
    send_to_logfire=True,
)

# ---------------------------------------------------------------------------
# Parameters (all from environment variables)
# ---------------------------------------------------------------------------

NUM_ACTORS = int(os.environ.get("NUM_ACTORS", "6"))
NUM_EMBED_ACTORS = int(os.environ.get("NUM_EMBED_ACTORS", "4"))
NUM_MILVUS_ACTORS = int(os.environ.get("NUM_MILVUS_ACTORS", "2"))
CPUS_PER_ACTOR = int(os.environ.get("CPUS_PER_ACTOR", "4"))

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "1"))
EMBED_MAP_BATCH_SIZE = int(os.environ.get("EMBED_MAP_BATCH_SIZE", "32"))

PVC_MOUNT_PATH = os.environ.get("PVC_MOUNT_PATH", "/mnt/data")
INPUT_PATH = os.environ.get("INPUT_PATH", "input/pdfs")
NUM_FILES = int(os.environ.get("NUM_FILES", "150"))

MILVUS_HOST = os.environ.get("MILVUS_HOST", "milvus-milvus.milvus.svc.cluster.local")
MILVUS_PORT = int(os.environ.get("MILVUS_PORT", "19530"))
MILVUS_DB = os.environ.get("MILVUS_DB", "default")
COLLECTION_NAME = os.environ.get("MILVUS_COLLECTION", "rag_documents")
MILVUS_BATCH_SIZE = int(os.environ.get("MILVUS_BATCH_SIZE", "64"))
MILVUS_TEXT_MAX_CHARS = int(os.environ.get("MILVUS_TEXT_MAX_CHARS", "8192"))

EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "384"))

CHUNK_MAX_TOKENS = int(os.environ.get("CHUNK_MAX_TOKENS", "128"))

REPARTITION_FACTOR = int(os.environ.get("REPARTITION_FACTOR", "10"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_pdf_paths(input_path: str, limit: int) -> List[str]:
    """Collect PDF paths up to limit (0 = no limit)."""
    root = Path(input_path)
    if not root.is_dir():
        return []
    out = []
    for p in root.rglob("*.pdf"):
        if p.is_file():
            out.append(str(p))
            if limit > 0 and len(out) >= limit:
                break
    return out


def _configure_ray_context():
    """Configure Ray Data context for throughput and progress display."""
    ctx = ray.data.DataContext.get_current()
    ctx.max_errored_blocks = 50
    if hasattr(ctx, "target_max_block_size"):
        ctx.target_max_block_size = 2 * 1024 * 1024
    if hasattr(ctx, "enable_rich_progress_bars"):
        ctx.enable_rich_progress_bars = True
    if hasattr(ctx, "use_ray_tqdm"):
        ctx.use_ray_tqdm = False


# ---------------------------------------------------------------------------
# Stage 1: Parse PDFs and chunk
# ---------------------------------------------------------------------------


class DoclingChunkActor:
    """Parse PDFs with Docling and chunk with HybridChunker."""

    def __init__(self):
        import socket

        # Configure logfire in the worker process with distinct service name
        logfire.configure(
            service_name="rag-docling",
            send_to_logfire=True,
        )

        from docling.chunking import HybridChunker
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            AcceleratorOptions,
            PdfPipelineOptions,
        )
        from docling.document_converter import DocumentConverter, PdfFormatOption

        os.environ["OMP_NUM_THREADS"] = str(CPUS_PER_ACTOR)
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

        self.hostname = socket.gethostname()
        self.actor_id = f"docling-{self.hostname[-8:]}"
        self.docs_processed = 0
        self.chunks_created = 0

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=CPUS_PER_ACTOR, device="cpu"
        )

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        self.chunker = HybridChunker(
            tokenizer=EMBEDDING_MODEL, max_tokens=CHUNK_MAX_TOKENS
        )
        logfire.info(
            "Actor initialized",
            actor_id=self.actor_id,
            actor_type="DoclingChunkActor",
            hostname=self.hostname,
            cpus=CPUS_PER_ACTOR,
        )
        print(f"[{self.hostname}] DoclingChunkActor ready")

    def __call__(self, batch: Dict[str, List]) -> Dict[str, List]:
        from docling.datamodel.base_models import DocumentStream

        batch_size = len(batch["path"])
        with logfire.span(
            "docling-batch",
            actor_id=self.actor_id,
            batch_size=batch_size,
        ) as batch_span:
            out: Dict[str, List[Any]] = {
                "text": [],
                "source_file": [],
                "chunk_index": [],
                "chunk_size_chars": [],
                "num_pages": [],
            }

            for file_path in batch["path"]:
                fname = os.path.basename(file_path)
                with logfire.span(
                    "parse-pdf {fname}",
                    fname=fname,
                    actor_id=self.actor_id,
                ) as pdf_span:
                    try:
                        if not os.path.isfile(file_path):
                            logfire.warn("File not found", fname=fname, actor_id=self.actor_id)
                            pdf_span.set_attribute("status", "skipped-not-found")
                            continue

                        file_size = os.path.getsize(file_path)
                        if file_size < 100:
                            logfire.warn("File empty", fname=fname, actor_id=self.actor_id)
                            pdf_span.set_attribute("status", "skipped-empty")
                            continue

                        pdf_span.set_attribute("file_size_bytes", file_size)

                        t0 = time.time()
                        with open(file_path, "rb") as f:
                            file_bytes = f.read()
                        stream = DocumentStream(name=fname, stream=io.BytesIO(file_bytes))
                        
                        with logfire.span("docling-convert", fname=fname, actor_id=self.actor_id):
                            doc = self.converter.convert(stream).document
                        
                        doc_pages = doc.num_pages() if hasattr(doc, "num_pages") else 0
                        pdf_span.set_attribute("num_pages", doc_pages)

                        chunk_count = 0
                        with logfire.span("chunking", fname=fname, actor_id=self.actor_id):
                            for idx, chunk in enumerate(self.chunker.chunk(doc)):
                                if chunk.text.strip():
                                    out["text"].append(chunk.text)
                                    out["source_file"].append(fname)
                                    out["chunk_index"].append(idx)
                                    out["chunk_size_chars"].append(len(chunk.text))
                                    out["num_pages"].append(doc_pages)
                                    chunk_count += 1

                        elapsed = time.time() - t0
                        pdf_span.set_attribute("chunks_created", chunk_count)
                        pdf_span.set_attribute("elapsed_sec", round(elapsed, 2))
                        pdf_span.set_attribute("status", "success")
                        
                        self.docs_processed += 1
                        self.chunks_created += chunk_count

                    except Exception as e:
                        logfire.error(
                            "Parse error",
                            fname=fname,
                            actor_id=self.actor_id,
                            error=str(e)[:200],
                        )
                        pdf_span.set_attribute("status", "error")
                        pdf_span.set_attribute("error", str(e)[:200])

            batch_span.set_attribute("chunks_output", len(out["text"]))
            batch_span.set_attribute("total_docs_processed", self.docs_processed)
            batch_span.set_attribute("total_chunks_created", self.chunks_created)

            print(
                f"[{self.hostname}] DoclingChunkActor batch={batch_size} "
                f"chunks={len(out['text'])}"
            )
            return out


# ---------------------------------------------------------------------------
# Stage 2: Embed with sentence-transformers
# ---------------------------------------------------------------------------


class SentenceTransformersEmbeddingActor:
    """Embed text chunks using sentence-transformers (CPU)."""

    def __init__(self):
        import socket

        # Configure logfire in the worker process with distinct service name
        logfire.configure(
            service_name="rag-embedding",
            send_to_logfire=True,
        )

        import numpy as np
        from sentence_transformers import SentenceTransformer

        self.hostname = socket.gethostname()
        self.actor_id = f"embed-{self.hostname[-8:]}"
        self.batches_processed = 0
        self.chunks_embedded = 0

        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.np = np
        logfire.info(
            "Actor initialized",
            actor_id=self.actor_id,
            actor_type="SentenceTransformersEmbeddingActor",
            hostname=self.hostname,
            model=EMBEDDING_MODEL,
        )
        print(f"[{self.hostname}] EmbeddingActor ready")

    def __call__(self, batch: Dict[str, List]) -> Dict[str, List]:
        texts = list(batch["text"])
        batch_size = len(texts)
        
        with logfire.span(
            "embedding-batch",
            actor_id=self.actor_id,
            batch_size=batch_size,
        ) as span:
            t0 = time.time()
            
            with logfire.span(
                "encode-texts",
                actor_id=self.actor_id,
                num_texts=batch_size,
            ):
                arr = self.np.asarray(
                    self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
                )
            
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            embeddings = arr.tolist()

            elapsed = time.time() - t0
            self.batches_processed += 1
            self.chunks_embedded += batch_size
            
            span.set_attribute("elapsed_sec", round(elapsed, 2))
            span.set_attribute("chunks_per_sec", round(batch_size / elapsed, 2) if elapsed > 0 else 0)
            span.set_attribute("total_batches_processed", self.batches_processed)
            span.set_attribute("total_chunks_embedded", self.chunks_embedded)

            print(
                f"[{self.hostname}] EmbeddingActor batch={batch_size} time={elapsed:.2f}s"
            )

            return {
                "text": texts,
                "source_file": list(batch["source_file"]),
                "chunk_index": list(batch["chunk_index"]),
                "chunk_size_chars": list(batch["chunk_size_chars"]),
                "num_pages": list(batch.get("num_pages", [0] * len(texts))),
                "embedding": embeddings,
            }


# ---------------------------------------------------------------------------
# Stage 3: Insert into Milvus
# ---------------------------------------------------------------------------


class MilvusWriteActor:
    """Insert embeddings into Milvus."""

    def __init__(self):
        import socket

        # Configure logfire in the worker process with distinct service name
        logfire.configure(
            service_name="rag-milvus",
            send_to_logfire=True,
        )

        from pymilvus import MilvusClient

        self.hostname = socket.gethostname()
        self.actor_id = f"milvus-{self.hostname[-8:]}"
        self.batches_processed = 0
        self.total_inserted = 0

        self.milvus = MilvusClient(
            uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}", db_name=MILVUS_DB
        )
        logfire.info(
            "Actor initialized",
            actor_id=self.actor_id,
            actor_type="MilvusWriteActor",
            hostname=self.hostname,
            milvus_host=MILVUS_HOST,
            collection=COLLECTION_NAME,
        )
        print(f"[{self.hostname}] MilvusWriteActor ready")

    def __call__(self, batch: Dict[str, List]) -> Dict[str, List]:
        texts = list(batch["text"])
        source_files = list(batch["source_file"])
        chunk_indices = list(batch["chunk_index"])
        chunk_sizes = list(batch.get("chunk_size_chars", [0] * len(texts)))
        embeddings = list(batch["embedding"])
        batch_size = len(texts)

        with logfire.span(
            "milvus-batch",
            actor_id=self.actor_id,
            batch_size=batch_size,
        ) as span:
            t0 = time.time()
            inserted = 0
            insert_batches = 0
            
            for i in range(0, len(texts), MILVUS_BATCH_SIZE):
                end = min(i + MILVUS_BATCH_SIZE, len(texts))
                data = []
                for j in range(i, end):
                    tx = str(texts[j])
                    if len(tx) > MILVUS_TEXT_MAX_CHARS:
                        tx = tx[:MILVUS_TEXT_MAX_CHARS]
                    data.append({
                        "source_file": str(source_files[j]),
                        "chunk_index": int(chunk_indices[j]),
                        "text": tx,
                        "embedding": list(embeddings[j]),
                    })
                
                with logfire.span(
                    "milvus-insert",
                    actor_id=self.actor_id,
                    insert_batch=insert_batches,
                    rows=len(data),
                ):
                    self.milvus.insert(collection_name=COLLECTION_NAME, data=data)
                
                inserted += len(data)
                insert_batches += 1

            elapsed = time.time() - t0
            self.batches_processed += 1
            self.total_inserted += inserted
            
            span.set_attribute("rows_inserted", inserted)
            span.set_attribute("insert_batches", insert_batches)
            span.set_attribute("elapsed_sec", round(elapsed, 2))
            span.set_attribute("rows_per_sec", round(inserted / elapsed, 2) if elapsed > 0 else 0)
            span.set_attribute("total_batches_processed", self.batches_processed)
            span.set_attribute("total_rows_inserted", self.total_inserted)

            print(
                f"[{self.hostname}] MilvusWriteActor batch={batch_size} "
                f"inserted={inserted} time={elapsed:.2f}s"
            )

            return {
                "chunks_inserted": [1] * len(texts),
                "source_file": source_files,
                "chunk_size_chars": chunk_sizes,
                "num_pages": list(batch.get("num_pages", [0] * len(texts))),
            }


# ---------------------------------------------------------------------------
# Milvus collection setup
# ---------------------------------------------------------------------------


def setup_milvus_collection():
    """Create or recreate the Milvus collection with vector index."""
    from pymilvus import CollectionSchema, DataType, FieldSchema, MilvusClient

    client = MilvusClient(uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}", db_name=MILVUS_DB)

    if client.has_collection(COLLECTION_NAME):
        logfire.info("Dropping existing collection", collection=COLLECTION_NAME)
        print(f"Dropping existing collection '{COLLECTION_NAME}'")
        client.drop_collection(COLLECTION_NAME)

    schema = CollectionSchema(
        fields=[
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="source_file", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(
                name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM
            ),
        ],
        description="RAG document chunks",
    )
    client.create_collection(collection_name=COLLECTION_NAME, schema=schema)

    with logfire.span("create-vector-index", index_type="IVF_FLAT", metric_type="COSINE"):
        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="embedding",
            index_type="IVF_FLAT",
            metric_type="COSINE",
            params={"nlist": 128},
        )
        client.create_index(collection_name=COLLECTION_NAME, index_params=index_params)

    logfire.info(
        "Collection ready",
        collection=COLLECTION_NAME,
        embedding_dim=EMBEDDING_DIM,
        milvus_host=MILVUS_HOST,
    )
    print(f"Collection '{COLLECTION_NAME}' created (dim={EMBEDDING_DIM})")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _run_pipeline(ds) -> Dict[str, Any]:
    """Run the 3-stage streaming pipeline: chunk -> embed -> insert.

    Uses the `concurrency` parameter (recommended over deprecated
    ActorPoolStrategy). Ray Data's streaming executor overlaps stages:
    downstream actors start as soon as upstream blocks are ready.

    Resource budget (default): 6×4 + 4×1 + 2×1 = 30 CPUs (of 32 available).
    Two CPUs left for driver overhead / GCS.
    """

    total_cpus = (NUM_ACTORS * CPUS_PER_ACTOR) + NUM_EMBED_ACTORS + NUM_MILVUS_ACTORS
    
    logfire.info(
        "Pipeline configuration",
        docling_actors=NUM_ACTORS,
        docling_cpus_per_actor=CPUS_PER_ACTOR,
        embed_actors=NUM_EMBED_ACTORS,
        milvus_actors=NUM_MILVUS_ACTORS,
        total_cpus=total_cpus,
        batch_size=BATCH_SIZE,
        embed_batch_size=EMBED_MAP_BATCH_SIZE,
        milvus_batch_size=MILVUS_BATCH_SIZE,
    )
    
    print(
        f"Pipeline: docling={NUM_ACTORS}x{CPUS_PER_ACTOR}CPU, "
        f"embed={NUM_EMBED_ACTORS}x1CPU, milvus={NUM_MILVUS_ACTORS}x1CPU "
        f"(total={total_cpus} CPUs)"
    )

    # Stage 1: Parse + chunk (CPU-heavy, bottleneck — gets most resources)
    with logfire.span(
        "stage-1-docling-setup",
        actors=NUM_ACTORS,
        cpus_per_actor=CPUS_PER_ACTOR,
    ):
        ds = ds.map_batches(
            DoclingChunkActor,
            concurrency=NUM_ACTORS,
            batch_size=BATCH_SIZE,
            num_cpus=CPUS_PER_ACTOR,
        )

    # Stage 2: Embed with sentence-transformers (CPU, parallel)
    with logfire.span(
        "stage-2-embedding-setup",
        actors=NUM_EMBED_ACTORS,
        model=EMBEDDING_MODEL,
    ):
        ds = ds.map_batches(
            SentenceTransformersEmbeddingActor,
            concurrency=NUM_EMBED_ACTORS,
            batch_size=EMBED_MAP_BATCH_SIZE,
            num_cpus=1,
        )

    # Stage 3: Write to Milvus (I/O-bound — fewer actors, server is the limit)
    with logfire.span(
        "stage-3-milvus-setup",
        actors=NUM_MILVUS_ACTORS,
        collection=COLLECTION_NAME,
    ):
        results = ds.map_batches(
            MilvusWriteActor,
            concurrency=NUM_MILVUS_ACTORS,
            batch_size=MILVUS_BATCH_SIZE,
            num_cpus=1,
        )

    # Consume results and collect metrics
    with logfire.span("consume-results") as consume_span:
        start = time.time()
        total_chunks = 0
        source_files: set = set()
        all_chunk_sizes: List[int] = []
        file_pages: Dict[str, int] = {}
        batch_count = 0

        for batch in results.iter_batches(batch_size=100, prefetch_batches=2):
            batch_count += 1
            for inserted, fname, size, pages in zip(
                batch["chunks_inserted"],
                batch["source_file"],
                batch["chunk_size_chars"],
                batch["num_pages"],
            ):
                total_chunks += int(inserted)
                fname = fname if isinstance(fname, str) else fname[0]
                if fname not in file_pages:
                    file_pages[fname] = int(pages)
                source_files.add(fname)
                if isinstance(size, list):
                    all_chunk_sizes.extend(size)
                else:
                    all_chunk_sizes.append(size)
            
            # Log progress every 10 batches
            if batch_count % 10 == 0:
                logfire.info(
                    "Pipeline progress",
                    batches_consumed=batch_count,
                    docs_so_far=len(source_files),
                    chunks_so_far=total_chunks,
                )

        total_pages = sum(file_pages.values())
        wall_clock = time.time() - start
        total_docs = len(source_files)
        
        consume_span.set_attribute("total_docs", total_docs)
        consume_span.set_attribute("total_chunks", total_chunks)
        consume_span.set_attribute("total_pages", total_pages)
        consume_span.set_attribute("wall_clock_sec", round(wall_clock, 2))
        consume_span.set_attribute("batches_consumed", batch_count)
        
    return _build_metrics(
        total_docs, total_chunks, wall_clock, all_chunk_sizes, total_pages=total_pages
    )


# ---------------------------------------------------------------------------
# Metrics and reporting
# ---------------------------------------------------------------------------


def _build_metrics(
    total_docs: int,
    total_chunks: int,
    wall_clock: float,
    chunk_sizes: List[int],
    total_pages: int = 0,
) -> Dict[str, Any]:
    """Build metrics dictionary. All values cast to native types for JSON."""
    docs_per_sec = total_docs / wall_clock if wall_clock > 0 else 0
    chunks_per_sec = total_chunks / wall_clock if wall_clock > 0 else 0
    pages_per_sec = total_pages / wall_clock if wall_clock > 0 else 0

    avg_chunk = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
    min_chunk = min(chunk_sizes) if chunk_sizes else 0
    max_chunk = max(chunk_sizes) if chunk_sizes else 0

    chunks_per_doc = total_chunks / total_docs if total_docs > 0 else 0
    pages_per_doc = total_pages / total_docs if total_docs > 0 else 0
    total_cpu = (NUM_ACTORS * CPUS_PER_ACTOR) + NUM_EMBED_ACTORS + NUM_MILVUS_ACTORS

    return {
        "embedding_model": str(EMBEDDING_MODEL),
        "num_actors": int(NUM_ACTORS),
        "cpus_per_actor": int(CPUS_PER_ACTOR),
        "num_embed_actors": int(NUM_EMBED_ACTORS),
        "num_milvus_actors": int(NUM_MILVUS_ACTORS),
        "chunk_max_tokens": int(CHUNK_MAX_TOKENS),
        "total_cpu_requested": int(total_cpu),
        "total_documents": int(total_docs),
        "total_pages": int(total_pages),
        "total_chunks": int(total_chunks),
        "pages_per_doc": float(round(pages_per_doc, 1)),
        "chunks_per_doc": float(round(chunks_per_doc, 1)),
        "wall_clock_s": float(round(wall_clock, 2)),
        "pages_per_sec": float(round(pages_per_sec, 2)),
        "docs_per_sec": float(round(docs_per_sec, 2)),
        "chunks_per_sec": float(round(chunks_per_sec, 2)),
        "avg_chunk_size_chars": float(round(avg_chunk, 1)),
        "min_chunk_size_chars": int(min_chunk),
        "max_chunk_size_chars": int(max_chunk),
        "embedding_dim": int(EMBEDDING_DIM),
    }


def _print_report(metrics: Dict[str, Any]):
    """Print human-readable report and machine-readable JSON footer."""
    from pymilvus import MilvusClient

    with logfire.span("finalize-report") as report_span:
        client = MilvusClient(uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}", db_name=MILVUS_DB)
        client.load_collection(COLLECTION_NAME)
        _flush = getattr(client, "flush", None)
        if callable(_flush):
            try:
                _flush(collection_name=COLLECTION_NAME)
            except Exception:
                pass

        stats = client.get_collection_stats(COLLECTION_NAME)
        row_count = stats.get("row_count") if isinstance(stats, dict) else None
        metrics["milvus_row_count"] = int(row_count) if row_count is not None else None

        report_span.set_attribute("milvus_row_count", metrics["milvus_row_count"])
        report_span.set_attribute("total_documents", metrics["total_documents"])
        report_span.set_attribute("total_chunks", metrics["total_chunks"])
        report_span.set_attribute("total_pages", metrics["total_pages"])
        report_span.set_attribute("wall_clock_s", metrics["wall_clock_s"])
        report_span.set_attribute("docs_per_sec", metrics["docs_per_sec"])
        report_span.set_attribute("pages_per_sec", metrics["pages_per_sec"])
        report_span.set_attribute("chunks_per_sec", metrics["chunks_per_sec"])

    print("\n" + "=" * 60)
    print("PERFORMANCE REPORT")
    print("=" * 60)
    print(f"Model:           {metrics['embedding_model']}")
    print(
        f"Docling actors:  {metrics['num_actors']} x {metrics['cpus_per_actor']} CPUs"
    )
    print(f"Embed actors:    {metrics['num_embed_actors']} x 1 CPU")
    print(f"Milvus actors:   {metrics['num_milvus_actors']} x 1 CPU")
    print(f"Total CPUs:      {metrics['total_cpu_requested']}")
    print("-" * 60)
    print(f"Documents:       {metrics['total_documents']}")
    print(
        f"Pages:           {metrics['total_pages']} ({metrics['pages_per_doc']:.1f}/doc)"
    )
    print(
        f"Chunks:          {metrics['total_chunks']} ({metrics['chunks_per_doc']:.1f}/doc)"
    )
    print(f"Wall clock:      {metrics['wall_clock_s']:.1f}s")
    print(
        f"Throughput:      {metrics['pages_per_sec']:.2f} pages/sec, "
        f"{metrics['docs_per_sec']:.2f} docs/sec, "
        f"{metrics['chunks_per_sec']:.1f} chunks/sec"
    )
    print(f"Milvus:          {row_count} rows in '{COLLECTION_NAME}'")
    print("=" * 60)
    try:
        print(f"\nRAG_METRICS_JSON={json.dumps(metrics)}")
    except TypeError as exc:
        print(f"\nRAG_METRICS_JSON=<could not serialize: {exc}>")
        print(metrics)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run():
    with logfire.span("rag-ingestion-pipeline"):
        _configure_ray_context()

        input_full_path = os.path.join(PVC_MOUNT_PATH, INPUT_PATH)
        target_blocks = max(1, NUM_ACTORS * REPARTITION_FACTOR)

        # Pass paths only -- actors read from the PVC directly, avoiding
        # loading all PDF bytes into Ray's object store.
        with logfire.span("collect-pdf-paths", input_path=input_full_path, limit=NUM_FILES):
            paths = _collect_pdf_paths(input_full_path, NUM_FILES)

        if not paths:
            logfire.warn("No PDFs found", path=input_full_path)
            print(f"No PDFs found under {input_full_path}")
            return
        
        logfire.info(
            "Starting ingestion",
            num_pdfs=len(paths),
            input_path=INPUT_PATH,
            target_blocks=target_blocks,
            embedding_model=EMBEDDING_MODEL,
        )
        print(f"Processing {len(paths)} PDFs")
        ds = ray.data.from_items([{"path": p} for p in paths])
        ds = ds.repartition(num_blocks=target_blocks, shuffle=False)

        with logfire.span("setup-milvus"):
            setup_milvus_collection()

        metrics = _run_pipeline(ds)
        
        logfire.info(
            "Pipeline complete",
            total_documents=metrics.get("total_documents", 0),
            total_chunks=metrics.get("total_chunks", 0),
            total_pages=metrics.get("total_pages", 0),
            wall_clock_s=metrics.get("wall_clock_s", 0),
            docs_per_sec=metrics.get("docs_per_sec", 0),
            pages_per_sec=metrics.get("pages_per_sec", 0),
            chunks_per_sec=metrics.get("chunks_per_sec", 0),
        )
        _print_report(metrics)


if __name__ == "__main__":
    ray.init(ignore_reinit_error=True)
    run()
