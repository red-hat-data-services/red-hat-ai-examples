## Launch Inference Servers for the Base and Compressed Models using vLLM

An inference server is a system that hosts a trained machine learning model and exposes an API endpoint, allowing users or applications to send inputs and receive predictions in real time. Inference servers are critical in production environments because they provide a standardized, scalable, and efficient way to deploy models for online usage.

vLLM is a high-performance inference engine specifically designed for large language models (LLMs). It optimizes throughput and latency by efficiently batching requests, reusing key-value caches, and managing GPU memory usage.

We use vLLM to launch inference servers for both the base model and the compressed model so that we can benchmark their performance under real-world serving conditions. By comparing metrics such as token throughput, latency, and concurrency handling, we can evaluate the benefits of model compression without affecting accuracy.

### vLLM Configuration for Single-Node and Multi-Node Serving

For single-node, single-GPU or multi-GPU (but not multi-node) vLLM serving, the main arguments are:

```text
--model                 : Model path or Hugging Face repo ID (required)

--tensor-parallel-size  : Number of GPUs to use (1 for single GPU, >1 for multi-GPU tensor parallelism)

--port                  : Port for the API server (default 8000)

--host                  : Host IP address (default 127.0.0.1)

--gpu-memory-utilization: Controls what fraction of each GPU’s memory vLLM will use for the model executor and KV cache. For example, --gpu-memory-utilization 0.5 means vLLM will use 50% of the GPU memory.

--quantization          : Method used to quantize the weights

--max-model-len         : argument sets the maximum context length (in tokens) that vLLM can process for both prompt and output combined. If not specified, it defaults to the model’s config value. Setting a higher value allows longer prompts/completions but increases GPU memory usage for the KV cache; setting it lower saves memory but limits context length. Set this to prevent problems with memory if the model’s default context length is too long.

```

For multi-node vLLM serving:

```text
--tensor-parallel-size   : Number of GPUs per node (or total GPUs if not using pipeline parallelism)
--pipeline-parallel-size : Number of nodes (optional, for pipeline parallelism)
```

Note: Multi-node setups also require a Ray cluster.

### Hardware Setup

For our example, both the base and compressed models will be served using a single-node, single-GPU setup. This ensures that performance comparisons between the models are fair and consistent.

GPU Used: 46GB L40S

vLLM Serving Mode: Single-node, single-GPU

Tensor Parallelism: 1 (no multi-GPU or multi-node setup)

Note: This setup simplifies deployment and ensures that system-level benchmarks like latency, throughput, and concurrency are directly comparable between the base and compressed models.

### Using the OpenAI SDK with vLLM

vLLM exposes an OpenAI-compatible REST API, which allows us to use the OpenAI SDK for testing the server without any modifications. Specifically:

vLLM runs a local web server (e.g., `http://127.0.0.1:8000/v1`)

It exposes the same endpoints as OpenAI (/v1/chat/completions, /v1/completions)

Requests follow the same schema (e.g., messages=[{"role": "..."}])

The OpenAI SDK can be used unchanged, sending requests to the local vLLM server

The SDK behaves as if it’s communicating with OpenAI, even though requests go to the local server

**Alternate option:** You can also send POST requests directly using Python’s requests library if you prefer more control.
