## Goal: 
This document will compare the system level performance of the compressed and base models. 

## Hardware:
Single L40S GPU, 46GB

## Base Model:
LLama-3.1-8B-Instruct

## Quantized Model:
LLama-3.1-8B-Instruct-int8-dynamic

## Quantization Scheme
Int W8A8

## Performance Results for Base Model

1. **Request Latency Statistics (Completed Requests)**

This table focuses on how **long** requests take and the latency characteristics of the base model server.

```text

ℹ Request Latency Statistics (Completed Requests)
|=============|=========|========|=========|=========|======|======|=======|=======|
| Benchmark   | Request Latency || TTFT             || ITL        || TPOT         ||
| Strategy    | Sec             || ms               || ms         || ms           ||
|             | Mdn     | p95    | Mdn     | p95     | Mdn  | p95  | Mdn   | p95   |
|-------------|---------|--------|---------|---------|------|------|-------|-------|
| synchronous | 11.4    | 11.4   | 115.9   | 124.1   | 22.2 | 22.2 | 22.3  | 22.4  |
| throughput  | 62.3    | 92.4   | 33854.1 | 60812.2 | 55.7 | 92.4 | 121.6 | 180.5 |
| constant    | 12.5    | 12.6   | 130.4   | 143.1   | 24.3 | 24.3 | 24.5  | 24.5  |
| constant    | 13.2    | 13.2   | 133.6   | 144.9   | 25.6 | 25.6 | 25.8  | 25.8  |
| constant    | 14.0    | 14.1   | 133.5   | 144.9   | 27.1 | 27.2 | 27.3  | 27.5  |
| constant    | 14.7    | 14.8   | 138.7   | 151.9   | 28.6 | 28.6 | 28.8  | 28.9  |
| constant    | 16.5    | 16.6   | 140.2   | 156.9   | 32.0 | 32.2 | 32.3  | 32.4  |
| constant    | 17.5    | 17.5   | 143.2   | 157.9   | 33.9 | 34.0 | 34.1  | 34.3  |
| constant    | 18.5    | 18.7   | 146.8   | 161.8   | 36.0 | 36.3 | 36.2  | 36.5  |
| constant    | 20.4    | 20.4   | 147.0   | 162.4   | 39.6 | 39.7 | 39.8  | 39.9  |
|=============|=========|========|=========|=========|======|======|=======|=======|
```

2.  **Server Throughput Statistics**

This table focuses on how many requests the base model server can handle per second. Throughput can be thought of as the **rate** (or time required) of processing. 

```text
ℹ Server Throughput Statistics
|=============|=====|======|=======|=======|========|========|========|=======|=======|========|
| Benchmark   | Requests                |||| Input Tokens   || Output Tokens || Total Tokens  ||
| Strategy    | Per Sec   || Concurrency  || Per Sec        || Per Sec       || Per Sec       ||
|             | Mdn | Mean | Mdn   | Mean  | Mdn    | Mean   | Mdn    | Mean  | Mdn   | Mean   |
|-------------|-----|------|-------|-------|--------|--------|--------|-------|-------|--------|
| synchronous | 0.1 | 0.1  | 1.0   | 1.0   | 92.5   | 101.8  | 45.1   | 44.8  | 45.1  | 137.4  |
| throughput  | 0.5 | 1.7  | 125.0 | 100.5 | 132.2  | 3094.4 | 604.5  | 885.0 | 607.5 | 2713.7 |
| constant    | 0.3 | 0.2  | 3.0   | 3.2   | 303.9  | 314.3  | 138.2  | 135.9 | 138.3 | 416.8  |
| constant    | 0.5 | 0.4  | 6.0   | 5.7   | 519.6  | 530.3  | 204.8  | 227.9 | 205.2 | 698.9  |
| constant    | 0.7 | 0.6  | 10.0  | 8.6   | 735.7  | 746.1  | 262.5  | 318.9 | 262.7 | 977.8  |
| constant    | 0.9 | 0.8  | 13.0  | 11.5  | 951.1  | 962.4  | 344.7  | 408.1 | 344.8 | 1251.4 |
| constant    | 1.1 | 0.9  | 18.0  | 15.5  | 1169.7 | 1178.3 | 422.8  | 491.6 | 423.4 | 1507.6 |
| constant    | 1.3 | 1.1  | 23.0  | 19.3  | 1383.0 | 1394.3 | 464.6  | 576.5 | 465.1 | 1767.8 |
| constant    | 1.5 | 1.3  | 28.0  | 23.4  | 1598.5 | 1610.6 | 497.3  | 658.7 | 498.2 | 2019.9 |
| constant    | 1.7 | 1.4  | 34.0  | 28.5  | 1827.6 | 1826.5 | 576.5  | 734.0 | 577.6 | 2250.6 |
|=============|=====|======|=======|=======|========|========|========|=======|=======|========|

```
## Performance results for compressed model
1. **Request Latency Statistics (Completed Requests)**

This table focuses on how **long** requests take and the latency characteristics of the server.

```text
ℹ Request Latency Statistics (Completed Requests)
|=============|=========|========|=========|=========|======|======|=======|=======|
| Benchmark   | Request Latency || TTFT             || ITL        || TPOT         ||
| Strategy    | Sec             || ms               || ms         || ms           ||
|             | Mdn     | p95    | Mdn     | p95     | Mdn  | p95  | Mdn   | p95   |
|-------------|---------|--------|---------|---------|------|------|-------|-------|
| synchronous | 7.6     | 7.9    | 87.9    | 445.7   | 14.7 | 14.7 | 14.8  | 15.5  |
| throughput  | 70.4    | 74.8   | 36149.3 | 40360.5 | 63.9 | 99.4 | 137.4 | 146.1 |
| constant    | 8.3     | 8.3    | 99.4    | 108.0   | 16.1 | 16.1 | 16.2  | 16.3  |
| constant    | 8.9     | 8.9    | 99.1    | 107.2   | 17.2 | 17.3 | 17.4  | 17.4  |
| constant    | 9.7     | 9.8    | 104.4   | 113.0   | 18.8 | 18.9 | 19.0  | 19.1  |
| constant    | 10.5    | 10.6   | 104.9   | 114.6   | 20.4 | 20.5 | 20.6  | 20.6  |
| constant    | 11.7    | 11.8   | 106.9   | 118.1   | 22.7 | 22.8 | 22.8  | 23.0  |
| constant    | 12.7    | 12.8   | 108.3   | 119.3   | 24.7 | 24.8 | 24.9  | 24.9  |
| constant    | 16.0    | 18.5   | 121.6   | 959.9   | 31.1 | 34.7 | 31.3  | 36.1  |
| constant    | 17.8    | 18.1   | 119.7   | 136.0   | 34.5 | 35.2 | 34.7  | 35.4  |
|=============|=========|========|=========|=========|======|======|=======|=======|

```

2.  **Server Throughput Statistics**

This table focuses on how many requests a server can handle per second. Throughput can be thought of as the **rate** (or time required) of processing. 
```text
Server Throughput Statistics
|=============|=====|======|=======|=======|========|========|=======|========|=======|========|
| Benchmark   | Requests                |||| Input Tokens   || Output Tokens || Total Tokens  ||
| Strategy    | Per Sec   || Concurrency  || Per Sec        || Per Sec       || Per Sec       ||
|             | Mdn | Mean | Mdn   | Mean  | Mdn    | Mean   | Mdn   | Mean   | Mdn   | Mean   |
|-------------|-----|------|-------|-------|--------|--------|-------|--------|-------|--------|
| synchronous | 0.1 | 0.1  | 1.0   | 1.0   | 139.6  | 148.9  | 68.2  | 67.6   | 68.2  | 207.3  |
| throughput  | 0.6 | 2.6  | 194.0 | 152.8 | 123.1  | 4262.7 | 966.7 | 1369.8 | 971.8 | 4200.5 |
| constant    | 0.4 | 0.4  | 4.0   | 3.3   | 456.2  | 465.9  | 217.6 | 209.7  | 217.8 | 643.0  |
| constant    | 0.7 | 0.7  | 6.0   | 6.1   | 779.7  | 789.8  | 326.7 | 353.9  | 327.1 | 1085.1 |
| constant    | 1.0 | 1.0  | 10.0  | 9.3   | 1103.9 | 1113.8 | 422.1 | 495.3  | 422.3 | 1518.7 |
| constant    | 1.3 | 1.2  | 14.0  | 12.8  | 1426.6 | 1437.8 | 498.8 | 634.7  | 499.5 | 1946.3 |
| constant    | 1.7 | 1.5  | 19.0  | 17.3  | 1753.6 | 1761.9 | 629.9 | 770.0  | 630.6 | 2361.2 |
| constant    | 2.0 | 1.7  | 25.0  | 22.0  | 2078.6 | 2085.8 | 746.2 | 901.6  | 747.0 | 2764.8 |
| constant    | 2.3 | 2.0  | 36.0  | 32.4  | 2401.2 | 2674.7 | 783.9 | 1110.9 | 786.0 | 3406.4 |
| constant    | 2.5 | 2.2  | 44.0  | 37.5  | 2733.0 | 2733.5 | 829.7 | 1123.5 | 831.5 | 3445.2 |
|=============|=====|======|=======|=======|========|========|=======|========|=======|========|
```
### Concurrency Comparison
The compressed model can handle more requests concurrently because compressing the model weights frees up GPU memory, allowing more space for the KV cache. If there is more memory available for storing KV cache, more and longer requests can be handled by the system.
   - Max concurrent requests handled by the compressed model: 44.0
   - Max concurrent requests handled by the base model: 34.0

### TTFT and ITL Comparison
The compressed model exhibits lower TTFT and ITL than the base model, even while sustaining higher median concurrency:

```
 Compressed model: median concurrency = 44.0, ITL = 34.5 ms

 Base model: median concurrency = 34.0, ITL = 39.6 ms
```
This indicates that the compressed model maintains better latency characteristics under higher load.

As the model is compressed, matrix multiplications are executed in lower precision as compared to higher precisions for the base model. This makes the computations faster. This benefit is most pronounced during the prefill phase, where the model processes the entire input prompt in parallel. As a result, the compressed model achieves a lower Time to First Token (TTFT).

During the decode phase, both models reuse previously computed KV pairs from the KV cache and only compute the KV for the current token. However, matrix multiplications are faster for the compressed model due to low-precision computation as compared to the base model.

While the compressed model benefits from faster low-precision matrix multiplications, it also incurs additional per-token overhead due to dynamic activation quantization. At low to moderate concurrency, the faster compute dominates. As concurrency increases, the repeated quantization overhead accumulates across many sequences, leading to faster ITL degradation relative to the base model.

### ITL Degradation Ratio

The ITL degradation ratio (ITL at highest concurrency / ITL at lowest concurrency) is greater for the compressed model, meaning the time required to generate tokens increases faster for compressed model as compared to the base model as the concurrency increases.

As the concurrency increases, meaning more and more requests are processed simultaneously, the time required for the compressed model to produce the next token increases at a higher rate than the base model. The reason the W8A8 models (both INT8 and FP8) show a higher ITL degradation factor (2.34)  than the Base FP16/BF16 model (1.78) is the required **dynamic re-quantization** process that happens per layer, per token, per sequence.

As we have performed **dynamic** quantization, while the weights are quantized beforehand (static), the activations for every layer of the model are quantized on the fly during inference (dynamic) when generating a token. This dynamic transformation adds an overhead. 

Quantizing activations dynamically involves the following steps:

```text
| Component / Stage         | Precision Used | Purpose |
|---------------------------|----------------|---------|
| Input Activation          | FP16 / BF16    | Input data with numerical stability |
| Quantization Step         | INT8 / FP8     | Convert activations to low precision |
| Weights                   | INT8 / FP8     | Stored quantized model parameters |
| MatMul (Internal)         | 8-bit × 8-bit  | Fast Tensor Core multiplication |
| Accumulation (Internal)   | INT32 / FP32   | High-precision accumulation |
| Output Activation         | FP16 / BF16    | Cast output back to higher precision |

```
These extra steps of first converting the activations to lower precision before performing MatMul, and then converting them back to higher precision for the next layer adds an overhead for the compressed model. This additional computation piles up when the number of requests to be handled in parallel is large - more requests, more overhead computation. 

```
   ITL degradation ratio compressed model = 34.5/14.7 = 2.34
   ITL degradation ratio base model = 39.6/22.2 = 1.78
```

Despite having a higher ITL degradation ratio, the ITL for the compressed model at highest observed concurrency (34.5) is still lower than the highest ITL for the base model (39.6). If multi-GPU infrastructure were used, the ITL degradation could be mitigated further, as this additional quantization workload would be distributed across multiple GPUs.