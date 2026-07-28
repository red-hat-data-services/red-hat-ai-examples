#!/usr/bin/env python3
"""
Ray Data + Docling Pipeline Configuration Calculator

Derives optimal configuration parameters for a Ray Data pipeline that uses
Docling actor pools to convert PDFs to Markdown/JSON on a Kubernetes cluster.

Usage:
    python configure.py --interactive
    python configure.py --num-files 10000 --num-workers 8 --worker-cpus 8 --worker-memory 16
"""

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from typing import List

# ─── Constants & Defaults ────────────────────────────────────────────────────

OVERHEAD_CPUS = 2  # CPUs reserved per worker for Ray overhead (raylet, object store)
HEAD_RAY_NUM_CPUS = (
    0  # Ray-advertised CPUs on head (always 0 — no actors scheduled there)
)
DEFAULT_HEAD_CPUS = 4  # Kubernetes CPU allocation for the head pod
DEFAULT_HEAD_MEMORY_GB = 8  # Kubernetes memory allocation for the head pod
MIN_MEMORY_PER_ACTOR_GB = 4  # Docling needs at least 4 GB per actor
DEFAULT_BATCH_SIZE = 4  # Files per map_batches call
DEFAULT_REPARTITION_FACTOR = 40  # Blocks = max_actors × this factor
DEFAULT_OBJECT_STORE_PROPORTION = 0.1  # Low because we pass paths, not bytes
DEFAULT_CPUS_PER_ACTOR = 2  # CPUs allocated to each Docling actor

# Estimated seconds per file for time projections
AVG_SECONDS_FAST = 5  # Small/simple PDFs
AVG_SECONDS_SLOW = 20  # Large/complex PDFs with tables


# ─── Data Structures ─────────────────────────────────────────────────────────


@dataclass
class PipelineConfig:
    """All input and derived configuration for the pipeline."""

    # --- Inputs ---
    num_files: int = 10000
    num_workers: int = 8
    worker_cpus: int = 8
    worker_memory_gb: int = 16
    head_cpus: int = DEFAULT_HEAD_CPUS
    head_memory_gb: int = DEFAULT_HEAD_MEMORY_GB
    cpus_per_actor: int = DEFAULT_CPUS_PER_ACTOR
    do_ocr: bool = False
    do_table_structure: bool = True
    batch_size: int = DEFAULT_BATCH_SIZE
    repartition_factor: int = DEFAULT_REPARTITION_FACTOR
    object_store_proportion: float = DEFAULT_OBJECT_STORE_PROPORTION

    # --- Derived (computed by calculate()) ---
    schedulable_cpus: int = 0
    actors_per_worker: int = 0
    max_actors: int = 0
    min_actors: int = 0
    object_store_memory_gb: float = 0.0
    memory_per_actor_gb: float = 0.0
    total_blocks: int = 0
    files_per_block: float = 0.0
    batches_per_block: int = 0
    total_cluster_cpus: int = 0
    total_cluster_memory_gb: int = 0
    estimated_time_fast_s: float = 0.0
    estimated_time_slow_s: float = 0.0

    # --- Validation messages ---
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ─── Core Logic ──────────────────────────────────────────────────────────────


def calculate(cfg: PipelineConfig) -> PipelineConfig:
    """Apply all equations to derive configuration values from inputs."""

    # CPUs available for actors on each worker (reserve OVERHEAD_CPUS for raylet etc.)
    cfg.schedulable_cpus = cfg.worker_cpus - OVERHEAD_CPUS

    # How many actors fit on one worker
    cfg.actors_per_worker = cfg.schedulable_cpus // cfg.cpus_per_actor

    # Cluster-wide actor pool bounds
    cfg.max_actors = cfg.num_workers * cfg.actors_per_worker
    cfg.min_actors = max(cfg.num_workers, cfg.max_actors // 3)

    # Memory carving: object store gets a slice, rest is split among actors
    cfg.object_store_memory_gb = cfg.worker_memory_gb * cfg.object_store_proportion
    if cfg.actors_per_worker > 0:
        cfg.memory_per_actor_gb = (
            cfg.worker_memory_gb - cfg.object_store_memory_gb
        ) / cfg.actors_per_worker
    else:
        cfg.memory_per_actor_gb = 0.0

    # Data partitioning
    cfg.total_blocks = cfg.max_actors * cfg.repartition_factor
    cfg.files_per_block = (
        cfg.num_files / cfg.total_blocks if cfg.total_blocks > 0 else cfg.num_files
    )
    # Each block is processed in batches of batch_size; this is the scheduling
    # granularity within a block — Ray can only preempt between batches.
    cfg.batches_per_block = (
        math.ceil(cfg.files_per_block / cfg.batch_size) if cfg.batch_size > 0 else 0
    )

    # Cluster totals (head + workers)
    cfg.total_cluster_cpus = cfg.head_cpus + (cfg.num_workers * cfg.worker_cpus)
    cfg.total_cluster_memory_gb = cfg.head_memory_gb + (
        cfg.num_workers * cfg.worker_memory_gb
    )

    # Time estimates
    if cfg.max_actors > 0:
        cfg.estimated_time_fast_s = (cfg.num_files * AVG_SECONDS_FAST) / cfg.max_actors
        cfg.estimated_time_slow_s = (cfg.num_files * AVG_SECONDS_SLOW) / cfg.max_actors
    else:
        cfg.estimated_time_fast_s = float("inf")
        cfg.estimated_time_slow_s = float("inf")

    return cfg


def validate(cfg: PipelineConfig) -> PipelineConfig:
    """Check constraints and populate errors/warnings."""
    cfg.errors = []
    cfg.warnings = []

    if cfg.schedulable_cpus < cfg.cpus_per_actor:
        cfg.errors.append(
            f"Not enough schedulable CPUs: {cfg.schedulable_cpus} available "
            f"(worker_cpus={cfg.worker_cpus} - {OVERHEAD_CPUS} overhead) "
            f"but cpus_per_actor={cfg.cpus_per_actor}"
        )

    if cfg.memory_per_actor_gb < MIN_MEMORY_PER_ACTOR_GB and cfg.actors_per_worker > 0:
        cfg.errors.append(
            f"Memory per actor too low: {cfg.memory_per_actor_gb:.1f} GB "
            f"(minimum {MIN_MEMORY_PER_ACTOR_GB} GB). "
            f"Increase worker_memory or reduce actors_per_worker."
        )

    if cfg.files_per_block > 50:
        cfg.warnings.append(
            f"Large blocks: ~{cfg.files_per_block:.0f} files/block. "
            f"One slow document will stall the whole block. "
            f"Consider increasing repartition_factor."
        )

    if cfg.files_per_block < 1 and cfg.num_files > 0:
        cfg.warnings.append(
            f"Over-partitioned: ~{cfg.files_per_block:.2f} files/block. "
            f"Many blocks will be empty. "
            f"Consider reducing repartition_factor or max_actors."
        )

    if cfg.do_ocr and cfg.memory_per_actor_gb < 6:
        cfg.warnings.append(
            f"OCR enabled with only {cfg.memory_per_actor_gb:.1f} GB per actor. "
            f"OCR models need ~6+ GB. Risk of OOM kills."
        )

    if cfg.max_actors > cfg.num_files and cfg.num_files > 0:
        cfg.warnings.append(
            f"More actors ({cfg.max_actors}) than files ({cfg.num_files}). "
            f"Some actors will be idle. Consider fewer workers."
        )

    if cfg.batch_size > cfg.files_per_block and cfg.files_per_block > 0:
        cfg.warnings.append(
            f"Batch size ({cfg.batch_size}) exceeds files per block "
            f"(~{cfg.files_per_block:.1f}). Batches will be partially filled. "
            f"Reduce batch_size to {max(1, int(cfg.files_per_block))} "
            f"or lower repartition_factor."
        )

    return cfg


# ─── Output Formatters ───────────────────────────────────────────────────────


def _fmt_time(seconds: float) -> str:
    """Format seconds as a human-readable duration."""
    if seconds == float("inf"):
        return "N/A"
    minutes = seconds / 60
    if minutes < 60:
        return f"~{minutes:.0f} min"
    hours = minutes / 60
    return f"~{hours:.1f} hr"


def format_summary(cfg: PipelineConfig) -> str:
    """Formatted table summarizing the configuration."""
    lines = []
    lines.append("=" * 70)
    lines.append("RAY DATA + DOCLING PIPELINE CONFIGURATION")
    lines.append("=" * 70)

    # Cluster
    lines.append("")
    lines.append("--- Cluster ---")
    lines.append(
        f"Workers:           {cfg.num_workers} x ({cfg.worker_cpus} CPUs, "
        f"{cfg.worker_memory_gb} GB)"
    )
    lines.append(
        f"Schedulable CPUs:  {cfg.schedulable_cpus} per worker "
        f"({OVERHEAD_CPUS} reserved for overhead)"
    )
    lines.append(
        f"Head node:         {cfg.head_cpus} CPUs, {cfg.head_memory_gb} GB "
        f"(Ray sees {HEAD_RAY_NUM_CPUS} CPUs — no actors scheduled)"
    )
    lines.append(
        f"Total:             {cfg.total_cluster_cpus} CPUs, "
        f"{cfg.total_cluster_memory_gb} GB"
    )

    # Actors
    lines.append("")
    lines.append("--- Actors ---")
    lines.append(f"Actors per worker: {cfg.actors_per_worker}")
    lines.append(
        f"Actor pool:        {cfg.min_actors}..{cfg.max_actors}  "
        f"({cfg.cpus_per_actor} CPUs, ~{cfg.memory_per_actor_gb:.1f} GB each)"
    )
    lines.append(
        f"Object store:      {cfg.object_store_memory_gb:.1f} GB per worker "
        f"({cfg.object_store_proportion * 100:.0f}%)"
    )

    # Docling
    lines.append("")
    lines.append("--- Docling ---")
    lines.append(f"OCR:               {'Enabled' if cfg.do_ocr else 'Disabled'}")
    lines.append(
        f"Table structure:   {'Enabled' if cfg.do_table_structure else 'Disabled'}"
    )

    # Data Partitioning
    lines.append("")
    lines.append("--- Data Partitioning ---")
    lines.append(f"Files:             {cfg.num_files:,}")
    lines.append(
        f"Blocks:            {cfg.total_blocks:,}  "
        f"(~{cfg.files_per_block:.0f} files/block)"
    )
    lines.append(f"Batch size:        {cfg.batch_size}")
    lines.append(f"Batches per block: {cfg.batches_per_block}")
    lines.append(f"Repartition factor:{cfg.repartition_factor}")

    # Estimated Time
    lines.append("")
    lines.append("--- Estimated Time ---")
    lines.append(
        f"Fast ({AVG_SECONDS_FAST}s/file):    {_fmt_time(cfg.estimated_time_fast_s)}"
    )
    lines.append(
        f"Slow ({AVG_SECONDS_SLOW}s/file):   {_fmt_time(cfg.estimated_time_slow_s)}"
    )

    # Errors & Warnings
    if cfg.errors:
        lines.append("")
        lines.append("--- ERRORS ---")
        for err in cfg.errors:
            lines.append(f"  ERROR: {err}")

    if cfg.warnings:
        lines.append("")
        lines.append("--- Warnings ---")
        for w in cfg.warnings:
            lines.append(f"  WARNING: {w}")

    lines.append("=" * 70)
    return "\n".join(lines)


def format_env_vars(cfg: PipelineConfig) -> str:
    """Environment variables for Ray job submission."""
    lines = [
        "",
        "--- Environment Variables (for runtime_env / env_vars) ---",
        "",
        f'    "NUM_FILES": "{cfg.num_files}",',
        f'    "MIN_ACTORS": "{cfg.min_actors}",',
        f'    "MAX_ACTORS": "{cfg.max_actors}",',
        f'    "CPUS_PER_ACTOR": "{cfg.cpus_per_actor}",',
        f'    "BATCH_SIZE": "{cfg.batch_size}",',
        f'    "REPARTITION_FACTOR": "{cfg.repartition_factor}",',
        f'    "OMP_NUM_THREADS": "{cfg.cpus_per_actor}",',
        f'    "MKL_NUM_THREADS": "{cfg.cpus_per_actor}",',
        f'    "RAY_DEFAULT_OBJECT_STORE_MEMORY_PROPORTION": "{cfg.object_store_proportion}",',
        "",
    ]
    return "\n".join(lines)


def format_cluster_config(cfg: PipelineConfig) -> str:
    """CodeFlare SDK ClusterConfiguration snippet."""
    lines = [
        "",
        "--- ClusterConfiguration (CodeFlare SDK) ---",
        "",
        "cluster_config = ClusterConfiguration(",
        '    name="ray-data-processor",',
        '    namespace="ray-docling",',
        "",
        "    # Head node — runs GCS, dashboard, job server (no actors)",
        f"    head_cpu_requests={cfg.head_cpus},",
        f"    head_cpu_limits={cfg.head_cpus},",
        f"    head_memory_requests={cfg.head_memory_gb},",
        f"    head_memory_limits={cfg.head_memory_gb},",
        "",
        f"    # Worker pods — {cfg.schedulable_cpus} CPUs usable by actors + {OVERHEAD_CPUS} for Ray overhead",
        f"    num_workers={cfg.num_workers},",
        f"    worker_cpu_requests={cfg.worker_cpus},",
        f"    worker_cpu_limits={cfg.worker_cpus},",
        f"    worker_memory_requests={cfg.worker_memory_gb},",
        f"    worker_memory_limits={cfg.worker_memory_gb},",
        "",
        '    image="quay.io/cathaloconnor/docling-ray:latest",',
        "",
        "    envs={",
        f'        "RAY_DEFAULT_OBJECT_STORE_MEMORY_PROPORTION": "{cfg.object_store_proportion}",',
        "    },",
        ")",
        "",
    ]
    return "\n".join(lines)


def format_cluster_patch(cfg: PipelineConfig) -> str:
    """JSON patch for oc patch to set rayStartParams (not exposed by CodeFlare SDK)."""
    patch = [
        {
            "op": "replace",
            "path": "/spec/enableInTreeAutoscaling",
            "value": True,
        },
        {
            "op": "add",
            "path": "/spec/workerGroupSpecs/0/rayStartParams/num-cpus",
            "value": str(cfg.schedulable_cpus),
        },
        {
            "op": "add",
            "path": "/spec/headGroupSpec/rayStartParams/num-cpus",
            "value": str(HEAD_RAY_NUM_CPUS),
        },
    ]
    patch_json = json.dumps(patch, indent=2)

    lines = [
        "",
        "--- oc patch command (apply after cluster.apply()) ---",
        "",
        "# The CodeFlare SDK does not expose rayStartParams, so we patch these after cluster.apply():",
        f"#   - Worker num-cpus={cfg.schedulable_cpus} (reserves {OVERHEAD_CPUS} CPUs for Ray overhead)",
        f"#   - Head num-cpus={HEAD_RAY_NUM_CPUS} (prevents actors from scheduling on head)",
        "#   - enableInTreeAutoscaling=true (ensures all workers register)",
        "",
        "oc patch raycluster <CLUSTER_NAME> \\",
        "    -n ray-docling --type json \\",
        f"    -p '{patch_json}'",
        "",
    ]
    return "\n".join(lines)


# ─── Interactive Mode ─────────────────────────────────────────────────────────


def _prompt_int(prompt: str, default: int) -> int:
    """Prompt user for an integer with a default."""
    raw = input(f"{prompt} [{default}]: ").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"  Invalid input, using default: {default}")
        return default


def _prompt_float(prompt: str, default: float) -> float:
    """Prompt user for a float with a default."""
    raw = input(f"{prompt} [{default}]: ").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"  Invalid input, using default: {default}")
        return default


def _prompt_bool(prompt: str, default: bool) -> bool:
    """Prompt user for a yes/no with a default."""
    default_str = "Y/n" if default else "y/N"
    raw = input(f"{prompt} [{default_str}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes", "true", "1")


def interactive_mode() -> dict:
    """Gather configuration inputs interactively."""
    print()
    print("=" * 50)
    print("  Ray Data + Docling Configuration Calculator")
    print("=" * 50)
    print()

    inputs = {}
    inputs["num_files"] = _prompt_int("Number of PDF files", 10000)

    print()
    print("--- Cluster Sizing ---")
    inputs["num_workers"] = _prompt_int("Number of worker pods", 8)
    inputs["worker_cpus"] = _prompt_int("CPUs per worker", 8)
    inputs["worker_memory_gb"] = _prompt_int("Memory per worker (GB)", 16)
    inputs["head_cpus"] = _prompt_int(
        "Head node CPUs (GCS, dashboard, job server)", DEFAULT_HEAD_CPUS
    )
    inputs["head_memory_gb"] = _prompt_int(
        "Head node memory (GB)", DEFAULT_HEAD_MEMORY_GB
    )

    print()
    print("--- Actor Configuration ---")
    inputs["cpus_per_actor"] = _prompt_int(
        "CPUs per Docling actor", DEFAULT_CPUS_PER_ACTOR
    )

    print()
    print("--- Docling Options ---")
    inputs["do_ocr"] = _prompt_bool("Enable OCR", False)
    inputs["do_table_structure"] = _prompt_bool(
        "Enable table structure detection", True
    )

    print()
    print("--- Advanced (press Enter for defaults) ---")
    inputs["batch_size"] = _prompt_int("Batch size", DEFAULT_BATCH_SIZE)
    inputs["repartition_factor"] = _prompt_int(
        "Repartition factor", DEFAULT_REPARTITION_FACTOR
    )
    inputs["object_store_proportion"] = _prompt_float(
        "Object store proportion", DEFAULT_OBJECT_STORE_PROPORTION
    )

    return inputs


# ─── CLI Argument Parsing ─────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Calculate optimal configuration for Ray Data + Docling pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s --interactive
  %(prog)s --num-files 10000 --num-workers 8 --worker-cpus 8 --worker-memory 16
  %(prog)s --num-files 1000 --num-workers 4 --worker-cpus 8 --worker-memory 16 --show-env
""",
    )

    # Mode
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive prompt mode",
    )

    # Inputs
    parser.add_argument(
        "--num-files",
        type=int,
        default=10000,
        help="Number of PDF files (default: 10000)",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=8,
        help="Number of Ray worker pods (default: 8)",
    )
    parser.add_argument(
        "--worker-cpus", type=int, default=8, help="CPUs per worker (default: 8)"
    )
    parser.add_argument(
        "--worker-memory",
        type=int,
        default=16,
        help="Memory per worker in GB (default: 16)",
    )
    parser.add_argument(
        "--head-cpus",
        type=int,
        default=DEFAULT_HEAD_CPUS,
        help=f"Head node CPUs (default: {DEFAULT_HEAD_CPUS})",
    )
    parser.add_argument(
        "--head-memory",
        type=int,
        default=DEFAULT_HEAD_MEMORY_GB,
        help=f"Head node memory in GB (default: {DEFAULT_HEAD_MEMORY_GB})",
    )
    parser.add_argument(
        "--cpus-per-actor",
        type=int,
        default=DEFAULT_CPUS_PER_ACTOR,
        help=f"CPUs per Docling actor (default: {DEFAULT_CPUS_PER_ACTOR})",
    )
    parser.add_argument(
        "--ocr", action="store_true", default=False, help="Enable OCR (default: off)"
    )
    parser.add_argument(
        "--no-table-structure",
        action="store_true",
        default=False,
        help="Disable table structure detection",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Batch size (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--repartition-factor",
        type=int,
        default=DEFAULT_REPARTITION_FACTOR,
        help=f"Repartition factor (default: {DEFAULT_REPARTITION_FACTOR})",
    )
    parser.add_argument(
        "--object-store-proportion",
        type=float,
        default=DEFAULT_OBJECT_STORE_PROPORTION,
        help=f"Object store memory proportion (default: {DEFAULT_OBJECT_STORE_PROPORTION})",
    )

    # Output flags
    parser.add_argument(
        "--show-env", action="store_true", help="Print env vars for job submission"
    )
    parser.add_argument(
        "--show-config", action="store_true", help="Print ClusterConfiguration snippet"
    )
    parser.add_argument(
        "--show-patch", action="store_true", help="Print oc patch command"
    )
    parser.add_argument(
        "--show-all", action="store_true", help="Print all code snippets"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output configuration as JSON"
    )

    return parser.parse_args()


# ─── Main ─────────────────────────────────────────────────────────────────────

BANNER = """\

  ╔══════════════════════════════════════════════════════════════════╗
  ║                         Red Hat AI                               ║
  ║          Ray Data + Docling Configuration Calculator             ║
  ╚══════════════════════════════════════════════════════════════════╝

  This tool provides configuration recommendations for running
  batch PDF processing pipelines with Ray Data and Docling on
  Red Hat OpenShift AI.

  These recommendations are provided on a best-effort basis and
  are intended as a starting point. Actual resource requirements
  may vary depending on your workload characteristics, cluster
  environment, and PDF complexity. Please validate all suggested
  values against your specific deployment before running in
  production.
"""


def main():
    args = parse_args()

    if not args.json:
        print(BANNER)

    if args.interactive:
        inputs = interactive_mode()
    else:
        inputs = {
            "num_files": args.num_files,
            "num_workers": args.num_workers,
            "worker_cpus": args.worker_cpus,
            "worker_memory_gb": args.worker_memory,
            "head_cpus": args.head_cpus,
            "head_memory_gb": args.head_memory,
            "cpus_per_actor": args.cpus_per_actor,
            "do_ocr": args.ocr,
            "do_table_structure": not args.no_table_structure,
            "batch_size": args.batch_size,
            "repartition_factor": args.repartition_factor,
            "object_store_proportion": args.object_store_proportion,
        }

    cfg = PipelineConfig(**inputs)
    cfg = calculate(cfg)
    cfg = validate(cfg)

    if args.json:
        # JSON output mode
        out = {
            "inputs": {
                "num_files": cfg.num_files,
                "num_workers": cfg.num_workers,
                "worker_cpus": cfg.worker_cpus,
                "worker_memory_gb": cfg.worker_memory_gb,
                "head_cpus": cfg.head_cpus,
                "head_memory_gb": cfg.head_memory_gb,
                "cpus_per_actor": cfg.cpus_per_actor,
                "do_ocr": cfg.do_ocr,
                "do_table_structure": cfg.do_table_structure,
                "batch_size": cfg.batch_size,
                "repartition_factor": cfg.repartition_factor,
                "object_store_proportion": cfg.object_store_proportion,
            },
            "derived": {
                "schedulable_cpus": cfg.schedulable_cpus,
                "actors_per_worker": cfg.actors_per_worker,
                "max_actors": cfg.max_actors,
                "min_actors": cfg.min_actors,
                "object_store_memory_gb": cfg.object_store_memory_gb,
                "memory_per_actor_gb": round(cfg.memory_per_actor_gb, 1),
                "total_blocks": cfg.total_blocks,
                "files_per_block": round(cfg.files_per_block, 1),
                "batches_per_block": cfg.batches_per_block,
                "total_cluster_cpus": cfg.total_cluster_cpus,
                "total_cluster_memory_gb": cfg.total_cluster_memory_gb,
                "estimated_time_fast_s": round(cfg.estimated_time_fast_s, 1),
                "estimated_time_slow_s": round(cfg.estimated_time_slow_s, 1),
            },
            "errors": cfg.errors,
            "warnings": cfg.warnings,
        }
        print(json.dumps(out, indent=2))
        if cfg.errors:
            sys.exit(1)
        return

    # Summary always prints
    print()
    print(format_summary(cfg))

    # Optional code snippets
    show_all = args.show_all
    if show_all or args.show_env:
        print(format_env_vars(cfg))
    if show_all or args.show_config:
        print(format_cluster_config(cfg))
    if show_all or args.show_patch:
        print(format_cluster_patch(cfg))

    if cfg.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
