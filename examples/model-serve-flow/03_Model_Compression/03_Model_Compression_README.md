# Step 1: Compress a LLM to INT8

## Navigation

- [Model Serving Overview](../README.md)
- [Step 1: Base Accuracy Benchmarking](../01_Base_Accuracy_Benchmarking/)
- [Step 2: Base Performance Benchmarking](../02_Base_Performance_Benchmarking/)
- Step 3: Model Compression
- [Step 4: Base Accuracy Benchmarking](../04_Compressed_Accuracy_Benchmarking/)
- [Step 5: Compressed Performance Benchmarking](../05_Compressed_Performance_Benchmarking/)
- [Step 6: Comparison](../06_Comparison)
- [Step 7: Model Deployment](../07_Deployment)

## Model Compression

Compress a Large Language Model (LLM) to reduce its size and computational cost while preserving as much accuracy as possible, enabling faster and more efficient deployment.

### Prerequisites

- A base model (RedHatAI/Llama-3.1-8B-Instruct) has been downloaded and saved in [base_model](../base_model) folder.
- Have enough resources for saving and loading a model. E.g., a model having 7 to 8 billion parameters takes around 14GB of memory to load.

### Procedure

1. ```text
        cd 01_Model_Compression

2. Open the [Model_Compression.ipynb](Model_Compression.ipynb) file in JupyterLab and follow the instructions directly in the notebook.

### Verification

You should be able to compress the base model and verify that the compressed model is almost half the size of the base model.

## Next step

Proceed to [Step 4: Base Accuracy Benchmarking](../04_Compressed_Accuracy_Benchmarking/04_Compressed_Accuracy_Benchmarking_README.md)
