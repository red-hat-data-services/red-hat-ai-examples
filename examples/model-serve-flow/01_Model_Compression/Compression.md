## Compress a Large Language Model using LLM Compressor

Model Compression is a technique that reduces the size and computational requirements of large language models (LLMs) while maintaining their performance as much as possible. It is especially important in production environments, where deploying full-scale models can be costly in terms of memory, latency, and infrastructure resources. Compressed models enable faster inference, lower GPU usage, and scalability for real-time applications.

`llm-compressor` is an open-source framework used to quantize/compress models using multiple compression algorithms and schemes.

It supports the following quantization algorithms and schemes:

**Algorithms**

- Simple PTQ
- GPTQ
- AWQ
- SmoothQuant
- SparseGPT
- AutoRound

**Schemes**

- W8A8-INT8
- W8A8-FP8
- W4A16
- W8A16
- NVFP4
- W8A8-FP8_BLOCK

### Data Aware Quantization

Data-Aware Quantization is a technique that uses representative input data to guide the quantization process of a model. Instead of simply converting weights and activations to lower precision, it analyzes the model's behavior on actual data to minimize accuracy loss. By calibrating the model with real inputs (calibration dataset), data-aware quantization ensures that the compressed model maintains performance on tasks it is likely to encounter in production.

For our use case, we will be using `W8A8-INT8` scheme to compress a model. This scheme performs 8-bit integer (INT8) quantization for weights and activations, providing ~2X smaller weights with 8-bit arithmetic operations. It uses `channel-wise quantization` to compress weights to 8 bits using `GPTQ`, and uses `dynamic per-token quantization` to compress activations to 8 bits. Weight quantization can be both per-tensor or per-channel for INT8. W8A8-INT8 is good for general performance and compression, especially for server and batch inference. Activation quantization is carried out during inference on vLLM. Activations can be static or dynamic.

This scheme requires a calibration dataset as it is a data-aware quantization tenchnique.

### Things to keep in mind for data aware quantization

1. **Choice of Calibration Dataset:** GPTQ quantization estimates activation ranges from calibration data. If the calibration data is very different from what the model will see in production, these ranges may be inaccurate, leading to higher quantization errors and degraded model outputs.

    For production, use a dataset that closely resembles the expected domain(e.g finance, medicine etc), task(Q/A,    summarization etc), and style of your inputs to ensure quantization preserves quality.

    For the sake of this example, we will use a small, general-purpose dataset for faster processing. Specifically, we use the `wikitext-2-raw-v1` version of the WikiText dataset which is the smaller version.

2. **Number of Calibration Samples Used for Quantization**

    More samples give better and stable statistics on the range and distribution of activations, which reduces quantization noise. Small calibration sets, on the other hand, are quicker but noisier.

    For the sake of this demo, we use a small number of samples (e.g., 16–512) is enough to show the process.

    For production, use a larger sample set (hundreds to thousands) to stabilize ranges and minimize error.

3. **Sequence Length**

    Longer input sequences generate larger activations because each token’s representation depends on all previous tokens and layers. These bigger values can exceed the quantization range (e.g., -128 to 127 for 8-bit quantization), causing rounding errors or clipping, which reduces accuracy.

    For this demo, shorter sequences are sufficient to illustrate quantization.

    For production, use sequences that reflect maximum expected lengths in your application to prevent errors.

### Quantizing/Compressing a Model to INT8

To quantize a model with the W8A8-INT8 scheme, we first apply Smooth Quant and then compress the model using the GPTQ algorithm.

**SmoothQuant** SmoothQuant operates on the activations (outputs of intermediate layers that become inputs to the next layer) produced by the base model. These activations can sometimes have extreme values (outliers). SmoothQuant scales the activations to reduce these outliers so that most values fall within a reasonable range, e.g., [-4, 4].

To ensure that the overall layer output remains unchanged (Y = W * A), SmoothQuant also scales the corresponding weights by multiplying them with the same factor.

Activations are scaled as:
$A^*=A/s$

Weights are scaled as:
$W^*=W∗s$

This way, the layer output remains approximately the same, but the activations are now suitable for stable low-bit quantization.

**GPTQModifier** GPTQ takes the smoothed activations and weights produced by SmoothQuant and computes a quantization scale for each weight matrix. This scale determines how weights will be mapped into low-bit integers (e.g., int8).

GPTQ then:

1. Quantizes the weights using these scales

    $Wquant=round(W/s)$

2. Computes the model outputs using:

    full-precision weights → Y

    quantized weights → Yquant

3. Adjusts the quantization error so that

    $Yquant≈Y$
