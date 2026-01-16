# Step 4: Evaluating Accuracy of the Compressed Model

## Navigation

- [Model Serving Overview](../README.md)
- [Step 0: 00_Setup](../00_Setup/00_Setup_README.md)
- [Step 1: Base Accuracy Benchmarking](../01_Base_Accuracy_Benchmarking/01_Base_Accuracy_Benchmarking_README.md)
- [Step 2: Base Performance Benchmarking](../02_Base_Performance_Benchmarking/02_Base_Performance_Benchmarking_README.md)
- [Step 3: Model Compression](../03_Model_Compression/03_Model_Compression_README.md)
- Step 4: Base Accuracy Benchmarking
- [Step 5: Compressed Performance Benchmarking](../05_Compressed_Performance_Benchmarking/05_Base_Performance_Benchmarking_README.md)
- [Step 6: Comparison](../06_Comparison)
- [Step 7: Model Deployment](../07_Deployment)

## Accuracy Benchmarking

This step will use lm_eval to run accuracy benchmarking on the compressed model. The results from benchmarking the compressed model will be compared against the baseline developed by the base model.

### Prerequisites

- The base model has been compressed successfully.

### Procedure

1. ```text
    cd ../04_Compressed_Accuracy_Benchmarking

2. Open the [Compressed_Accuracy_Benchmarking.ipynb](Compressed_Accuracy_Benchmarking.ipynb) file in JupyterLab and follow the instructions directly in the notebook. This will give results for the base model.

### Verification

Results for the compressed model accuracy should be saved in the `model-serve-flow/results/` folder.

## Next step

Proceed to [Step 5: Compressed Performance Benchmarking](../05_Compressed_Performance_Benchmarking_README.md).
