# Module 4: Knowledge Mixing

## Navigation

- [Knowledge Tuning Overview](../README.md)
- [Setup](../00_Setup/00_Setup_README.md)
- [Module 1: Base Model Evaluation](../01_Base_Model_Evaluation/01_Base_Model_Evaluation_README.md)
- [Module 2: Data Processing](../02_Data_Processing/02_Data_Processing_README.md)
- [Module 3: Knowledge Generation](../03_Knowledge_Generation/03_Knowledge_Generation_README.md)
- Module 4: Knowledge Mixing
- [Module 5: Model Training](../05_Model_Training/05_Model_Training_README.md)
- [Module 6: Evaluation](../06_Evaluation/06_Evaluation_README.md)

## Knowledge mixing and preparing training mixes

This module mixes generated Q&A, extractive/detailed summaries, and other artifacts into training-ready datasets. It prepares different cut sizes and mixes (upsampling, downsampling) that are consumed by model training workflows.

![Knowledge Mixing Flow Diagram](../../../assets/usecase/knowledge-tuning/Knowledge%20Mixing.png)

### Prerequisites

- You completed the steps in [Module 3: Knowledge Generation](../03_Knowledge_Generation/03_Knowledge_Generation_README.md).

- The `output/step_03/*` folder contains the summary folders generated from the module 3 notebook.

- The following environment variables are set in the [.env.example](./.env.example) file:

  - `TOKENIZER_MODEL` — A valid tokenizer model for counting tokens. The tokenizer must be compatible with `transformers`.
  - `SAVE_GPT_OSS_FORMAT` — A Boolean value that specifies whether to save the output in GPT-OSS format. The default (e.g. `false`)
  - `CUT_SIZES` — A comma-separated list of cut sizes to generate. For example: `10,20`
  - `QA_PER_DOC` — The number of Q&A pairs to save in each document.

### Procedure

1. In JupyterLab, open the [Knowledge_Mixing.ipynb](./Knowledge_Mixing.ipynb) file and follow the notebook instructions.

### Verification

The notebook generates the following artifacts:

- `output/step_04/combined_cut_{N}x.jsonl` — Mixed datasets for each cut size.

## Debug & tips

- If token counting fails, ensure `TOKENIZER_MODEL` points to a valid tokenizer compatible with `transformers`.

## Next steps

In this Knowledge Tuning example, the output training dataset is small enough for training and you can proceed to [Module 5: Model Training](../05_Model_Training/05_Model_Training_README.md).

**NOTE:** In a use case where the output dataset is too large for training (for example, 1 million samples), your next step would be to identify representative samples subsets of the data as illustrated in [the example Subset Selection for Dataset Diversity notebook](https://github.com/opendatahub-io/data-processing/blob/main/notebooks/use-cases/subset-selection.ipynb).
