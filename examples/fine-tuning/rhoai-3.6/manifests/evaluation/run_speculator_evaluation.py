#!/usr/bin/env python3
"""Run a temporary Eagle3 vLLM server and evaluate it without KFP.

Run this in a CUDA/GPU environment where the verifier, draft checkpoint, and
output directory are accessible as filesystem paths. For OpenShift, mount the
PVC into the pod first; this program does not create or mount PVCs.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import site
import subprocess
import sys
import sysconfig
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

# Keep the evaluator files and provenance helper on the same, immutable
# Speculators release commit.
EVALUATOR_REF = "1c800f2b053bcd538fc11bf49ec843d4dfa81a95"
EVALUATOR_FILES = ("evaluate.py", "perf_utils.py", "mrcr.py")
EVALUATOR_SHA256 = {
    "evaluate.py": "0fb2aef469ec489eb9b8cc137a98f305d32f6b6bf66e2254f774927d1c47438b",
    "perf_utils.py": "e6a0e2b1a58a62e7daf4533854a5004e5bf35e91f5edf320af66e1a2630413bd",
    "mrcr.py": "cf8d3c68d94e73eff21f14d20bf0659103d17d648e6fd23f949c4fe72f288a15",
    "provenance.py": "2ddd7c8c10eaaca2678552979c848f985eb146b35ae14062f9589151d4ee020a",
}

# Evaluation settings. Model and output paths are supplied through required Job
# environment variables so customers do not need to edit this file.
USER_CONFIG = {
    # The Job mounts the user-selected PVC at this stable path. These paths are
    # relative to the PVC root; the PVC name belongs only in the Job YAML.
    "pvc_mount_root": "/mnt/persistent",
    "verifier_model": None,
    "draft_model": None,
    "output_dir": None,
    "dataset": "RedHatAI/speculator_benchmarks",
    "subsets": (
        "HumanEval,math_reasoning,qa,question,rag,summarization,"
        "tool_call,translation,writing"
    ),
    "mode": "sweep",
    "max_requests": 200,
    "max_concurrency": 128,
    "max_tokens": 4096,
    "temperature": 1.0,
    "num_speculative_tokens": 5,
    "gpu_memory_utilization": 0.9,
    "port": 8000,
    "startup_timeout_seconds": 900,
    "evaluation_timeout_seconds": 7200,
    "trust_remote_code": False,
}


def _required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable is not set: {name}")
    return value


def _ensure_guidellm() -> None:
    """Install the pinned GuideLLM CLI if it is not already available."""
    if shutil.which("guidellm"):
        return

    print("Installing GuideLLM (guidellm~=0.7.1)...", flush=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "guidellm~=0.7.1",
        ],
        check=True,
    )

    script_dirs = {
        sysconfig.get_path("scripts"),
        str(Path(site.getuserbase()) / "bin"),
    }
    os.environ["PATH"] = os.pathsep.join(
        [directory for directory in script_dirs if directory]
        + [os.environ.get("PATH", "")]
    )
    if shutil.which("guidellm") is None:
        raise RuntimeError(
            "GuideLLM was installed, but its command is not on PATH. "
            "Restart the notebook kernel or install guidellm~=0.7.1 in the environment."
        )


def _download_file(url: str, destination: Path, expected_sha256: str) -> None:
    """Download and verify a pinned evaluator file, retrying transient errors."""
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            request = Request(url, headers={"User-Agent": "speculator-evaluation"})
            with urlopen(request, timeout=60) as response:  # noqa: S310
                content = response.read()
            if not content:
                raise RuntimeError(f"Downloaded an empty file from {url}")
            actual_sha256 = hashlib.sha256(content).hexdigest()
            if actual_sha256 != expected_sha256:
                raise RuntimeError(
                    f"SHA-256 mismatch for {url}: expected {expected_sha256}, "
                    f"got {actual_sha256}"
                )
            destination.write_bytes(content)
            return
        except (URLError, TimeoutError, OSError, RuntimeError) as error:
            last_error = error
            if attempt < 3:
                time.sleep(attempt)

    raise RuntimeError(f"Could not download {url}: {last_error}")


def _prepare_evaluator(work_dir: Path) -> tuple[Path, Path]:
    """Download the pinned evaluator and its provenance compatibility module."""
    evaluator_dir = work_dir / "scripts" / "evaluate"
    evaluator_dir.mkdir(parents=True, exist_ok=True)

    for filename in EVALUATOR_FILES:
        url = (
            f"https://raw.githubusercontent.com/vllm-project/speculators/"
            f"{EVALUATOR_REF}/scripts/evaluate/{filename}"
        )
        _download_file(url, evaluator_dir / filename, EVALUATOR_SHA256[filename])

    compat_dir = work_dir / "compat"
    compat_package = compat_dir / "speculators"
    compat_package.mkdir(parents=True, exist_ok=True)
    (compat_package / "__init__.py").write_text(
        '"""Compatibility namespace for pinned evaluator provenance."""\n'
    )
    provenance_url = (
        f"https://raw.githubusercontent.com/vllm-project/speculators/"
        f"{EVALUATOR_REF}/src/speculators/provenance.py"
    )
    _download_file(
        provenance_url,
        compat_package / "provenance.py",
        EVALUATOR_SHA256["provenance.py"],
    )
    return evaluator_dir / "evaluate.py", compat_dir


def _resolve_storage_paths(config: dict[str, object]) -> tuple[Path, Path, Path]:
    """Resolve ``<pvc-name>/<path>`` values under the configured workbench root."""
    mount_root = Path(str(config["pvc_mount_root"])).expanduser().resolve()
    if not mount_root.is_dir():
        raise FileNotFoundError(f"Configured PVC mount root not found: {mount_root}")

    def resolve(path: object) -> Path:
        value = str(path).strip()
        if value.startswith("pvc://"):
            raise ValueError(
                "Use a path relative to pvc_mount_root (for example, "
                "'speculator/run-01/checkpoints/checkpoint_best'). "
                "Set the PVC claim name only in the Job YAML."
            )
        relative_path = Path(value).expanduser()
        if relative_path.is_absolute():
            return relative_path.resolve()
        return (mount_root / relative_path).resolve()

    return (
        resolve(config["verifier_model"]),
        resolve(config["draft_model"]),
        resolve(config["output_dir"]),
    )


def _wait_for_server(process: subprocess.Popen[bytes], url: str, timeout: int) -> None:
    """Wait for vLLM health, or fail if startup exits or times out."""
    deadline = time.monotonic() + timeout
    health_url = f"{url}/health"

    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"vLLM exited during startup with code {process.returncode}; "
                "check the container logs."
            )
        try:
            with urlopen(health_url, timeout=5) as response:  # noqa: S310
                if response.status == 200:
                    return
            time.sleep(2)
        except (URLError, TimeoutError, OSError):
            time.sleep(2)

    raise TimeoutError(f"vLLM did not become healthy within {timeout} seconds")


def _stop_server(process: subprocess.Popen[bytes]) -> None:
    """Stop vLLM and its worker processes."""
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def main() -> int:
    config = {
        **USER_CONFIG,
        "verifier_model": _required_environment("SPECULATOR_VERIFIER_MODEL"),
        "draft_model": _required_environment("SPECULATOR_DRAFT_MODEL"),
        "output_dir": _required_environment("SPECULATOR_OUTPUT_DIR"),
    }

    vllm = shutil.which("vllm")
    if vllm is None:
        raise RuntimeError("The environment must have the vLLM CLI installed.")
    _ensure_guidellm()

    try:
        import numpy  # noqa: F401
    except ImportError as error:
        raise RuntimeError("NumPy is required by the Speculators evaluator.") from error

    verifier_model, draft_model, output_dir = _resolve_storage_paths(config)
    if not verifier_model.is_dir():
        raise FileNotFoundError(f"Verifier model directory not found: {verifier_model}")
    if not draft_model.is_dir():
        raise FileNotFoundError(f"Draft model directory not found: {draft_model}")
    if (
        config["max_requests"] < 1
        or config["max_tokens"] < 1
        or config["num_speculative_tokens"] < 1
    ):
        raise ValueError(
            "max-requests, max-tokens, and num-speculative-tokens must be positive"
        )
    if not 0 < config["gpu_memory_utilization"] <= 1:
        raise ValueError("gpu-memory-utilization must be greater than 0 and at most 1")

    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = Path(config["dataset"]).expanduser()
    subsets = config["subsets"] or ("local" if dataset_path.exists() else "HumanEval")

    with tempfile.TemporaryDirectory(prefix="speculator-eval-") as temporary_dir:
        evaluator_script, compat_dir = _prepare_evaluator(Path(temporary_dir))
        evaluator_environment = os.environ.copy()
        existing_pythonpath = evaluator_environment.get("PYTHONPATH", "")
        evaluator_environment["PYTHONPATH"] = os.pathsep.join(
            path for path in (str(compat_dir), existing_pythonpath) if path
        )
        dataset_path = Path(str(config["dataset"])).expanduser()
        if not dataset_path.exists():
            # The default dataset is on Hugging Face Hub. Some serving images
            # set offline flags globally; clear them for the evaluator process.
            for variable in (
                "HF_HUB_OFFLINE",
                "HF_DATASETS_OFFLINE",
                "TRANSFORMERS_OFFLINE",
            ):
                evaluator_environment[variable] = "0"

        speculative_config = json.dumps({
            "method": "eagle3",
            "model": str(draft_model),
            "draft_tensor_parallel_size": 1,
            "num_speculative_tokens": config["num_speculative_tokens"],
        })
        vllm_command = [
            vllm,
            "serve",
            str(verifier_model),
            "--host",
            "127.0.0.1",
            "--port",
            str(config["port"]),
            "--gpu-memory-utilization",
            str(config["gpu_memory_utilization"]),
            "--speculative-config",
            speculative_config,
        ]
        if config["trust_remote_code"]:
            vllm_command.append("--trust-remote-code")

        server_url = f"http://127.0.0.1:{config['port']}"
        print("Starting temporary vLLM server:", " ".join(vllm_command), flush=True)
        server = subprocess.Popen(vllm_command, start_new_session=True)
        try:
            _wait_for_server(
                server,
                server_url,
                config["startup_timeout_seconds"],
            )
            print("vLLM is ready; running evaluation.", flush=True)
            evaluate_command = [
                sys.executable,
                str(evaluator_script),
                config["mode"],
                "--target",
                f"{server_url}/v1",
                "--dataset",
                config["dataset"],
                "--subsets",
                subsets,
                "--output-dir",
                str(output_dir),
                "--max-requests",
                str(config["max_requests"]),
                "--max-concurrency",
                str(config["max_concurrency"]),
                "--gen-kwargs",
                json.dumps({
                    "temperature": config["temperature"],
                    "max_tokens": config["max_tokens"],
                }),
            ]
            subprocess.run(
                evaluate_command,
                check=True,
                env=evaluator_environment,
                timeout=config["evaluation_timeout_seconds"],
            )
        finally:
            _stop_server(server)

    print(f"Evaluation results saved under: {output_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        RuntimeError,
        TimeoutError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"Evaluation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
