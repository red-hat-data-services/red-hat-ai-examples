## Performance Benchmarking Using GuideLLM

Performance benchmarking is the process of evaluating how efficiently a model performs under real-world conditions. Unlike accuracy evaluation, which focuses on the quality of predictions, performance benchmarking measures system-level metrics such as inference speed, latency, concurrency handling, and throughput. These metrics are critical for deploying large language models (LLMs) in production environments, where high demand and resource constraints can impact the user experience.

Benchmarking ensures that the deployed model:

- Responds within acceptable latency limits

- Handles multiple concurrent requests without performance degradation

- Makes efficient use of available hardware (CPU/GPU, memory)

### Why Benchmark Both Base and Compressed Models

When compressing a model, optimizations like quantization reduce memory usage and inference time. However, these changes can introduce subtle performance differences. Benchmarking both the base model and the compressed model under identical conditions provides a direct comparison, helping you understand the benefits and trade-offs of compression.

### GuideLLM Overview

GuideLLM is an open-source benchmarking framework specifically designed to evaluate LLMs served via vLLM. It measures fine-grained performance metrics, including:

- *Token throughput*

- *Latency metrics*

  - Time to First Token (TTFT)

  - Inter-Token Latency (ITL)

  - End-to-end request latency

- *Concurrency scaling*

- *Request-level diagnostics*

By using GuideLLM, you can systematically measure the efficiency of your LLM deployments and make informed decisions about resource allocation and optimizations.

### Metrics provided by GuideLLM

GuideLLM provides multiple metrics tat can be used to evaluate the performace of a LLM.

These performance metrics include:

- ``Request Rate`` (Requests Per Second): The number of requests processed per second.
Indicates the throughput of the system and its ability to handle concurrent workloads.
- ``Request Concurrency``: The number of requests being processed simultaneously.
Helps evaluate the system's capacity to handle parallel workloads.

- ``Output Tokens Per Second``
The average number of output tokens generated per second as a throughput metric across all requests. Provides insights into the server's performance and efficiency in generating output tokens.
- ``Total Tokens Per Second``: The combined rate of prompt and output tokens processed per second as a throughput metric across all requests.
Provides insights into the server's overall performance and efficiency in processing both prompt and output tokens.

- ``Request Latency``: The time taken to process a single request, from start to finish.
A critical metric for evaluating the responsiveness of the system.

- ``Time to First Token (TTFT)``: The time taken to generate the first token of the output.
Indicates the initial response time of the model, which is crucial for user-facing applications.

- ``Inter-Token Latency (ITL)``: The average time between generating consecutive tokens in the output, excluding the first token. Helps assess the smoothness and speed of token generation.

- ``Time Per Output Token``: The average time taken to generate each output token, including the first token. Provides a detailed view of the model's token generation efficiency.

- ``Statistical Summaries``
GuideLLM provides detailed statistical summaries for each of the above metrics using the StatusDistributionSummary and DistributionSummary models. These summaries include the following statistics:

**Summary Statistics**

- Mean: The average value of the metric.
- Median: The middle value of the metric when sorted.
- Mode: The most frequently occurring value of the metric.
- Variance: The measure of how much the values of the metric vary.
- Standard Deviation (Std Dev): The square root of the variance, indicating the   spread of the values.
- Min: The minimum value of the metric.
- Max: The maximum value of the metric.
- Count: The total number of data points for the metric.
- Total Sum: The sum of all values for the metric.

### Token Configuration for Different Use Cases

GuideLLM allows to configure both **input (prompt) tokens** and **output (completion) tokens** depending on the workload to be evaluated.
Different use cases benefit from different token budgets, and these values can be fully adjusted based on the requirements.

1. **Chat Use Case**

    Chat-style interactions typically have moderate prompts and short-to-medium responses.

    Input tokens: ~512

    Output tokens: ~1,024

    Rationale: Chat prompts are usually concise, and responses should be coherent without being excessively long.

2. **RAG (Retrieval-Augmented Generation)**

    RAG workloads include retrieved documents in the prompt, resulting in longer input sizes while answers remain relatively short.

    Input tokens: ~2,000

    Output tokens: ~500

    Rationale: Retrieved context significantly increases prompt length; outputs should remain grounded and precise.

3. **Reasoning** (e.g., long-form reasoning, code explanation, chain-of-thought tasks)

    Reasoning tasks often require short prompts but longer outputs to capture detailed step-by-step reasoning.

    Input tokens: ~300

    Output tokens: ~1,500

    Rationale: These tasks need extended reasoning or multi-step analysis, so outputs must accommodate longer sequences.

### Performance Benchmarking Parameters

GuideLLM allows fine-grained configuration of benchmark runs. Below are the key parameters used to evaluate a vLLM server:

**1. target**: The URL of the vLLM model server to benchmark.

**2. profile/rate-type**: Defines the traffic pattern. Optons include:

- ``synchronous``: Runs requests one at a time (sequential)
- ``throughput``: Tests maximum throughput by running requests in parallel - To see how many requests can be handled in parallel
- ``concurrent``: Runs a fixed number of parallel request streams
- ``constant``: Sends requests at a fixed rate per second
- ``poisson``: Sends requests following a Poisson distribution
- ``sweep``: Automatically determines optimal performance points (default)

**3. rate**: The numeric rate value whose meaning depends on profile - for sweep it's the number of benchmarks, for concurrent it's simultaneous requests, for constant/poisson it's requests per second. GuideLLM supports multiple workload simulation modes. Each rate type determines which benchmarks are run. The example above uses sweep, which runs a series of benchmarks for 30 seconds each: first, a synchronous test that sends one request at a time (representing minimal traffic), then a throughput test where all requests are sent in parallel to identify the system's maximum RPS. Finally, it runs intermediate RPS levels to capture latency metrics across the full traffic spectrum.

**4. data**: Specifies the dataset source. This can be a file path, Hugging Face dataset ID, synthetic data configuration, or in-memory data. In this case, we will be setting it to define a synthetic data configuration.
Synthetic datasets allow you to generate data on the fly with customizable parameters. This is useful for controlled experiments, stress testing, and simulating specific scenarios. For example, you might want to evaluate how a model handles long prompts or generates outputs with specific characteristics. Data can be configured for different use cases like chat, RAG, code generation etc.
Important config parameters:

- ``prompt_tokens``: : Average number of tokens in prompts.
- ``output_tokens``: Average number of tokens in outputs.
- ``samples``: Number of samples to generate (default: 1000)
- ``source``: Source text for generation (default: prideandprejudice.txt.gz). This can be any text file, URL containing a text file, or a compressed text file. The text is used to sample from at a word and punctuation granularity and then combined into a single string of the desired lengths.

**5. max-seconds**: Maximum duration in seconds for each benchmark run (can also use **--max-requests** to limit by request count instead)

**6. processor**: Specifies the tokenizer to use. This is only required for synthetic data generation or when local calculations are specified through configuration settings. By default, the processor is set to the --model argument. If --model is not supplied, it defaults to the model retrieved from the backend. The tokenizer is used to calculate the number of tokens to adjust the input length based on ``prompt_tokens``.  Using the model’s native tokenizer ensures the prompt token count matches what the model actually receives and the output token count reflects the true workload.

**Note**: For synthetic data generation, a source file has to be provided which can be continuous text in a compatible format like txt. Input prompts (number can be specified using the ``source`` param) are then sampled from this file, with prompts having a length of ``prompt_tokens`` tokens.

### Running a Benchmark for Our Use Case

For our evaluation, we will run a `sweep` benchmark on the vLLM server for `120 seconds`. This measures performance across varying traffic levels and collects metrics like throughput, latency, and token generation efficiency.
