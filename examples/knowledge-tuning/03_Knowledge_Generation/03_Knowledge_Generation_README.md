
# Module 3: Knowledge Generation

## Navigation

- [Knowledge Tuning Overview](../README.md)
- [Setup](../00_Setup/00_Setup_README.md)
- [Module 1: Base Model Evaluation](../01_Base_Model_Evaluation/01_Base_Model_Evaluation_README.md)
- [Module 2: Data Processing](../02_Data_Processing/02_Data_Processing_README.md)
- Module 3: Knowledge Generation
- [Module 4: Knowledge Mixing](../04_Knowledge_Mixing/04_Knowledge_Mixing_README.md)
- [Module 5: Model Training](../05_Model_Training/05_Model_Training_README.md)
- [Module 6: Evaluation](../06_Evaluation/06_Evaluation_README.md)

## Knowledge generation and expanding seed dataset into Q&A

This module expands the curated seed examples produced in the previous step into a larger set of Q&A pairs using LLMs and local utilities. It can be used to produce synthetic training examples or to augment existing datasets.

![Knowledge Generation Flow Diagram](../../../assets/usecase/knowledge-tuning/Knowledge%20Genertaion.png)

### Prerequisites

- You completed the steps in [Module 2: Data Processing](../02_Data_Processing/02_Data_Processing_README.md).

- You have access to an LLM endpoint.

- Verify that the following environment variables are set in the [.env.example](./.env.example) file:
  - `TEACHER_MODEL_API_KEY` — The LLM API key.
  - `TEACHER_MODEL_BASE_URL` — The LLM HTTP endpoint.
  - `TEACHER_MODEL_NAME` — The model to call for data generation.

### Procedure

1. Open the [Knowledge_Generation.ipynb](./Knowledge_Generation.ipynb) file in JupyterLab and follow the notebook instructions.

### Verification

The notebook generates the following artifact:

- `output/step_03/**/gen.jsonl` — This file contains the raw generation output for
  - Extractive summary
  - Detailed summary
  - Key facts Q&A
  - Document based Q&A

## Debug & tips

- If generation fails, check that the values for the API key, endpoint URL, and request rate limits environment variables are correct.

## Next step

Proceed to [Module 4: Knowledge Mixing](../04_Knowledge_Mixing/04_Knowledge_Mixing_README.md).
