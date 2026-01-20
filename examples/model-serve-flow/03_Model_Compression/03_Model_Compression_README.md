# Step 3: Compress the Base Model to INT8

## Navigation

- [Model Serving Overview](../README.md)
- [Step 0: 00_Setup](../00_Setup/00_Setup_README.md)
- [Step 1: Base Accuracy Benchmarking](../01_Base_Accuracy_Benchmarking/01_Base_Accuracy_Benchmarking_README.md)
- [Step 2: Base Performance Benchmarking](../02_Base_Performance_Benchmarking/02_Base_Performance_Benchmarking_README.md)
- Step 3: Model Compression
- [Step 4: Base Accuracy Benchmarking](../04_Compressed_Accuracy_Benchmarking/04_Compressed_Accuracy_Benchmarking_README.md)
- [Step 5: Compressed Performance Benchmarking](../05_Compressed_Performance_Benchmarking/05_Base_Performance_Benchmarking_README.md)
- [Step 6: Comparison](../06_Comparison)
- [Step 7: Model Deployment](../07_Deployment)

## Model Compression

Compress a Large Language Model (LLM) to reduce its size and computational cost while preserving as much accuracy as possible, enabling faster and more efficient deployment.

### Prerequisites

- A base model (RedHatAI-Llama-3.1-8B-Instruct) has been downloaded and saved in `model-serve-flow/base_model/` folder.
- Have enough resources for saving and loading a model. E.g., a model having 7 to 8 billion parameters takes around 14GB of memory to load.

### Procedure

1. ```text
        cd 01_Model_Compression

2. Open the [Model_Compression.ipynb](Model_Compression.ipynb) file in JupyterLab and follow the instructions directly in the notebook.

### Verification

- You should be able to compress the base model and verify that the compressed model is almost half the size of the base model.
- A compressed model (RedHatAI-Llama-3.1-8B-Instruct-int8-dynamic) should be saved in `model-serve-flow/compressed_model` directory.

## Next step

Proceed to [Step 4: Base Accuracy Benchmarking](../04_Compressed_Accuracy_Benchmarking/04_Compressed_Accuracy_Benchmarking_README.md)
