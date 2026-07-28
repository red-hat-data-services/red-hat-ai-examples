"""Query-side helpers for the RAG demo notebooks.

Kept in a separate file so the notebook cells stay short and readable.
Import with: ``from rag_helpers import ask_llm, search_milvus, build_context``
"""

import json
import logging
import subprocess
import time

logger = logging.getLogger("rag-query")


# ---------------------------------------------------------------------------
# KServe deployment helpers
# ---------------------------------------------------------------------------


def deploy_vllm_service(
    name: str,
    namespace: str,
    model_name: str,
    *,
    runtime_image: str = "quay.io/modh/vllm:rhoai-2.20-cuda",
    served_model_name: str | None = None,
    task: str = "generate",
    max_model_len: int = 4096,
    extra_args: list[str] | None = None,
    cpu_requests: str = "2",
    cpu_limits: str = "4",
    memory_requests: str = "8Gi",
    memory_limits: str = "16Gi",
    gpu_count: int = 1,
) -> str:
    """Deploy a vLLM model as a KServe ServingRuntime + InferenceService.

    Works for both LLM (``task="generate"``) and embedding
    (``task="embedding"``) models.  Returns the in-cluster endpoint URL.
    """
    served = served_model_name or model_name
    gpu_res = {"nvidia.com/gpu": str(gpu_count)} if gpu_count > 0 else {}

    args = [
        "--port=8080",
        f"--model={model_name}",
        f"--served-model-name={served}",
        f"--max-model-len={max_model_len}",
        f"--task={task}",
    ]
    if extra_args:
        args.extend(extra_args)

    container = {
        "name": "kserve-container",
        "image": runtime_image,
        "command": ["python", "-m", "vllm.entrypoints.openai.api_server"],
        "args": args,
        "ports": [{"containerPort": 8080, "protocol": "TCP"}],
        "resources": {
            "requests": {"cpu": cpu_requests, "memory": memory_requests, **gpu_res},
            "limits": {"cpu": cpu_limits, "memory": memory_limits, **gpu_res},
        },
    }

    serving_runtime = {
        "apiVersion": "serving.kserve.io/v1alpha1",
        "kind": "ServingRuntime",
        "metadata": {"name": name, "namespace": namespace},
        "spec": {
            "multiModel": False,
            "supportedModelFormats": [{"autoSelect": True, "name": "vLLM"}],
            "containers": [container],
        },
    }

    predictor_spec: dict = {
        "model": {
            "modelFormat": {"name": "vLLM"},
            "runtime": name,
            "resources": {
                "requests": {"cpu": cpu_requests, "memory": memory_requests, **gpu_res},
                "limits": {"cpu": cpu_limits, "memory": memory_limits, **gpu_res},
            },
        },
    }

    isvc = {
        "apiVersion": "serving.kserve.io/v1beta1",
        "kind": "InferenceService",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "annotations": {"serving.kserve.io/deploymentMode": "RawDeployment"},
        },
        "spec": {"predictor": predictor_spec},
    }

    for resource in [serving_runtime, isvc]:
        kind = resource["kind"]
        res_json = json.dumps(resource)
        result = subprocess.run(
            ["oc", "apply", "-f", "-", "-n", namespace],
            input=res_json,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to apply {kind}: {result.stderr.strip()}")
        logger.info("%s '%s' applied", kind, name)

    endpoint = f"http://{name}-predictor.{namespace}.svc.cluster.local:8080"
    print(f"  {name}: {endpoint}")
    return endpoint


def wait_for_service(name: str, namespace: str, timeout: int = 900, interval: int = 15):
    """Poll until a KServe InferenceService is Ready."""
    print(f"Waiting for InferenceService '{name}' (timeout {timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            [
                "oc",
                "get",
                "inferenceservice",
                name,
                "-n",
                namespace,
                "-o",
                "jsonpath={.status.conditions[?(@.type=='Ready')].status}",
            ],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip() == "True":
            print(f"  InferenceService '{name}' is Ready")
            return
        time.sleep(interval)
    raise TimeoutError(f"InferenceService '{name}' not ready after {timeout}s")


def test_llm_endpoint(endpoint: str, model_name: str, retries: int = 3) -> bool:
    """Send a quick health-check request to a vLLM chat endpoint."""
    import requests

    url = f"{endpoint}/v1/chat/completions"
    for i in range(retries):
        try:
            resp = requests.post(
                url,
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 8,
                },
                timeout=30,
            )
            resp.raise_for_status()
            print(f"  LLM endpoint healthy ({resp.elapsed.total_seconds():.1f}s)")
            return True
        except Exception as exc:
            if i < retries - 1:
                logger.info("Retry %d: %s", i + 1, exc)
                time.sleep(5)
            else:
                logger.error(
                    "LLM health check failed after %d retries: %s", retries, exc
                )
    return False


def delete_vllm_service(name: str, namespace: str):
    """Delete a ServingRuntime and InferenceService by name."""
    for kind in ["inferenceservice", "servingruntime"]:
        result = subprocess.run(
            ["oc", "delete", kind, name, "-n", namespace, "--ignore-not-found"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"  Deleted {kind} '{name}'")


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def ask_llm(question: str, *, llm, model_name: str, context: str = "") -> str:
    """Send a question to the LLM, optionally with RAG context."""
    if context:
        prompt = (
            "You are a technical research assistant. Answer the user's question "
            "based ONLY on the numbered context documents below.\n\n"
            "Rules:\n"
            "- Cite your sources using [1], [2], etc. matching the document numbers.\n"
            "- After your answer, list each cited source on its own line under "
            "'Sources:' with the document number and filename.\n"
            "- If the answer is not in the provided context, say so explicitly.\n\n"
            f"## Context\n\n{context}\n\n"
            f"## Question\n\n{question}\n\n"
            "## Answer\n\n"
        )
    else:
        prompt = (
            "You are a helpful assistant. You do NOT have access to external documents "
            "or research papers. If the user asks about specific research findings, "
            "you MUST say: 'I do not have access to research documents. Please provide "
            "context from the relevant papers.'\n\n"
            f"## Question\n\n{question}\n\n"
            "## Answer\n\n"
        )

    try:
        response = llm.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.1,
        )
    except Exception as exc:
        logger.error("LLM API call failed: %s", exc)
        return f"[Error: LLM request failed — {exc}]"

    if not response.choices:
        return "[Error: LLM returned no choices]"

    answer = response.choices[0].message.content
    if response.usage:
        logger.info(
            "LLM response: prompt_tokens=%d completion_tokens=%d",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )
    return answer


def search_milvus(
    question: str,
    *,
    milvus,
    embed_model,
    collection_name: str,
    top_k: int = 5,
    score_threshold: float = 0.5,
) -> list:
    """Embed the question and search Milvus for similar chunks."""
    query_embedding = embed_model.encode([question], normalize_embeddings=True).tolist()

    try:
        results = milvus.search(
            collection_name=collection_name,
            data=query_embedding,
            limit=top_k,
            output_fields=["source_file", "chunk_index", "text"],
            search_params={"metric_type": "COSINE", "params": {"nprobe": 16}},
        )
    except Exception as exc:
        logger.error("Milvus search failed: %s", exc)
        return []

    contexts = []
    for hits in results:
        for hit in hits:
            contexts.append({
                "text": hit["entity"]["text"],
                "source_file": hit["entity"]["source_file"],
                "chunk_index": hit["entity"]["chunk_index"],
                "score": hit["distance"],
            })

    total = len(contexts)
    # pymilvus COSINE returns similarity (higher = more similar); >= keeps strong matches.
    contexts = [c for c in contexts if c["score"] >= score_threshold]
    logger.info(
        "Milvus search: %d results, %d after threshold filter",
        total,
        len(contexts),
    )
    return contexts


def build_context(chunks: list) -> str:
    """Format retrieved chunks with numbered references for citation."""
    return "\n\n---\n\n".join(
        f"[{i}] ({c['source_file']}, chunk {c['chunk_index']}, "
        f"score: {c['score']:.3f})\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    )


def print_comparison(
    question: str, answer_no_rag: str, answer_with_rag: str, chunks: list
):
    """Print the side-by-side RAG comparison with numbered sources."""
    sep = "=" * 60
    print(f"Question: {question}")
    print(f"\n{sep}\n  WITHOUT RAG\n{sep}\n")
    print(answer_no_rag)
    print(f"\n{sep}\n  WITH RAG\n{sep}\n")
    print(answer_with_rag)
    print(f"\n{sep}\n  SOURCES\n{sep}\n")
    for i, c in enumerate(chunks, 1):
        print(
            f"  [{i}] {c['source_file']}  (chunk {c['chunk_index']}, score: {c['score']:.3f})"
        )
