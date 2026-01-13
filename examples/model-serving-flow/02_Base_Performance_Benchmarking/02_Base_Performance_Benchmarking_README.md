# Step 4: Evaluating System Level Performance of the Base and Compressed Models

## Navigation

- [Model Serving Overview](../README.md)
- [Step 1: Base Accuracy Benchmarking](../01_Base_Accuracy_Benchmarking/)
- Step 2: Base Performance Benchmarking
- [Step 3: Model Compression](../03_Model_Compression/)
- [Step 4: Base Accuracy Benchmarking](../04_Compressed_Accuracy_Benchmarking/)
- [Step 5: Compressed Performance Benchmarking](../05_Compressed_Performance_Benchmarking/)
- [Step 6: Comparison](../06_Comparison)
- [Step 7: Model Deployment](../07_Deployment)

## Performance Benchmarking

Use GuideLLM to run performance benchmarking on the base model. The results from benchmarking the base and compressed models are later compared in [Step 6: Comparison](../06_Comparison/Performance_Comparison.md).

### Prerequisites

- A base model (RedHatAI/Llama-3.1-8B-Instruct) has been downloaded and saved in [base_model](../base_model) folder.

### Procedure

1. ```text
        cd ../02_Base_Performance_Benchmarking

2. Open the [Base.ipynb](Base.ipynb) file in JupyterLab and follow the instructions directly in the notebook. This will give results for the base model.

### Verification

- A vLLM server hosting the base model has started
- Performance metrics have been saved in the [results](../results) folder

## Next step

Proceed to [Step 3: Model Compression](../03_Model_Compression/03_Model_Compression_README.md).
