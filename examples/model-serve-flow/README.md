## Example Workflow

This example demonstrates the end-to-end workflow for quantizing, benchmarking, serving, and evaluating a LLaMA-3.1 8B model. Each step is designed to optimize model performance while maintaining accuracy and usability in production.

### 1. Quantize the Model

Quantization is the process of converting model parameters (weights and activations) from high-precision floating-point formats (e.g., FP16 or BF16) to lower-precision integer formats (e.g., INT8).

Why we quantize:

- Reduce memory usage: Lower precision weights occupy less GPU memory, allowing larger batch sizes and longer KV caches, which improves overall system throughput.

- Speed up computation: Low-precision matrix multiplications (INT8/FP8) are inherently faster on modern GPU architectures than high-precision operations, significantly reducing inference time.

- Enable deployment on resource-constrained environments: Quantization makes large language models feasible for real-time applications and devices with limited VRAM.

**How We Quantize in This Example**

- `Base Model` – LLaMA-3.1-8B-Instruct

- `Tool Used` – LLM Compressor

- `Quantization Scheme` – INT8 W8A8 (8-bit weights and 8-bit activations), specifically employing dynamic quantization of activations

- `Output Model` – A compressed model named LLama-3.1-8B-Instruct-int8-dynamic

---

### 2. Accuracy Benchmarking

Quantization is a lossy compression technique. Converting floating-point numbers to integers introduces minor rounding errors, which can accumulate across millions of parameters and potentially degrade the model's predictive capabilities.

Why we benchmark accuracy:

- Ensure minimal degradation: Benchmarking verifies that the accuracy drop introduced by quantization is within an acceptable tolerance for production needs

- Compare performance trade-offs: It provides critical data to confirm that the speed improvements gained from compression do not come at a significant cost to model capabilities (e.g., reasoning, knowledge)

**How We Perform Accuracy Benchmarking**

Models Evaluated:

Accuracy evaluation is done for both the original base model and compressed model

`Tool Used` – LMEval

Tasks Evaluated:

We measure performance across diverse capabilities to get a holistic view:

- MMLU – General knowledge and reasoning

- IFEval – Language fluency and comprehension

- ARC – Logical and scientific reasoning

- HellaSwag – Commonsense completion

---

### 3. Launching the Model for Inference using vLLM

vLLM is a very popular inference engine used for deploying LLMs. Various performance benchmarking tools like GuideLLM are used to evaluate the performance of models hosted by such systems. The idea is to test the performance keeping a production setup in mind. So we serve both base and compressed models using vLLM so their performance can be assessed and compared using GuideLLM.

**How We Serve the Models**

`Tool Used` – vLLM (a high-throughput serving engine for LLMs)

`Models Served` – Both the Base and the Compressed models are served under identical conditions

Key Settings for Production Optimization:

- `--max-num-seqs` – Sets maximum concurrent requests to optimize throughput via continuous batching

- `--enable-chunked-prefill` – Reduces GPU memory usage by splitting long prompts (prefills) into manageable chunks

- `--enable-prefix-caching` – Reuses previously computed Key-Value (KV) caches for faster decoding of repeated or shared prompts

- `--gpu-memory-utilization` – Explicitly manages the percentage of GPU memory used for KV caching

---

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
