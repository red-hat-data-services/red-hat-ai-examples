# Step 1: Compress a LLM to INT8

## Navigation

- [Model Serving Overview](../README.md)
- Step 1: Model Compression
- [Step 2: Accuracy Benchmarking](../02_Accuracy_Benchmarking/Accuracy_Benchmarking.md)
- [Step 3: Setting up vLLM Servers](../03_Vllm_Server/Vllm_Server.md)
- [Step 4: Performance Benchmarking](../04_Performance_Benchmarking/Performance_Benchmarking.md)
- [Step 5: Comparison](../05_Comparison/)

## Model Compression

Compress a Large Language Model (LLM) to reduce its size and computational cost while preserving as much accuracy as possible, enabling faster and more efficient deployment.

### Prerequisites

- Have enough resources for saving and loading a model. E.g., a model having 7 to 8 billion parameters takes around 14GB of memory to load.

### Procedure

1. Install dependencies

    ```text
        cd 01_Model_Compression
        pip install .

2. Open the [Model_Compression.ipynb](Model_Compression.ipynb) file in JupyterLab and follow the instructions directly in the notebook.

### Verification

You should be able to downlaod a model, compress it and verify that the compressed model is almost half the size of the base model.

## Next step

Proceed to [Step 2: Accuracy_Benchmarking.md](../02_Accuracy_Benchmarking/Accuracy_Benchmarking_README.md).
