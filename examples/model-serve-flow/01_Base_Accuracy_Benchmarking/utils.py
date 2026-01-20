import os
import pickle
from typing import Union

import torch
from lm_eval.evaluator import simple_evaluate


def model_size_gb(model):
    """
    Compute the model's size in gigabytes and return its parameter dtype.

    Returns:
        (float): Total size of all model parameters in GB.
        (torch.dtype | None): Data type of the model parameters, or None if empty.
    """
    total = 0
    for param in model.parameters():
        total += param.nelement() * param.element_size()
    size_gb = total / (1024 * 1024 * 1024)  # GB

    return size_gb


def evaluate(
    model_path: str,
    tasks: list[str] = ["mmlu"],
    model: str = "hf",
    num_fewshot: int = 0,
    device: str = None,
    limit: Union[int, float, None] = None,
    apply_chat_template: bool = False,
    verbosity: str = None,
    log_samples: bool = False,
    batch_size: Union[int, str] = None,
):
    """
    Evaluate a language model on specified tasks using lm-eval-harness.

    Parameters
    ----------
    model_path : str
        Path to the pretrained model or HuggingFace model.
    tasks : list[str]
        List of task names to evaluate. Defaults to ["mmlu"].
    model : str, default "hf"
        Selects which model type or provider is evaluated. default is "hf".
    num_fewshot : int, default 0
        Number of few-shot examples per task (0 for zero-shot).
    device : str or None, default None
        Device to run evaluation on ("cpu" or "cuda"). Auto-detected if None.
    limit : int, float, or None, default None
        Limit number of documents per task (int for count, float for fraction).
    apply_chat_template : bool, default False
        When True, adjusts delimiter handling for chat-style prompts:
        sets the target delimiter to an empty string instead of the default whitespace.
        Useful for likelihood or multiple-choice tasks with chat models to prevent
        spacing issues between context and target. Does NOT apply a full chat template.
    verbosity : str, default "DEBUG"
        Level of logging for inputs and outputs. Can be set to None
    log_samples : bool, default False
        Whether to save sample outputs for debugging.

    Returns
    -------
    dict
        Evaluation results from simple_evaluate.
    """

    cuda_available = torch.cuda.is_available()

    device = (device or "").lower()
    device = (
        device if device in {"cpu", "cuda"} else ("cuda" if cuda_available else "cpu")
    )
    if device == "cuda" and not cuda_available:
        device = "cpu"

    if limit is None:
        limit = None if device == "cuda" else 4
    if batch_size is None:
        batch_size = "auto" if device == "cuda" else 4

    model_args = {"pretrained": model_path}

    try:
        results = simple_evaluate(
            model=model,
            model_args=model_args,
            tasks=tasks,
            num_fewshot=num_fewshot,
            limit=limit,
            device=device,
            apply_chat_template=apply_chat_template,
            verbosity=verbosity,
            log_samples=log_samples,
            batch_size=batch_size,
        )
    except Exception as e:
        raise RuntimeError(f"Could not run accuracy evaluation: {e}") from e

    return results


def save_pickle(path, data):
    os.makedirs(path, exist_ok=True)
    with open(f"{path}/results.pkl", "wb") as f:
        pickle.dump(data, f)


def load_pickle(path):
    with open(f"{path}/results.pkl", "rb") as f:
        return pickle.load(f)
