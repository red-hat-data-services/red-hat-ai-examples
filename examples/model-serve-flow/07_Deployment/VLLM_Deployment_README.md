# Deploying the Compressed Model Using vLLM Server

**Overview:**

This guide demonstrates how to deploy a compressed LLaMA 3.1 8B INT8 model using a vLLM server.
The model has already been compressed, validated for accuracy, and benchmarked for performance.
We will cover: starting the server, loading the model, and verifying that it is serving requests via curl or the OpenAI SDK.

## Prerequisites

1. A machine, container, or environment with vLLM installed and ready to run, using either CPU or GPU resources.
2. The compressed model is available in a local path or shared storage accessible by the server.
3. Python and openai SDK installed if you plan to test programmatically.

## Steps to deply a model

### Step 1: Start the vLLM Server

Start the vLLM server and point it to your compressed model:

```bash
vllm serve /path/to/model \
  --host 0.0.0.0 \
  --port 8000 \
  --api-key <"confgure your secret token"> \
  --tensor-parallel-size <num of GUPs available per node> \
  --pipeline-parallel-size <total number of available nodes> \
  --max-model-len 8192 \
  --enable-prefix-caching \
  --max-num-batched-tokens 8192 \
  --max-num-seqs 1024 \
  --gpu-memory-utilization 0.9 \
  --quantization compressed-tensors \
  --disable-log-stats \
```

### Step 2: Verify the Server is Running

Once the server starts, check if it is listening on port 8000:

```bash
curl -v http://localhost:8000/health
```

A successful response confirms the server is live. The response should show `200 OK`

### Step 3: Programmatic Verification Using OpenAI SDK

Use the follwoing code to test out the server:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",  # Use local server endpoint
    api_key=<your secret token>
)
response = client.chat.completions.create(
    model= "path to the model", #e.g. ../Llama_3.1_8B_Instruct_int8_dynamic
    messages=[{"role": "user", "content": "What is photosynthesis?"}],
)

print(response.choices[0].message.content)
```
