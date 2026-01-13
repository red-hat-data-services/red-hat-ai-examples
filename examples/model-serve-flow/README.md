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

### Step 1. Baseline Accuracy Evaluation (Base Model)

Before applying any form of model compression, we first evaluate the base model to establish an accuracy baseline. This baseline is critical for understanding how subsequent compression techniques impact model quality.

Quantization is a lossy compression technique. Converting high-precision floating-point parameters into lower-precision representations introduces rounding errors that can accumulate across millions (or billions) of parameters and potentially degrade predictive performance. Establishing a baseline ensures that any accuracy changes observed later can be attributed to compression rather than evaluation or serving artifacts.

**Why we benchmark accuracy**:

- Create a reference baseline against which the compressed model’s accuracy can be compared

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

More details on evaluating LLMs is provided in [Accuracy_Evaluation.md](docs/Accuracy_Evaluation.md)

### Step 2. Baseline Inference Serving & Performance Benchmarking (Base Model)

After establishing the accuracy baseline, the next step is to evaluate the system-level inference performance of the base model in a production-style setup.

In this step, the base model is served using vLLM, and its inference performance is measured under load using GuideLLM. The results from this step serve as the performance baseline for later comparison with the compressed model.

#### Launching the Model for Inference using vLLM

vLLM is a very popular inference engine used for deploying LLMs. Various performance benchmarking tools like GuideLLM are used to evaluate the performance of models hosted by such systems.

Why we deploy models using vLLM:

The idea is to test the performance keeping a production setup in mind. So we serve both base and compressed models using vLLM so their performance can be assessed and compared using GuideLLM.

How We Serve the Models

Tool Used – vLLM (a high-throughput serving engine for LLMs)

Models Served – Both the Base and the Compressed models are served under identical conditions

Key Settings for Production Optimization:

--max-num-seqs – Sets maximum concurrent requests to optimize throughput via continuous batching

--enable-chunked-prefill – Reduces GPU memory usage by splitting long prompts (prefills) into manageable chunks

--enable-prefix-caching – Reuses previously computed Key-Value (KV) caches for faster decoding of repeated or shared prompts

--gpu-memory-utilization – Explicitly manages the percentage of GPU memory used for KV caching

#### Performance Benchmarking

Once the model is running, GuideLLM is used to generate concurrent inference traffic and collect performance metrics. Performance benchmarking confirms the real-world inference efficiency under load.

**How We Measure Performance**

`Tool Used` – GuideLLM (a specialized tool for LLM performance measurement)

**Metrics Evaluated**

- `Time to First Token (TTFT)` – The time taken to generate the first output token after receiving the prompt

- `Inter-Token Latency (ITL)` – The time between generating consecutive tokens (streaming speed)

- `Throughput` – Tokens generated per second (the primary measure of system capacity)

- `Concurrency` – Maximum number of requests the model can handle in parallel before performance significantly degrades

---
More details on system level performance benchmarking and GuideLLM are provided in [System_Level_Performance_Benchmarking.md](docs/System_Level_Performance_Benchmarking.md)

### Step 3: Model Quantization

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
More details on quantization are provided in [Compression.md](docs/Compression.md).

### Step 4: Accuracy Evaluation (Compressed Model)

The compressed model is evaluated on the same benchmark datasets and metrics as the base model (Step 1). This allows a direct comparison against the accuracy baseline to quantify any impact of quantization.

**Purpose**: Compare the accuracy of the compressed model to the base model

**Metrics & Benchmarks**: Same as Step 1 (MMLU, IFEval, ARC, HellaSwag; accuracy, accuracy_norm, task-specific scores)

**Outcome**: Quantitative metrics for the compressed model to assess if accuracy is preserved

More details on evaluation methods are available in [Accuracy_Evaluation.md](docs/Accuracy_Evaluation.md)

### Performance Benchmarking (Compressed Model)

The compressed model is served using vLLM and benchmarked using GuideLLM following the same approach as Step 2 for the base model. This provides system-level metrics to compare latency, throughput, and concurrency with the baseline.

**Purpose**: Assess inference performance of the compressed model relative to the base model

**Metrics**: TTFT, ITL, throughput, concurrency (same as Step 2)

**Outcome**: Baseline comparison for performance trade-offs after compression

More details on system-level benchmarking are available in [System_Level_Performance_Benchmarking.md](docs/System_Level_Performance_Benchmarking)

### 6. Result Comparison

This step integrates the accuracy and performance data to provide a comprehensive view of the quantization trade-offs

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

Results are compared in [Accuracy_Comparison.md](docs/Accuracy_Comparison.md) and [Performance_Comparison.md](docs/Performance_Comparison.md)

### Step 7: Model Deployement

This step provides a guide to deploy the compressed model on a Red Hat OpenShift AI (RHOAI) cluster and vLLM. Detailed instructions are available in: [RHOAI_Deployment_README.md](07_Deployment/RHOAI_Deployment_README.md) and [VLLM_Deployment_README.md](07_Deployment/VLLM_Deployment_README.md)

## Project Structure

The `model-serve-flow` project is organized into sequential steps, with each step contained in its own directory:

- Step 1: [01_Base_Accuracy_Benchmarking](01_Base_Accuracy_Benchmarking)

- Step 2: [02_Base_Performance_Benchmarking](02_Base_Performance_Benchmarking)

- Step 3: [03_Model_Compression](03_Model_Compression)

- Step 4: [04_Compressed_Accuracy_Benchmarking](04_Compressed_Accuracy_Benchmarking)

- Step 5: [05_Compressed_Performance_Benchmarking](05_Compressed_Performance_Benchmarking)

- Step 6: [06_Comparison](06_Comparison)

- Step 7: [07_Deployment](07_Deployment)

Each step represents a distinct stage in the model compression, evaluation, and deployment workflow.
