# Step 2: Evaluating Accuracy of a Model

## Navigation

- [Model Serving Overview](../README.md)
- [Step 1: Model Compression](../01_Model_Compression/Model_Compression.md)
- Step 2: Accuracy Benchmarking
- [Step 3: Setting up vLLM Servers](../03_Vllm_Server/Vllm_Server.md)
- [Step 4: Performance Benchmarking](../04_Performance_Benchmarking/Performance_Benchmarking.md)
- [Step 5: Comparison](../05_Comparison/)

## Accuracy Benchmarking

Use lm_eval to run accuracy benchmarking on the base and compressed models. The results from benchmarking the base model will be used as a reference/baseline to compare the results of the compressed model.

### Prerequisites

- The base model is compressed using the notebook in previous step [Model_Compression.ipynb](../01_Model_Compression//Model_Compression.ipynb)

### Procedure

1. Install dependencies

    ```text
    cd ../02_Accuracy_Benchmarking
    pip install .

2. Open the [Base.ipynb](Base.ipynb) file in JupyterLab and follow the instructions directly in the notebook. This will give results for the base model.

3. For running accuracy benchmarking on the compressed model, open the [Compressed.ipynb](Compressed.ipynb) notebook and run the cells.

### Verification

All cells should run successfully and base and compressed accuracy results should be saved in the `results` folder.

## Next step

Proceed to [Step 3: vLLM_Server](../03_Vllm_Server/Vllm_Server.md).
