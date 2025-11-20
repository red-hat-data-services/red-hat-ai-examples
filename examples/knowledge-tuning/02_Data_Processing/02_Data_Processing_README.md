
# Module 2: Data Processing

## Navigation

- [Knowledge Tuning Overview](../README.md)
- [Setup](../00_Setup/00_Setup_README.md)
- [Module 1: Base Model Evaluation](../01_Base_Model_Evaluation/01_Base_Model_Evaluation_README.md)
- Module 2: Data Processing
- [Module 3: Knowledge Generation](../03_Knowledge_Generation/03_Knowledge_Generation_README.md)
- [Module 4: Knowledge Mixing](../04_Knowledge_Mixing/04_Knowledge_Mixing_README.md)
- [Module 5: Model Training](../05_Model_Training/05_Model_Training_README.md)
- [Module 6: Evaluation](../06_Evaluation/06_Evaluation_README.md)

## Data processing and seed dataset generation

In this module, you convert a data source (an example URL) into a small, curated seed dataset that is suitable for Synthetic Data Generation (SDG). The Jupyter notebook for this module uses [docling](https://www.docling.ai/) to convert the URL content to JSON format, chunk the converted data, select representative chunks, and generate initial question and answer (Q&A) pairs.

![Data Preprocessing Flow Diagram](../../../assets/usecase/knowledge-tuning/Data%20Preprocessing.png)

### Prerequisites

- You completed the steps in [Module 1: Base Model Evaluation](../01_Base_Model_Evaluation/01_Base_Model_Evaluation_README.md).


### Procedure

- In JupyterLab, open the [Data_Processing.ipynb](./Data_Processing.ipynb) file and follow the notebook instructions.

### Verification

The notebook generates the following artifacts:

- `output/step_02/docling_output/` — A directory that contains the JSON files output by Docling.
- `output/step_02/chunks.jsonl` — A file that contains all of the chunks.
- `output/step_02/seed_data.jsonl` — A file that contains the final seed dataset.

## Next step

Proceed to [Module 3: Knowledge Generation](../03_Knowledge_Generation/03_Knowledge_Generation_README.md).
