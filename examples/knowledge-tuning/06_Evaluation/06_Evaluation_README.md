# Module 6: Evaluation

## Navigation

- [Knowledge Tuning Overview](../README.md)
- [Setup](../00_Setup/00_Setup_README.md)
- [Module 1: Base Model Evaluation](../01_Base_Model_Evaluation/01_Base_Model_Evaluation_README.md)
- [Module 2: Data Processing](../02_Data_Processing/02_Data_Processing_README.md)
- [Module 3: Knowledge Generation](../03_Knowledge_Generation/03_Knowledge_Generation_README.md)
- [Module 4: Knowledge Mixing](../04_Knowledge_Mixing/04_Knowledge_Mixing_README.md)
- [Module 5: Model Training](../05_Model_Training/05_Model_Training_README.md)
- Module 6: Evaluation

## Evaluate the trained model

In this module, the notebook evaluates trained models and generated datasets against held-out test data. It computes metrics and produces human-readable reports for quality assessment.

### Prerequisites

- You completed the steps in [Module 5: Model Training](../05_Model_Training/05_Model_Training_README.md).

- The [.env.example](./.env.example) file sets the `STUDENT_MODEL_NAME` environment variable to the name of the trained model.

### Procedure

- In JupyterLab, open the [Evaluation.ipynb](./Evaluation.ipynb) file and follow the notebook instructions.

### Verification

The notebook generates metrics and produces a quality assessment report.

## Next steps

Review metrics and iterate on earlier steps (data, generation, mixing, or training) as needed.
