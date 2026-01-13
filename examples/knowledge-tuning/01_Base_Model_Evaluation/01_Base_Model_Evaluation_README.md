
# Module 1: Base Model Evaluation

## Navigation

- [Knowledge Tuning Overview](../README.md)
- [Setup](../00_Setup/00_Setup_README.md)
- Module 1: Base Model Evaluation
- [Module 2: Data Processing](../02_Data_Processing/02_Data_Processing_README.md)
- [Module 3: Knowledge Generation](../03_Knowledge_Generation/03_Knowledge_Generation_README.md)
- [Module 4: Knowledge Mixing](../04_Knowledge_Mixing/04_Knowledge_Mixing_README.md)
- [Module 5: Model Training](../05_Model_Training/05_Model_Training_README.md)
- [Module 6: Evaluation](../06_Evaluation/06_Evaluation_README.md)

## Evaluate the base model

In the Teacher-Student model paradigm, the student model is also known as the base model. Before you train a base model, evaluate it's preliminary performance. Later, after you train the model with your data, you can objectively compare how effective the knowledge tuning tasks are for customizing the model.

### Prerequisites

- You completed the [Setup](../00_Setup/00_Setup_README.md) steps.

- Verify that the following environment variable is set in the [.env.example](./.env.example) file:

  - `STUDENT_MODEL_NAME` — Model name

### Procedure

- In JupyterLab, open the [Base_Model_Evaluation.ipynb](./Base_Model_Evaluation.ipynb) file and follow the notebook instructions.

### Verification

You completed the base model evaluation.

## Next step

Proceed to [Module 2: Data Processing](../02_Data_Processing/02_Data_Processing_README.md).
