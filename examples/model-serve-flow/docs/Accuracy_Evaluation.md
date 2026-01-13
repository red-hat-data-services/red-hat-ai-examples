## Evaluate Accuracy of the Base and the Compressed Model

After compression, it is imperative to evaluate the accuracy of the compressed and base models on standard benchmarks to determine how compression affects its accuracy and generative quality relative to the base model.

For this purpose, `lm-evaluation-harness` is an open-source project that provides a unified framework to test generative language models on a large number of different evaluation tasks.

It computes key performance metrics such as:

- Accuracy / Score – Model correctness on benchmark tasks

- Per-task evaluation – Fine-grained insights into capabilities like reasoning or comprehension

It supports dozens of standard benchmarks, including MMLU, ARC etc. For our use case, we will be evaluating our base and compressed models on the follwoing tasks:

- MMLU: General knowledge across subjects.

- IFeval: Instruction-following tasks.

- ARC: Logical and scientific reasoning.

- HellaSwag: Commonsense completion.

### Evaluating the Compressed Model with `simple_evaluate`

`simple_evaluate` is the **main entry point** in LM Evaluation Harness to evaluate a model across one or multiple benchmark datasets. It handles:

1. Wrapping your model (or creating an LM object) to provide a **standardized interface**.
2. Preparing inputs and optionally applying **few-shot examples** or **chat/instruction templates**.
3. Running the model on benchmark tasks and collecting outputs.
4. Computing **evaluation metrics** (accuracy, accuracy_norm, etc.) for each task.
5. Returning a **results dictionary** that includes task-level metrics and model configuration info.

We have wrapped **simple_evaluate** in a helper function **evaluate** which can be found in [utils.py](utils.py).

**Key concepts:**

- **LM object**:
  LM Evaluation Harness wraps all models (Hugging Face, custom, or preloaded) in an `LM` object. This object provides a consistent interface (`loglikelihood`, `generate`, etc.) regardless of model backend.

- **model_args**:
  Optional dictionary or string containing model-specific arguments (e.g., temperature, top-k, top-p). Ignored if passing a pre-wrapped LM object.

- **apply_chat_template**:
  If your model is chat-based or instruction-following, this parameter allows you to prepend a prompt template to match the model's training format.

**Parameters used here:**

- `model`: Path or name of the model to evaluate (can be a string or an LM object).
- `model_args`: Optional dictionary to provide model-specific arguments (e.g., batch size, device).
- `tasks`: List of task names or objects to evaluate.
- `num_fewshot`: Number of examples in the few-shot context (set to 0 for zero-shot).
- `batch_size`: Number of samples to process per batch.
- `device`: Device to run the model on (e.g., "cuda" or "cpu").
- `apply_chat_template`: Whether to wrap inputs in a chat-style template; useful for chat or instruction-tuned models.
- `verbosity`: Set logging level; use `"DEBUG"` to inspect inputs/outputs for debugging. Default is None.
- `log_samples`: Whether to log per-sample outputs for inspection.

**NOTE**:

1. Running the evaluation on the entire list of tasks can take long. So for testing, you can use a single task instead.

2. The results will be stored as a **results.pkl** files in the directories defined by **compressed_results_dir** and **base_results_dir** paths in the [Base.ipynb](Base.ipynb) and [Compressed.ipynb](Compressed.ipynb) notebooks.
