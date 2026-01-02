# Step 3: Setting up vLLM servers for the Base and Compressed Models

## Navigation

- [Model Serving Overview](../README.md)
- [Step 1: Model Compression](../01_Model_Compression/Model_Compression.md)
- [Step 2: Accuracy Benchmarking](../02_Accuracy_Benchmarking/Accuracy_Benchmarking.md)
- Step 3: Setting up vLLM Servers
- [Step 4: Performance Benchmarking](../04_Performance_Benchmarking/Performance_Benchmarking.md)
- [Step 5: Comparison](../05_Comparison/)

## Setting up a vLLM Server

vLLM is used to host the base and compressed models and make them available for performance benchmarking in [Step 4](../04_Performance_Benchmarking/Performance_Benchmarking.md).

### Prerequisites

- The base model is compressed using the notebook  [Model_Compression.ipynb](../01_Model_Compression//Model_Compression.ipynb) in the Model_Compression step.

### Procedure

1. Install dependencies

    ```text
    cd ../03_Vllm_Server
    pip install .

2. Open the [Base.ipynb](Base.ipynb) file in JupyterLab and follow the instructions directly in the notebook. Once you run the `vllm server` command in the terminal, the base model will be accessible for inference and performance benchmarking.

3. To start up a server for the compressed model, follow the [Compressed.ipynb](Compressed.ipynb) notebook.

Note:

- Servers for both the models can be spun up together, given the resources are enough.
- If you are unable to start vLLM servers for both models together and are running into OOM errors, spin up a server for the base model and run performance benchmarking in Step 4 using the [Base.ipynb](../04_Performance_Benchmarking/Base.ipynb) notebook
- Before moving on to the compressed model, kill the server for the base model. Spin up a vLLM server for the Compressed model by follwoing the [Compressed.ipynb](Compressed.ipynb) notebook.
- Perform performance benchmarking for the compressed model using [Compressed.ipynb](../04_Performance_Benchmarking/Compressed.ipynb)

### Verification

Testing the server using `generate` and  `stream` methods should yield results.

## Next step

Proceed to [Step 4: Performance Benchmarking](../04_Performance_Benchmarking/Performance_Benchmarking_README.md).
