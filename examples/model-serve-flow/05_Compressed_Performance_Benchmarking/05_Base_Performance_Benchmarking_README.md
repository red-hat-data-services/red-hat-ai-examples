# Step 5: Evaluating System Level Performance of the Compressed Model

## Navigation

- [Model Serving Overview](../README.md)
- [Step 1: Base Accuracy Benchmarking](../01_Base_Accuracy_Benchmarking/)
- [Step 2: Base Performance Benchmarking](../02_Base_Performance_Benchmarking/)
- [Step 3: Model Compression](../03_Model_Compression/)
- [Step 4: Base Accuracy Benchmarking](../04_Compressed_Accuracy_Benchmarking/)
- Step 5: Compressed Performance Benchmarking
- [Step 6: Comparison](../06_Comparison)
- [Step 7: Model Deployment](../07_Deployment)

## Performance Benchmarking

Use GuideLLM to run performance benchmarking on the compressed model. The results from benchmarking the compressed and base models are later compared in [Step 6: Comparison](../06_Comparison/Performance_Comparison.md).

### Prerequisites

- A base model (RedHatAI/Llama-3.1-8B-Instruct) has been compressed and saved

### Procedure

1. ```text
        cd ../05_Compressed_Performance_Benchmarking

2. Open the [Compressed.ipynb](Compressed.ipynb) file in JupyterLab and follow the instructions directly in the notebook. This will give results for the base model.

### Verification

- A vLLM server hosting the base model has started
- Performance metrics have been saved in the [results](../results) folder

## Next step

Proceed to [Step 6: Comparison](../06_Comparison) and finally, got to [Step 7: Model Deployment](../07_Deployment) for deploying the compressed model.
