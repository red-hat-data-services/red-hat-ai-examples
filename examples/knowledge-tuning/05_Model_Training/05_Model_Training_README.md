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

Ihe notebook in this module demonstrates how to fine-tune or instruction-tune a student model by using the mixed datasets produced in Module 3. The following diagram illustrates the model training workflow.

![Model Training Flow Diagram](../../../assets/usecase/knowledge-tuning/Model%20Training.png)

You can train the student model on a GPU-enabled workbench or on a training cluster.

### Prerequisites

- You completed the steps in [Module 4: Knowledge Mixing](../04_Knowledge_Mixing/04_Knowledge_Mixing_README.md).

- Your workbench is GPU-enabled for training as described in [Setup](../00_Setup/00_Setup_README.md) for details.

- Verify that the [.env.example](./.env.example) file sets the following environment variable:

#### Environment variables

- `STUDENT_MODEL` — The model that you want to train.

### Procedure

- In JupyterLab, open the [Model_Training.ipynb](./Model_Training.ipynb) file and follow the notebook instructions or run your training script/entrypoint.

### Verification

The notebook generates the following artifacts:

- `output/step_05/checkpoints/` — Model checkpoints and training logs

## Debug & tips

- Monitor GPU memory, if needed.

## Next step

Proceed to [Module 6: Evaluation](../06_Evaluation/06_Evaluation_README.md).
