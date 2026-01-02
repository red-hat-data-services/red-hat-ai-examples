# Step 4: Evaluating System Level Performance of the Base and Compressed Models

## Navigation

- [Model Serving Overview](../README.md)
- [Step 1: Model Compression](../01_Model_Compression/Model_Compression.md)
- [Step 2: Accuracy Benchmarking](../02_Accuracy_Benchmarking/Accuracy_Benchmarking.md)
- [Step 3: Setting up vLLM Servers](../03_Vllm_Server/Vllm_Server.md)
- Step 4: Performance Benchmarking
- [Step 5: Comparison](../05_Comparison/)

## Performance Benchmarking

Use GuideLLM to run performance benchmarking on the base and compressed models. The results from benchmarking the base and compressed models are later compared in [Step 5: Comparison](../05_Comparison/Performance_Comparison.md).

### Prerequisites

- The base model is compressed using the notebook in previous step [Model_Compression.ipynb](../01_Model_Compression//Model_Compression.ipynb)

- vLLM server for the model under question is running.

### Procedure

1. Install dependencies

    ```text
        cd ../04_Performance_Benchmarking
        pip install .

2. Open the [Base.ipynb](Base.ipynb) file in JupyterLab and follow the instructions directly in the notebook. This will give results for the base model.

3. For running performance benchmarking on the compressed model, open the [Compressed.ipynb](Compressed.ipynb) notebook and run the cells.

### Verification

Results will be saved in the `results` folder.

## Next step

Proceed to [Step 5: Comparison](../05_Comparison) for [accuracy comparison](../05_Comparison/Accuracy_Comparison.md) and [performance comparison](../05_Comparison/Performance_Comparison.md).
