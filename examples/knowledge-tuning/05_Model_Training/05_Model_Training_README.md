# Module 5: Model Training

## Navigation

- [Knowledge Tuning Overview](../README.md)
- [Setup](../00_Setup/00_Setup_README.md)
- [Module 1: Base Model Evaluation](../01_Base_Model_Evaluation/01_Base_Model_Evaluation_README.md)
- [Module 2: Data Processing](../02_Data_Processing/02_Data_Processing_README.md)
- [Module 3: Knowledge Generation](../03_Knowledge_Generation/03_Knowledge_Generation_README.md)
- [Module 4: Knowledge Mixing](../04_Knowledge_Mixing/04_Knowledge_Mixing_README.md)
- Module 5: Model Training
- [Module 6: Evaluation](../06_Evaluation/06_Evaluation_README.md)

## Fine tuning the model

Ihe notebook in this module demonstrates how to fine-tune a student model by using the mixed datasets produced in Module 4. The following diagram illustrates the model training workflow.

![Model Training Flow Diagram](../../../assets/usecase/knowledge-tuning/Model%20Training.png)

### Prerequisites

- You completed the steps in [Module 4: Knowledge Mixing](../04_Knowledge_Mixing/04_Knowledge_Mixing_README.md).

- Your workbench is GPU-enabled for training, as described in [Setup](../00_Setup/00_Setup_README.md).

- The [.env.example](./.env.example) file sets the `STUDENT_MODEL` environment variable.

### Procedure

- In JupyterLab, open the [Model_Training.ipynb](./Model_Training.ipynb) file and follow the notebook instructions.

### Verification

The notebook generates the following artifacts:

- `output/step_05/checkpoints/` — Model checkpoints and training logs

## Debug & tips

- Monitor GPU memory if, for example, the model takes longer than expected to return a result. You can use the NVIDIA System Management Interface (nvidia-smi) command-line utility to monitor the GPU utilization to determine whether the model is using GPU memory.

## Next step

Proceed to [Module 6: Evaluation](../06_Evaluation/06_Evaluation_README.md).
