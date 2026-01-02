## Project Overview

The `model-serve-flow` project demonstrates an end-to-end workflow for compressing, evaluating, serving, and benchmarking large language models in a production-style setup.

The project is organized as a sequence of clearly defined steps, each representing a distinct stage in the model compression and deployment lifecycle, from quantization and accuracy evaluation to inference serving and performance benchmarking.

This repository uses a LLaMA-3.1 8B model as a concrete example to illustrate the full workflow, with each step designed to optimize model performance while maintaining accuracy and usability in production.

## Setup & Installation

Clone the repository:

```bash
git clone https://github.com/red-hat-data-services/red-hat-ai-examples.git
cd red-hat-ai-examples/examples/model-serve-flow
```

## Detailed Step-by-Step Workflow

### 1. Quantize the Model

Quantization is the process of converting model parameters (weights and activations) from high-precision floating-point formats (e.g., FP16 or BF16) to lower-precision integer formats (e.g., INT8).

**Why we quantize**:

- *Reduce memory usage*: Lower precision weights occupy less GPU memory, allowing larger batch sizes and longer KV caches, which improves overall system throughput.

- *Speed up computation*: Low-precision matrix multiplications (INT8/FP8) are inherently faster on modern GPU architectures than high-precision operations, significantly reducing inference time.

- *Enable deployment on resource-constrained environments*: Quantization makes large language models feasible for real-time applications and devices with limited VRAM.

**How We Quantize in This Example**

- `Base Model` – LLama-3.1-8B-Instruct

- `Tool Used` – LLM Compressor

- `Quantization Scheme` – INT8 W8A8 (8-bit weights and 8-bit activations), specifically employing dynamic quantization of activations

- `Output Model` – A compressed model named LLama_3.1_8B_Instruct_int8_dynamic

---
More details on quantization are provided in [Compression.md](01_Model_Compression/Compression.md).

### 2. Accuracy Benchmarking

Quantization is a lossy compression technique. Converting floating-point numbers to integers introduces minor rounding errors, which can accumulate across millions of parameters and potentially degrade the model's predictive capabilities.

**Why we benchmark accuracy**:

- *Ensure minimal degradation*: Benchmarking verifies that the accuracy drop introduced by quantization is within an acceptable tolerance for production needs

- *Compare performance trade-offs*: It provides critical data to confirm that the speed improvements gained from compression do not come at a significant cost to model capabilities (e.g., reasoning, knowledge)

**How We Perform Accuracy Benchmarking**

`Models Evaluated` - Accuracy evaluation is done for both the original base model and compressed model.

`Tool Used` – LMEval

**Tasks Evaluated**:

We measure performance across diverse capabilities to get a holistic view:

- MMLU – General knowledge and reasoning

- IFEval – Language fluency and comprehension

- ARC – Logical and scientific reasoning

- HellaSwag – Commonsense completion

---

More details on evaluating LLMs is provided in [Accuracy_Evaluation.md](02_Accuracy_Benchmarking/Accuracy_Evaluation.md)

### 3. Launching the Model for Inference using vLLM

vLLM is a very popular inference engine used for deploying LLMs. Various performance benchmarking tools like GuideLLM are used to evaluate the performance of models hosted by such systems.

**Why we deploy models using vLLM**:

The idea is to test the performance keeping a production setup in mind. So we serve both base and compressed models using vLLM so their performance can be assessed and compared using GuideLLM.

**How We Serve the Models**

`Tool Used` – vLLM (a high-throughput serving engine for LLMs)

`Models Served` – Both the Base and the Compressed models are served under identical conditions

**Key Settings for Production Optimization**:

- `--max-num-seqs` – Sets maximum concurrent requests to optimize throughput via continuous batching

- `--enable-chunked-prefill` – Reduces GPU memory usage by splitting long prompts (prefills) into manageable chunks

- `--enable-prefix-caching` – Reuses previously computed Key-Value (KV) caches for faster decoding of repeated or shared prompts

- `--gpu-memory-utilization` – Explicitly manages the percentage of GPU memory used for KV caching

---
More details on vLLM are provided in [Model_Serving_vLLM.md](03_Vllm_Server/Vllm_Server_README.md)

### 4. Performance Benchmarking

While quantization should lead to speed improvements, performance benchmarking confirms the real-world inference efficiency under load. This is the ultimate test of the quantization value proposition.

**Why we benchmark performance**

- *Understand model efficiency* – Confirms that the compressed model delivers the expected speed gains (reduced latency and higher throughput) compared to the base model

- *Identify bottlenecks* – Highlights limits of concurrency or potential latency spikes under heavy load

- *Direct comparison* – Provides verifiable metrics to justify the deployment of the compressed model over the original

**How We Measure Performance**

`Tool Used` – GuideLLM (a specialized tool for LLM performance measurement)

**Metrics Evaluated**

- `Time to First Token (TTFT)` – The time taken to generate the first output token after receiving the prompt

- `Inter-Token Latency (ITL)` – The time between generating consecutive tokens (streaming speed)

- `Throughput` – Tokens generated per second (the primary measure of system capacity)

- `Concurrency` – Maximum number of requests the model can handle in parallel before performance significantly degrades

---
More details on system level performance benchmarking and GuideLLM are provided in [System_Level_Performance_Benchmarking.md](04_Performance_Benchmarking/System_Level_Performance_Benchmarking.md)

### 5. Result Comparison

The final step integrates the accuracy and performance data to provide a comprehensive view of the quantization trade-offs

All results are compiled in a comparison markdown file (comparison.md)

Key comparisons include:

- Latency differences (TTFT & ITL)

- Maximum concurrency supported

- Throughput per second

- ITL degradation ratio at increasing concurrency

**Why this step is important**

- **Evaluate trade-offs** – Shows the balance between speed, concurrency, and accuracy

- **Support decision-making** – Helps determine whether the compressed model is suitable for production

- **Communicate results clearly** – Provides a single reference for model selection

## Project Structure

The `model-serve-flow` project is organized into sequential steps, with each step contained in its own directory:

- Step 1: [01_Model_Compression](01_Model_Compression)

- Step 2: [02_Accuracy_Benchmarking](02_Accuracy_Benchmarking)

- Step 3: [03_Vllm_server](03_Vllm_server)

- Step 4: [04_Performance_Benchmarking](04_Performance_Benchmarking)

- Step 5: [05_Comparison](05_Comparison)

Each step represents a distinct stage in the model compression, evaluation, and deployment workflow.

### Base vs Compressed Model Workflow

- Step 1 is executed once to generate the compressed model.

- Steps 2 through 4 must be executed separately for both the base and the compressed models.

To ensure clean execution and to avoid GPU out-of-memory (OOM) issues, each of these steps contains two separate notebooks:

- `Base.ipynb` — for experiments using the base model

- `Compressed.ipynb` — for experiments using the compressed model

Keeping the base and compressed workflows in separate notebooks ensures that only one model is loaded into GPU memory at a time and prevents interference between experiments.

Step 5 compares the accuracy and performance results of the two models.

### Recommended Execution Order

For Steps 3 (vLLM Serving) and 4 (Performance Benchmarking), the notebooks should be run model-by-model, not step-by-step across models.

### Correct execution order

1. Launch the vLLM server for the base model (Step 3 → [Base.ipynb](03_Vllm_Server/Base.ipynb))

2. Run performance benchmarking for the base model (Step 4 → [Base.ipynb](04_Performance_Benchmarking/Base.ipynb))

3. Launch the vLLM server for the compressed model (Step 3 → [Compressed.ipynb](03_Vllm_Server/Compressed.ipynb))

4. Run performance benchmarking for the compressed model (Step 4 → [Compressed.ipynb](04_Performance_Benchmarking/Compressed.ipynb))

This order ensures that:

- Only one inference server is active at a time

- GPU resources are fully released before switching models

- Performance measurements remain consistent and comparable
