"""RAG ingestion pipeline: parse PDFs, chunk, embed, insert into Milvus.

3-stage Ray Data pipeline submitted as a RayJob to an existing RayCluster:
  Stage 1: DoclingChunkActor              -- parse PDFs + chunk (CPU, parallel)
  Stage 2: Embedding (mode-dependent)     -- "local" uses sentence-transformers (CPU)
                                             "service" uses vLLM via ray.data.llm (GPU)
  Stage 3: MilvusWriteActor              -- insert vectors into Milvus (I/O, parallel)

Execution model:
  Ray Data runs these operators in *dependency order*. Downstream stages can start
  as soon as upstream blocks exist (pipelining), but Docling is usually the long
  pole.

All configuration is read from environment variables set by the notebook.
"""

import io
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import ray

logger = logging.getLogger("rag-ingestion")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

# ---------------------------------------------------------------------------
# Parameters (all from environment variables)
# ---------------------------------------------------------------------------

NUM_ACTORS = int(os.environ.get("NUM_ACTORS", "6"))
NUM_MILVUS_ACTORS = int(os.environ.get("NUM_MILVUS_ACTORS", "2"))
CPUS_PER_ACTOR = int(os.environ.get("CPUS_PER_ACTOR", "4"))

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "2"))
MILVUS_BATCH_SIZE = int(os.environ.get("MILVUS_BATCH_SIZE", "64"))

PVC_MOUNT_PATH = os.environ.get("PVC_MOUNT_PATH", "/mnt/data")
INPUT_PATH = os.environ.get("INPUT_PATH", "input/pdfs")
NUM_FILES = int(os.environ.get("NUM_FILES", "0"))

MILVUS_HOST = os.environ.get("MILVUS_HOST", "milvus-milvus.milvus.svc.cluster.local")
MILVUS_PORT = int(os.environ.get("MILVUS_PORT", "19530"))
MILVUS_DB = os.environ.get("MILVUS_DB", "default")
COLLECTION_NAME = os.environ.get("MILVUS_COLLECTION", "rag_documents")
MILVUS_TEXT_MAX_CHARS = int(os.environ.get("MILVUS_TEXT_MAX_CHARS", "8192"))
DROP_EXISTING_COLLECTION = (
    os.environ.get("DROP_EXISTING_COLLECTION", "true").lower() == "true"
)

# Embedding mode: "local" (sentence-transformers, CPU) or "service" (vLLM, GPU)
EMBEDDING_MODE = os.environ.get("EMBEDDING_MODE", "service")
EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL", "ibm-granite/granite-embedding-125m-english"
)
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "768"))
EMBEDDING_BATCH_SIZE = int(os.environ.get("EMBEDDING_BATCH_SIZE", "32"))
NUM_EMBEDDING_ACTORS = int(os.environ.get("NUM_EMBEDDING_ACTORS", "2"))

# vLLM-specific configuration (only used when EMBEDDING_MODE = "service")
VLLM_MODEL_SOURCE = os.environ.get("VLLM_MODEL_SOURCE", EMBEDDING_MODEL)
VLLM_BATCH_SIZE = int(os.environ.get("VLLM_BATCH_SIZE", "4"))
VLLM_CONCURRENCY = int(os.environ.get("VLLM_CONCURRENCY", "1"))
VLLM_ACCELERATOR_TYPE = os.environ.get("VLLM_ACCELERATOR_TYPE", None)
VLLM_ENGINE_KWARGS_JSON = os.environ.get("VLLM_ENGINE_KWARGS_JSON", "{}")

CHUNK_MAX_TOKENS = int(os.environ.get("CHUNK_MAX_TOKENS", "256"))

REPARTITION_FACTOR = int(os.environ.get("REPARTITION_FACTOR", "2"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_pdf_paths(input_path: str, limit: int) -> List[str]:
    """Collect PDF paths up to limit (0 = no limit).

    Paths are sorted for deterministic ordering so that a NUM_FILES limit
    always selects the same subset regardless of filesystem traversal order.
    """
    root = Path(input_path)
    if not root.is_dir():
        return []
    out = sorted(str(p) for p in root.rglob("*.pdf") if p.is_file())
    return out[:limit] if limit > 0 else out


def _configure_ray_context():
    """Configure Ray Data context for throughput and progress display."""
    ctx = ray.data.DataContext.get_current()
    ctx.max_errored_blocks = int(os.environ.get("MAX_ERRORED_BLOCKS", "0"))
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
        self.docs_skipped = 0
        self.docs_failed = 0
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
        print(f"[{self.hostname}] DoclingChunkActor ready")

    def __call__(self, batch: Dict[str, List]) -> Dict[str, List]:
        from docling.datamodel.base_models import DocumentStream

        batch_size = len(batch["path"])
        batch_skipped = 0
        batch_failed = 0
        out: Dict[str, List[Any]] = {
            "text": [],
            "source_file": [],
            "chunk_index": [],
            "chunk_size_chars": [],
            "num_pages": [],
            "docling_parse_time_s": [],
            "chunk_time_s": [],
            "docs_skipped": [],
            "docs_failed": [],
        }

        for file_path in batch["path"]:
            fname = os.path.basename(file_path)
            try:
                if not os.path.isfile(file_path):
                    logger.warning("File not found, skipping: %s", fname)
                    batch_skipped += 1
                    continue

                file_size = os.path.getsize(file_path)
                if file_size < 100:
                    logger.warning(
                        "File too small (%d bytes), skipping: %s", file_size, fname
                    )
                    batch_skipped += 1
                    continue

                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                stream = DocumentStream(name=fname, stream=io.BytesIO(file_bytes))

                t_parse = time.time()
                doc = self.converter.convert(stream).document
                parse_elapsed = time.time() - t_parse

                doc_pages = doc.num_pages() if hasattr(doc, "num_pages") else 0

                t_chunk = time.time()
                chunks = [c for c in self.chunker.chunk(doc) if c.text.strip()]
                chunk_elapsed = time.time() - t_chunk

                for idx, chunk in enumerate(chunks):
                    out["text"].append(chunk.text)
                    out["source_file"].append(fname)
                    out["chunk_index"].append(idx)
                    out["chunk_size_chars"].append(len(chunk.text))
                    out["num_pages"].append(doc_pages)
                    out["docling_parse_time_s"].append(parse_elapsed)
                    out["chunk_time_s"].append(chunk_elapsed)
                    out["docs_skipped"].append(0)
                    out["docs_failed"].append(0)

                self.docs_processed += 1
                self.chunks_created += len(chunks)
                logger.info(
                    "%s: %d chunks, parse=%.1fs chunk=%.1fs",
                    fname,
                    len(chunks),
                    parse_elapsed,
                    chunk_elapsed,
                )

            except Exception as e:
                batch_failed += 1
                logger.error("Parse error for %s: %s", fname, str(e)[:200])

        self.docs_skipped += batch_skipped
        self.docs_failed += batch_failed

        if batch_skipped or batch_failed:
            logger.warning(
                "Batch %d files: %d ok, %d skipped, %d failed "
                "(cumulative: %d processed, %d skipped, %d failed)",
                batch_size,
                batch_size - batch_skipped - batch_failed,
                batch_skipped,
                batch_failed,
                self.docs_processed,
                self.docs_skipped,
                self.docs_failed,
            )

        # Emit per-batch failure counts once (on first chunk or as a
        # single-row sentinel when every file in the batch was skipped/failed).
        if out["text"]:
            out["docs_skipped"][0] = batch_skipped
            out["docs_failed"][0] = batch_failed
        elif batch_skipped or batch_failed:
            out["text"].append("")
            out["source_file"].append("__sentinel__")
            out["chunk_index"].append(-1)
            out["chunk_size_chars"].append(0)
            out["num_pages"].append(0)
            out["docling_parse_time_s"].append(0.0)
            out["chunk_time_s"].append(0.0)
            out["docs_skipped"].append(batch_skipped)
            out["docs_failed"].append(batch_failed)

        print(
            f"[{self.hostname}] DoclingChunkActor batch={batch_size} "
            f"chunks={len(out['text'])} skipped={batch_skipped} failed={batch_failed}"
        )
        return out


# ---------------------------------------------------------------------------
# Stage 2: Embed with vLLM via Ray Data LLM processor
# ---------------------------------------------------------------------------


def _build_vllm_embed_processor():
    """Build a Ray Data LLM processor for embedding with vLLM.

    Uses vLLMEngineProcessorConfig with task_type='embed' so that the vLLM
    engine runs inside Ray Data GPU workers. The model, concurrency, and
    engine kwargs are all driven by environment variables.
    """
    from ray.data.llm import build_processor, vLLMEngineProcessorConfig

    try:
        engine_kwargs = json.loads(VLLM_ENGINE_KWARGS_JSON)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"VLLM_ENGINE_KWARGS_JSON is not valid JSON: {VLLM_ENGINE_KWARGS_JSON!r}"
        ) from exc

    config = vLLMEngineProcessorConfig(
        model_source=VLLM_MODEL_SOURCE,
        task_type="embed",
        batch_size=VLLM_BATCH_SIZE,
        concurrency=VLLM_CONCURRENCY,
        accelerator_type=VLLM_ACCELERATOR_TYPE if VLLM_ACCELERATOR_TYPE else None,
        engine_kwargs=engine_kwargs,
        tokenize_stage={"enabled": False},
        detokenize_stage={"enabled": False},
        chat_template_stage={"enabled": False},
    )

    def _preprocess(row):
        row["prompt"] = row["text"]
        row["embed_start_time"] = time.time()
        return row

    def _postprocess(row):
        return dict(
            text=row["text"],
            source_file=row["source_file"],
            chunk_index=row["chunk_index"],
            chunk_size_chars=row["chunk_size_chars"],
            num_pages=row["num_pages"],
            docling_parse_time_s=row["docling_parse_time_s"],
            chunk_time_s=row["chunk_time_s"],
            docs_skipped=row["docs_skipped"],
            docs_failed=row["docs_failed"],
            embed_time_s=time.time() - row["embed_start_time"],
            embedding=row["embeddings"],
        )

    processor = build_processor(
        config,
        preprocess=_preprocess,
        postprocess=_postprocess,
    )
    return processor


# ---------------------------------------------------------------------------
# Stage 2 (local mode): Embed with sentence-transformers (CPU)
# ---------------------------------------------------------------------------


class SentenceTransformerEmbedActor:
    """Generate embeddings using sentence-transformers on CPU."""

    def __init__(self):
        import socket

        from sentence_transformers import SentenceTransformer

        self.hostname = socket.gethostname()
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.chunks_embedded = 0

        actual_dim = self.model.get_sentence_embedding_dimension()
        if actual_dim != EMBEDDING_DIM:
            raise ValueError(
                f"Model '{EMBEDDING_MODEL}' produces {actual_dim}-dim embeddings "
                f"but EMBEDDING_DIM is set to {EMBEDDING_DIM}"
            )

        print(
            f"[{self.hostname}] SentenceTransformerEmbedActor ready ({EMBEDDING_MODEL})"
        )

    def __call__(self, batch: Dict[str, List]) -> Dict[str, List]:
        texts = list(batch["text"])
        t0 = time.time()
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        elapsed = time.time() - t0
        per_chunk = elapsed / len(texts) if texts else 0.0

        self.chunks_embedded += len(texts)

        return {
            "text": texts,
            "source_file": list(batch["source_file"]),
            "chunk_index": list(batch["chunk_index"]),
            "chunk_size_chars": list(batch["chunk_size_chars"]),
            "num_pages": list(batch["num_pages"]),
            "docling_parse_time_s": list(batch["docling_parse_time_s"]),
            "chunk_time_s": list(batch["chunk_time_s"]),
            "docs_skipped": list(batch["docs_skipped"]),
            "docs_failed": list(batch["docs_failed"]),
            "embed_time_s": [per_chunk] * len(texts),
            "embedding": [emb.tolist() for emb in embeddings],
        }


# ---------------------------------------------------------------------------
# Stage 3: Insert into Milvus
# ---------------------------------------------------------------------------


class MilvusWriteActor:
    """Insert embeddings into Milvus."""

    def __init__(self):
        import socket

        from pymilvus import MilvusClient

        self.hostname = socket.gethostname()
        self.actor_id = f"milvus-{self.hostname[-8:]}"
        self.batches_processed = 0
        self.total_inserted = 0
        self.total_truncated = 0

        self.milvus = MilvusClient(
            uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}", db_name=MILVUS_DB
        )
        print(f"[{self.hostname}] MilvusWriteActor ready")

    def __call__(self, batch: Dict[str, List]) -> Dict[str, List]:
        texts = list(batch["text"])
        source_files = list(batch["source_file"])
        chunk_indices = list(batch["chunk_index"])
        chunk_sizes = list(batch.get("chunk_size_chars", [0] * len(texts)))
        embeddings = list(batch["embedding"])
        batch_size = len(texts)

        t0 = time.time()
        inserted = 0
        batch_truncated = 0

        for i in range(0, len(texts), MILVUS_BATCH_SIZE):
            end = min(i + MILVUS_BATCH_SIZE, len(texts))
            data = []
            for j in range(i, end):
                tx = str(texts[j])
                if len(tx) > MILVUS_TEXT_MAX_CHARS:
                    logger.warning(
                        "Truncating chunk %s:%d from %d to %d chars",
                        source_files[j],
                        chunk_indices[j],
                        len(tx),
                        MILVUS_TEXT_MAX_CHARS,
                    )
                    tx = tx[:MILVUS_TEXT_MAX_CHARS]
                    batch_truncated += 1
                data.append({
                    "source_file": str(source_files[j]),
                    "chunk_index": int(chunk_indices[j]),
                    "text": tx,
                    "embedding": list(embeddings[j]),
                })

            for attempt in range(3):
                try:
                    self.milvus.insert(collection_name=COLLECTION_NAME, data=data)
                    break
                except (TypeError, ValueError):
                    raise
                except Exception:
                    if attempt == 2:
                        raise
                    wait = 2**attempt
                    logger.warning("Milvus insert retry %d/3 in %ds", attempt + 1, wait)
                    time.sleep(wait)
            inserted += len(data)

        elapsed = time.time() - t0
        self.batches_processed += 1
        self.total_inserted += inserted
        self.total_truncated += batch_truncated

        per_chunk_write_time = elapsed / batch_size if batch_size > 0 else 0.0

        if batch_truncated:
            logger.warning(
                "Batch had %d/%d chunks truncated to %d chars "
                "(cumulative: %d truncated)",
                batch_truncated,
                batch_size,
                MILVUS_TEXT_MAX_CHARS,
                self.total_truncated,
            )

        print(
            f"[{self.hostname}] MilvusWriteActor batch={batch_size} "
            f"inserted={inserted} truncated={batch_truncated} time={elapsed:.2f}s"
        )

        return {
            "chunks_inserted": [1] * len(texts),
            "source_file": source_files,
            "chunk_size_chars": chunk_sizes,
            "num_pages": list(batch.get("num_pages", [0] * len(texts))),
            "docling_parse_time_s": list(
                batch.get("docling_parse_time_s", [0.0] * len(texts))
            ),
            "chunk_time_s": list(batch.get("chunk_time_s", [0.0] * len(texts))),
            "embed_time_s": list(batch.get("embed_time_s", [0.0] * len(texts))),
            "milvus_write_time_s": [per_chunk_write_time] * len(texts),
            "docs_skipped": list(batch.get("docs_skipped", [0] * len(texts))),
            "docs_failed": list(batch.get("docs_failed", [0] * len(texts))),
        }


# ---------------------------------------------------------------------------
# Milvus collection setup
# ---------------------------------------------------------------------------


def setup_milvus_collection():
    """Create or recreate the Milvus collection with vector index."""
    from pymilvus import CollectionSchema, DataType, FieldSchema, MilvusClient

    client = MilvusClient(uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}", db_name=MILVUS_DB)

    if client.has_collection(COLLECTION_NAME):
        if DROP_EXISTING_COLLECTION:
            print(f"Dropping existing collection '{COLLECTION_NAME}'")
            client.drop_collection(COLLECTION_NAME)
        else:
            raise RuntimeError(
                f"Collection '{COLLECTION_NAME}' already exists. "
                f"Set DROP_EXISTING_COLLECTION=true to drop and recreate it, "
                f"or use a different MILVUS_COLLECTION name."
            )

    schema = CollectionSchema(
        fields=[
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="source_file", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(
                name="text", dtype=DataType.VARCHAR, max_length=MILVUS_TEXT_MAX_CHARS
            ),
            FieldSchema(
                name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM
            ),
        ],
        description="RAG document chunks",
    )
    client.create_collection(collection_name=COLLECTION_NAME, schema=schema)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_type="IVF_FLAT",
        metric_type="COSINE",
        params={"nlist": 128},
    )
    client.create_index(collection_name=COLLECTION_NAME, index_params=index_params)

    print(f"Collection '{COLLECTION_NAME}' created (dim={EMBEDDING_DIM})")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _run_pipeline(ds) -> Dict[str, Any]:
    """Run the 3-stage streaming pipeline: chunk -> embed -> insert.

    Stage 1 uses map_batches with CPU actors for Docling parsing/chunking.
    Stage 2 embeds chunks — either locally via sentence-transformers (CPU)
    or via vLLMEngineProcessorConfig (GPU), controlled by EMBEDDING_MODE.
    Stage 3 uses map_batches with CPU actors for Milvus insertion.
    """

    if EMBEDDING_MODE == "local":
        print(
            f"Pipeline: docling={NUM_ACTORS}x{CPUS_PER_ACTOR}CPU, "
            f"embed=sentence-transformers x{NUM_EMBEDDING_ACTORS} (CPU), "
            f"milvus={NUM_MILVUS_ACTORS}x1CPU"
        )
    else:
        print(
            f"Pipeline: docling={NUM_ACTORS}x{CPUS_PER_ACTOR}CPU, "
            f"embed=vLLM concurrency={VLLM_CONCURRENCY} (GPU), "
            f"milvus={NUM_MILVUS_ACTORS}x1CPU"
        )

    # Stage 1: Parse + chunk (CPU-heavy, bottleneck)
    ds = ds.map_batches(
        DoclingChunkActor,
        concurrency=NUM_ACTORS,
        batch_size=BATCH_SIZE,
        num_cpus=CPUS_PER_ACTOR,
    )

    # Stage 2: Embed
    if EMBEDDING_MODE == "local":
        ds = ds.map_batches(
            SentenceTransformerEmbedActor,
            concurrency=NUM_EMBEDDING_ACTORS,
            batch_size=EMBEDDING_BATCH_SIZE,
            num_cpus=2,
        )
    else:
        embed_processor = _build_vllm_embed_processor()
        ds = embed_processor(ds)

    # Stage 3: Write to Milvus (I/O-bound)
    results = ds.map_batches(
        MilvusWriteActor,
        concurrency=NUM_MILVUS_ACTORS,
        batch_size=MILVUS_BATCH_SIZE,
        num_cpus=1,
    )

    # Consume results and collect metrics
    start = time.time()
    total_chunks = 0
    total_docs_skipped = 0
    total_docs_failed = 0
    source_files: set = set()
    all_chunk_sizes: List[int] = []
    file_pages: Dict[str, int] = {}
    batch_count = 0

    stage_timings: Dict[str, List[float]] = {
        "docling_parse_time_s": [],
        "chunk_time_s": [],
        "embed_time_s": [],
        "milvus_write_time_s": [],
    }
    timing_source_files: List[str] = []
    timing_num_pages: List[int] = []

    for batch in results.iter_batches(batch_size=100, prefetch_batches=2):
        batch_count += 1
        for (
            inserted,
            fname,
            size,
            pages,
            dt_parse,
            dt_chunk,
            dt_embed,
            dt_milvus,
            d_skipped,
            d_failed,
        ) in zip(
            batch["chunks_inserted"],
            batch["source_file"],
            batch["chunk_size_chars"],
            batch["num_pages"],
            batch["docling_parse_time_s"],
            batch["chunk_time_s"],
            batch["embed_time_s"],
            batch["milvus_write_time_s"],
            batch["docs_skipped"],
            batch["docs_failed"],
            strict=True,
        ):
            total_chunks += int(inserted)
            total_docs_skipped += int(d_skipped)
            total_docs_failed += int(d_failed)
            fname = fname if isinstance(fname, str) else fname[0]
            if fname not in file_pages:
                file_pages[fname] = int(pages)
            source_files.add(fname)
            if isinstance(size, list):
                all_chunk_sizes.extend(size)
            else:
                all_chunk_sizes.append(size)

            stage_timings["docling_parse_time_s"].append(float(dt_parse))
            stage_timings["chunk_time_s"].append(float(dt_chunk))
            stage_timings["embed_time_s"].append(float(dt_embed))
            stage_timings["milvus_write_time_s"].append(float(dt_milvus))
            timing_source_files.append(fname)
            timing_num_pages.append(int(pages))

        if batch_count % 10 == 0:
            logger.info(
                "Progress: %d batches, %d docs, %d chunks",
                batch_count,
                len(source_files),
                total_chunks,
            )

    total_pages = sum(file_pages.values())
    wall_clock = time.time() - start
    total_docs = len(source_files)

    return _build_metrics(
        total_docs,
        total_chunks,
        wall_clock,
        all_chunk_sizes,
        total_pages=total_pages,
        stage_timings=stage_timings,
        timing_source_files=timing_source_files,
        timing_num_pages=timing_num_pages,
        file_pages=file_pages,
        total_docs_skipped=total_docs_skipped,
        total_docs_failed=total_docs_failed,
    )


# ---------------------------------------------------------------------------
# Metrics and reporting
# ---------------------------------------------------------------------------


def _compute_per_stage_metrics(
    stage_timings: Dict[str, List[float]],
    timing_source_files: List[str],
    timing_num_pages: List[int],
    file_pages: Dict[str, int],
) -> Dict[str, Any]:
    """Compute per-PDF and per-page averages for each pipeline stage.

    Docling parse and chunk times are per-PDF (every chunk from the same PDF
    carries the same value), so we deduplicate by source file before averaging.
    Embed and Milvus write times are per-chunk, so per-PDF values are computed
    by summing all chunk times within each PDF and averaging across PDFs.
    """
    from collections import defaultdict

    total_pages = sum(file_pages.values())
    metrics: Dict[str, Any] = {}

    per_pdf_parse: Dict[str, float] = {}
    per_pdf_chunk: Dict[str, float] = {}
    per_pdf_embed: Dict[str, float] = defaultdict(float)
    per_pdf_milvus: Dict[str, float] = defaultdict(float)

    for i, fname in enumerate(timing_source_files):
        if fname not in per_pdf_parse:
            per_pdf_parse[fname] = stage_timings["docling_parse_time_s"][i]
            per_pdf_chunk[fname] = stage_timings["chunk_time_s"][i]
        per_pdf_embed[fname] += stage_timings["embed_time_s"][i]
        per_pdf_milvus[fname] += stage_timings["milvus_write_time_s"][i]

    def _safe_mean(vals):
        return sum(vals) / len(vals) if vals else 0.0

    parse_vals = list(per_pdf_parse.values())
    chunk_vals = list(per_pdf_chunk.values())
    embed_vals = list(per_pdf_embed.values())
    milvus_vals = list(per_pdf_milvus.values())

    metrics["avg_docling_parse_per_pdf_s"] = round(_safe_mean(parse_vals), 3)
    metrics["avg_chunk_per_pdf_s"] = round(_safe_mean(chunk_vals), 3)
    metrics["avg_embed_per_pdf_s"] = round(_safe_mean(embed_vals), 3)
    metrics["avg_milvus_write_per_pdf_s"] = round(_safe_mean(milvus_vals), 3)

    if total_pages > 0:
        metrics["avg_docling_parse_per_page_s"] = round(
            sum(parse_vals) / total_pages, 4
        )
        metrics["avg_chunk_per_page_s"] = round(sum(chunk_vals) / total_pages, 4)
        metrics["avg_embed_per_page_s"] = round(sum(embed_vals) / total_pages, 4)
        metrics["avg_milvus_write_per_page_s"] = round(
            sum(milvus_vals) / total_pages, 4
        )
    else:
        metrics["avg_docling_parse_per_page_s"] = 0.0
        metrics["avg_chunk_per_page_s"] = 0.0
        metrics["avg_embed_per_page_s"] = 0.0
        metrics["avg_milvus_write_per_page_s"] = 0.0

    embed_times = stage_timings["embed_time_s"]
    milvus_times = stage_timings["milvus_write_time_s"]
    metrics["avg_embed_per_chunk_s"] = round(_safe_mean(embed_times), 4)
    metrics["avg_milvus_write_per_chunk_s"] = round(_safe_mean(milvus_times), 4)

    metrics["avg_total_per_pdf_s"] = round(
        metrics["avg_docling_parse_per_pdf_s"]
        + metrics["avg_chunk_per_pdf_s"]
        + metrics["avg_embed_per_pdf_s"]
        + metrics["avg_milvus_write_per_pdf_s"],
        3,
    )
    metrics["avg_total_per_page_s"] = round(
        metrics["avg_docling_parse_per_page_s"]
        + metrics["avg_chunk_per_page_s"]
        + metrics["avg_embed_per_page_s"]
        + metrics["avg_milvus_write_per_page_s"],
        4,
    )

    return {k: float(v) for k, v in metrics.items()}


def _build_metrics(
    total_docs: int,
    total_chunks: int,
    wall_clock: float,
    chunk_sizes: List[int],
    total_pages: int = 0,
    stage_timings: Dict[str, List[float]] | None = None,
    timing_source_files: List[str] | None = None,
    timing_num_pages: List[int] | None = None,
    file_pages: Dict[str, int] | None = None,
    total_docs_skipped: int = 0,
    total_docs_failed: int = 0,
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

    metrics = {
        "embedding_mode": str(EMBEDDING_MODE),
        "embedding_model": str(EMBEDDING_MODEL),
        "num_actors": int(NUM_ACTORS),
        "cpus_per_actor": int(CPUS_PER_ACTOR),
        "vllm_concurrency": int(VLLM_CONCURRENCY),
        "num_milvus_actors": int(NUM_MILVUS_ACTORS),
        "chunk_max_tokens": int(CHUNK_MAX_TOKENS),
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
        "total_docs_skipped": int(total_docs_skipped),
        "total_docs_failed": int(total_docs_failed),
    }

    if stage_timings and timing_source_files and file_pages:
        metrics.update(
            _compute_per_stage_metrics(
                stage_timings,
                timing_source_files,
                timing_num_pages or [],
                file_pages,
            )
        )

    return metrics


def _print_report(metrics: Dict[str, Any]):
    """Print human-readable report and machine-readable JSON footer."""
    from pymilvus import MilvusClient

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

    print("\n" + "=" * 60)
    print("PERFORMANCE REPORT")
    print("=" * 60)
    print(f"Embed mode:      {metrics['embedding_mode']}")
    print(f"Embed model:     {metrics['embedding_model']}")
    print(
        f"Docling actors:  {metrics['num_actors']} x {metrics['cpus_per_actor']} CPUs"
    )
    if metrics["embedding_mode"] == "service":
        print(f"vLLM embed:      concurrency={metrics['vllm_concurrency']} (GPU)")
    else:
        print(f"ST embed:        {NUM_EMBEDDING_ACTORS} actors (CPU)")
    print(f"Milvus actors:   {metrics['num_milvus_actors']} x 1 CPU")
    print("-" * 60)
    print(f"Documents:       {metrics['total_documents']}")
    if metrics.get("total_docs_skipped") or metrics.get("total_docs_failed"):
        print(
            f"  Skipped:       {metrics['total_docs_skipped']}  |  "
            f"Failed: {metrics['total_docs_failed']}"
        )
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

    if "avg_docling_parse_per_pdf_s" in metrics:
        print("\n" + "-" * 60)
        print("PER-STAGE TIMING (averages)")
        print("-" * 60)
        print(f"{'Stage':<20} {'per PDF (s)':>12} {'per page (s)':>14}")
        print(f"{'─' * 20} {'─' * 12} {'─' * 14}")
        stages = [
            (
                "Docling parse",
                "avg_docling_parse_per_pdf_s",
                "avg_docling_parse_per_page_s",
            ),
            ("Chunking", "avg_chunk_per_pdf_s", "avg_chunk_per_page_s"),
            ("Embedding*", "avg_embed_per_pdf_s", "avg_embed_per_page_s"),
            (
                "Milvus write",
                "avg_milvus_write_per_pdf_s",
                "avg_milvus_write_per_page_s",
            ),
        ]
        for label, pdf_key, page_key in stages:
            print(f"{label:<20} {metrics[pdf_key]:>12.3f} {metrics[page_key]:>14.4f}")
        print(f"{'─' * 20} {'─' * 12} {'─' * 14}")
        print(
            f"{'Total':<20} {metrics['avg_total_per_pdf_s']:>12.3f} "
            f"{metrics['avg_total_per_page_s']:>14.4f}"
        )
        print("\n* Embedding timing is approximate (vLLM batches internally)")

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
    if EMBEDDING_MODE not in ("local", "service"):
        raise ValueError(
            f"EMBEDDING_MODE must be 'local' or 'service', got: {EMBEDDING_MODE!r}"
        )
    print(f"Embedding mode: {EMBEDDING_MODE} ({EMBEDDING_MODEL}, dim={EMBEDDING_DIM})")

    _configure_ray_context()

    input_full_path = os.path.join(PVC_MOUNT_PATH, INPUT_PATH)
    target_blocks = max(1, NUM_ACTORS * REPARTITION_FACTOR)

    paths = _collect_pdf_paths(input_full_path, NUM_FILES)

    if not paths:
        print(f"No PDFs found under {input_full_path}")
        return

    print(f"Processing {len(paths)} PDFs")
    ds = ray.data.from_items([{"path": p} for p in paths])
    ds = ds.repartition(num_blocks=target_blocks, shuffle=False)

    setup_milvus_collection()

    metrics = _run_pipeline(ds)
    _print_report(metrics)


if __name__ == "__main__":
    ray.init(ignore_reinit_error=True)
    run()
