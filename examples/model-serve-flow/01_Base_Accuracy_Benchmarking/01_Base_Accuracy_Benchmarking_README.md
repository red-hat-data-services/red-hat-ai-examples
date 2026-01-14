# Step 1: Evaluating Accuracy of Base Model

## Navigation

- [Model Serving Overview](../README.md)
- [Step 0: 00_Setup](../00_Setup/00_Setup_README.md)
- Step 1: Base Accuracy Benchmarking
- [Step 2: Base Performance Benchmarking](../02_Base_Performance_Benchmarking/02_Base_Performance_Benchmarking_README.md)
- [Step 3: Model Compression](../03_Model_Compression/03_Model_Compression_README.md)
- [Step 4: Base Accuracy Benchmarking](../04_Compressed_Accuracy_Benchmarking/04_Compressed_Accuracy_Benchmarking_README.md)
- [Step 5: Compressed Performance Benchmarking](../05_Compressed_Performance_Benchmarking/05_Base_Performance_Benchmarking_README.md)
- [Step 6: Comparison](../06_Comparison)
- [Step 7: Model Deployment](../07_Deployment)

## Accuracy Benchmarking

This step will use lm_eval to run accuracy benchmarking on the base model. The results from benchmarking the base model will be used as a reference/baseline to compare the results of the compressed model.

### Prerequisites

- Have enough resources for saving and loading a model. E.g., a model having 7 to 8 billion parameters takes around 14GB of memory to load.

### Procedure

1. ```text
    cd ../01_Base_Accuracy_Benchmarking

2. Open the [Base.ipynb](Base.ipynb) file in JupyterLab and follow the instructions directly in the notebook. This will give results for the base model.

### Verification

A model should be downlaoded and saved in the `model-serve-flow/base_model/` folder. All cells should run successfully. Results for the base model accuracy should be saved in the `model-serve-flow/results/` folder.

## Next step

Proceed to [Step 2: Base Performance Benchmarking](../02_Base_Performance_Benchmarking/02_Base_Performance_Benchmarking_README.md).
