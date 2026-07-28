"""Ray Data + Docling PDF processing script.

This script is submitted to a Ray cluster (via RayCluster job submission or
RayJob CRD) and converts PDF files to Markdown and JSON using Docling.

All parameters are read from environment variables so the script has no
hardcoded values.  See the companion notebooks for how these variables are
set at submission time.
"""

import glob
import multiprocessing as mp
import os
import queue
import subprocess
import time
from pathlib import Path
from typing import Dict, List

import pandas as pd
import ray

# ---------------------------------------------------------------------------
# Parameters (passed as environment variables from the job submission)
# ---------------------------------------------------------------------------
MIN_ACTORS = int(os.environ.get("MIN_ACTORS", "8"))
MAX_ACTORS = int(os.environ.get("MAX_ACTORS", "24"))
CPUS_PER_ACTOR = int(os.environ.get("CPUS_PER_ACTOR", "4"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "4"))
REPARTITION_FACTOR = int(os.environ.get("REPARTITION_FACTOR", "40"))

PVC_MOUNT_PATH = os.environ.get("PVC_MOUNT_PATH", "/mnt/data")
INPUT_PATH = os.environ.get("INPUT_PATH", "input/pdfs/10000")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "output")
WRITE_JSON = os.environ.get("WRITE_JSON", "1").lower() in ("1", "true", "yes")
NUM_FILES = int(os.environ.get("NUM_FILES", "10000"))

FILE_TIMEOUT = int(os.environ.get("FILE_TIMEOUT", "600"))
MAX_ERRORED_BLOCKS = int(os.environ.get("MAX_ERRORED_BLOCKS", "100"))


def _mkdir(path: Path):
    subprocess.run(["mkdir", "-p", "-m", "777", str(path)], check=False)


def _write(path, data, retries=3, delay=0.5):
    for attempt in range(retries):
        try:
            with open(path, "wb") as f:
                f.write(data)
            return
        except OSError:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise


# ---------------------------------------------------------------------------
# Converter subprocess
# ---------------------------------------------------------------------------


def _converter_worker(req_q, res_q, cpus_per_actor, output_base_str, write_json):
    """Long-running subprocess that owns the DocumentConverter.

    Initialises Docling once, then loops on a request queue converting one
    file at a time.  Output files (markdown, JSON) are written directly
    from this process to avoid passing large data through the queue.
    """
    os.environ["OMP_NUM_THREADS"] = str(cpus_per_actor)
    os.environ["MKL_NUM_THREADS"] = str(cpus_per_actor)

    import io

    from docling.datamodel.base_models import DocumentStream, InputFormat
    from docling.datamodel.pipeline_options import (
        AcceleratorOptions,
        PdfPipelineOptions,
    )
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=cpus_per_actor,
        device="cpu",
    )
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    output_base = Path(output_base_str)
    markdown_dir = output_base / "markdown"
    json_dir = output_base / "json" if write_json else None

    if write_json:
        import orjson

    # Signal parent that initialisation is complete
    res_q.put(("ready",))

    while True:
        msg = req_q.get()
        if msg is None:
            break

        file_path = msg
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            file_size = len(file_bytes)
            if file_size == 0:
                res_q.put(("error", 0, 0, 0.0, 0.0, "File empty"))
                continue

            fname = os.path.basename(file_path)
            fname_base = fname.rsplit(".", 1)[0]

            stream = DocumentStream(name=fname, stream=io.BytesIO(file_bytes))
            result = converter.convert(stream)
            doc = result.document

            pages = getattr(doc, "pages", None)
            page_count = len(pages) if pages is not None else 0

            md_bytes = doc.export_to_markdown().encode("utf-8")
            md_kb = round(len(md_bytes) / 1024, 2)
            _write(markdown_dir / f"{fname_base}.md", md_bytes)

            js_kb = 0.0
            if write_json and json_dir is not None:
                json_bytes = orjson.dumps(doc.export_to_dict())
                js_kb = round(len(json_bytes) / 1024, 2)
                _write(json_dir / f"{fname_base}.json", json_bytes)

            res_q.put(("success", page_count, file_size, md_kb, js_kb, ""))

        except Exception as e:
            res_q.put(("error", 0, 0, 0.0, 0.0, str(e)[:150]))


# ---------------------------------------------------------------------------
# Ray Data actor
# ---------------------------------------------------------------------------


class DoclingProcessor:
    """Thin actor that delegates conversion to a subprocess."""

    def __init__(self):
        import socket

        self.hostname = socket.gethostname()

        self.output_base = Path(PVC_MOUNT_PATH) / OUTPUT_PATH
        _mkdir(self.output_base)
        _mkdir(self.output_base / "markdown")
        if WRITE_JSON:
            _mkdir(self.output_base / "json")

        self._start_worker()
        print(
            f"[{self.hostname}] DoclingProcessor ready "
            f"(converter pid={self._worker.pid}, timeout={FILE_TIMEOUT}s)"
        )

    def _start_worker(self):
        self._req_q = mp.Queue()
        self._res_q = mp.Queue()
        self._worker = mp.Process(
            target=_converter_worker,
            args=(
                self._req_q,
                self._res_q,
                CPUS_PER_ACTOR,
                str(self.output_base),
                WRITE_JSON,
            ),
            daemon=True,
        )
        self._worker.start()
        msg = self._res_q.get(timeout=300)  # Wait up to 5 min for model loading
        assert msg[0] == "ready"

    def _restart_worker(self):
        """Kill the hung subprocess and start a fresh one."""
        if self._worker.is_alive():
            self._worker.terminate()
            self._worker.join(timeout=5)
            if self._worker.is_alive():
                self._worker.kill()
                self._worker.join()
        while True:
            try:
                self._res_q.get_nowait()
            except queue.Empty:
                break
        self._start_worker()
        print(f"[{self.hostname}] Restarted converter (new pid={self._worker.pid})")

    def __call__(self, batch: Dict[str, List]) -> Dict[str, List]:
        path_list = batch["path"]

        filenames, statuses, page_counts, errors = [], [], [], []
        docling_durations, file_sizes_mb = [], []
        output_md_kb, output_json_kb = [], []
        pages_per_second, actor_hosts = [], []

        for file_path in path_list:
            fname = os.path.basename(file_path)
            t0 = time.time()

            status, error_msg = "success", ""
            page_count = 0
            file_size_mb, md_kb, js_kb = 0.0, 0.0, 0.0

            self._req_q.put(str(file_path))

            try:
                result = self._res_q.get(timeout=FILE_TIMEOUT)
                status_str, page_count, file_size, md_kb, js_kb, error_msg = result
                file_size_mb = (
                    round(file_size / (1024 * 1024), 3) if file_size > 0 else 0.0
                )
                if status_str != "success":
                    status = "error"
            except queue.Empty:
                status = "timeout"
                error_msg = f"Timed out after {FILE_TIMEOUT}s"
                self._restart_worker()

            docling_duration = round(time.time() - t0, 3)

            filenames.append(fname)
            statuses.append(status)
            page_counts.append(int(page_count))
            errors.append(error_msg)
            docling_durations.append(docling_duration)
            file_sizes_mb.append(file_size_mb)
            output_md_kb.append(float(md_kb))
            output_json_kb.append(float(js_kb))
            pps = (
                round(page_count / docling_duration, 2)
                if docling_duration > 0 and page_count > 0
                else 0.0
            )
            pages_per_second.append(pps)
            actor_hosts.append(self.hostname)

        return {
            "filename": filenames,
            "status": statuses,
            "page_count": page_counts,
            "error": errors,
            "docling_duration_s": docling_durations,
            "file_size_mb": file_sizes_mb,
            "output_md_kb": output_md_kb,
            "output_json_kb": output_json_kb,
            "pages_per_second": pages_per_second,
            "actor_hostname": actor_hosts,
        }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def ray_data_process():
    input_full_path = os.path.join(PVC_MOUNT_PATH, INPUT_PATH)

    pdf_paths = glob.glob(f"{input_full_path}/**/*.pdf", recursive=True)[:NUM_FILES]
    print(f"Found {len(pdf_paths)} PDFs to process.")

    target_blocks = MAX_ACTORS * REPARTITION_FACTOR
    ds = ray.data.from_pandas(pd.DataFrame({"path": pdf_paths}))
    ds = ds.repartition(target_blocks)
    print(
        f"Repartitioned into {target_blocks} blocks "
        f"(~{len(pdf_paths) // target_blocks} files/block) "
        f"for {MAX_ACTORS} max actors."
    )
    print(
        f"Per-file timeout: {FILE_TIMEOUT}s  |  "
        f"max_errored_blocks: {MAX_ERRORED_BLOCKS}"
    )

    results_ds = ds.map_batches(
        DoclingProcessor,
        compute=ray.data.ActorPoolStrategy(
            min_size=MIN_ACTORS,
            max_size=MAX_ACTORS,
        ),
        batch_size=BATCH_SIZE,
        batch_format="numpy",
        num_cpus=CPUS_PER_ACTOR,
    )

    # ------------------------------------------------------------------
    # Collect results and print performance report
    # ------------------------------------------------------------------
    start_time = time.time()
    success_count = error_count = timeout_count = 0
    total_pages = 0
    total_docling_time = 0.0
    total_file_size_mb = 0.0
    total_md_kb = 0.0
    total_json_kb = 0.0
    actor_distribution = {}
    errors_list = []

    for batch in results_ds.iter_batches(
        batch_size=200,
        prefetch_batches=2,
        batch_format="numpy",
    ):
        n = len(batch["filename"])
        for i in range(n):
            status = str(batch["status"][i])
            if status == "success":
                success_count += 1
            elif status == "timeout":
                timeout_count += 1
                errors_list.append((batch["filename"][i], str(batch["error"][i])))
            else:
                error_count += 1
                errors_list.append((batch["filename"][i], str(batch["error"][i])))

            total_pages += int(batch["page_count"][i])
            total_docling_time += float(batch["docling_duration_s"][i])
            total_file_size_mb += float(batch["file_size_mb"][i])
            total_md_kb += float(batch["output_md_kb"][i])
            total_json_kb += float(batch["output_json_kb"][i])

            actor = str(batch["actor_hostname"][i])
            actor_distribution[actor] = actor_distribution.get(actor, 0) + 1

    wall_clock = time.time() - start_time
    total_files = success_count + error_count + timeout_count
    error_rate = (error_count / total_files * 100) if total_files else 0.0
    timeout_rate = (timeout_count / total_files * 100) if total_files else 0.0

    print("\n" + "=" * 70)
    print("PERFORMANCE REPORT")
    print("=" * 70)
    print(f"Actors:         {MIN_ACTORS}..{MAX_ACTORS}  | CPUs/actor: {CPUS_PER_ACTOR}")
    print(
        f"Blocks:         {target_blocks}  "
        f"(~{len(pdf_paths) // target_blocks} files/block)"
    )
    print(f"File timeout:   {FILE_TIMEOUT}s")
    print("\n--- Results ---")
    print(f"Total:          {total_files}")
    print(f"Success:        {success_count} ({100 - error_rate - timeout_rate:.1f}%)")
    print(f"Errors:         {error_count} ({error_rate:.1f}%)")
    print(f"Timeouts:       {timeout_count} ({timeout_rate:.1f}%)")
    print(f"Total pages:    {total_pages}")
    print("\n--- Throughput ---")
    print(f"Wall clock:     {wall_clock:.1f}s")
    if wall_clock > 0:
        print(f"Files/second:   {success_count / wall_clock:.2f}")
        print(f"Pages/second:   {total_pages / wall_clock:.2f}")
    print("\n--- Actor Distribution ---")
    for actor, count in sorted(actor_distribution.items()):
        pct = count / total_files * 100 if total_files else 0.0
        print(f"  {actor}: {count} files ({pct:.1f}%)")
    if errors_list:
        print("\n--- Errors & Timeouts (first 10) ---")
        for fname, err in errors_list[:10]:
            print(f"  {fname}: {err[:80]}")
    print("=" * 70)


if __name__ == "__main__":
    ray.init(ignore_reinit_error=True)
    ctx = ray.data.DataContext.get_current()
    ctx.enable_rich_progress_bars = True
    ctx.use_ray_tqdm = False
    ctx.max_errored_blocks = MAX_ERRORED_BLOCKS
    ray_data_process()
