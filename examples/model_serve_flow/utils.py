import os, pickle
from typing import Union
from openai import OpenAI
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
    size_gb =  total / (1024 * 1024 * 1024)  # GB
    # try:
    #     dtype = next(model.parameters()).dtype
    # except StopIteration:
    #     dtype = None
    return size_gb


def tokenize_for_calibration(
    examples,
    input_column,
    tokenizer,
    max_length,
    model_type="general",
    custom_template=None  # dictionary with 'text' and 'mapping'
):
    """
    Tokenize dataset text examples for use in GPTQ / LM Compressor calibration.
    
    This function prepares text inputs according to the expected prompting format
    of different model types (general, chat, instruction, code). Calibration text
    should resemble the inputs the model will see in real usage so that activation
    statistics are accurate for quantization.
    
    Behavior:
    - If a custom template dictionary (`custom_template`) is provided, the template text
      is applied to each example using the specified placeholder.
    - If `custom_template` is not provided, a default template is selected based on
      `model_type` using predefined mappings.
    - For general-purpose models, the default template is raw text (`"{text}"`).
    - For chat, instruction, or code models, structured templates are applied 
      (e.g., "User: ...\nAssistant:", instruction headers, or code docstring format).
    - Only a single column from the dataset is required for calibration; the placeholder
      in the template is filled with values from this column.
    
    Args:
        examples (dict):
            A batch from a Hugging Face dataset.
        column (str):
            Name of the column that contains text to be used for calibration.
        tokenizer (transformers.PreTrainedTokenizerBase):
            The tokenizer associated with the model being calibrated.
        max_length (int):
            Maximum sequence length for truncation/padding during tokenization.
        model_type (str, optional):
            Type of model input format to use when no custom template is provided. One of:
                - "general": raw text (default)
                - "chat": conversational prompt format
                - "instruction": instruction-following format
                - "code": code generation format
        custom_template (dict, optional):
            A dictionary specifying a custom template for calibration. Must contain:
                - 'template_text': the template string containing a placeholder
                - 'placeholder': the name of the placeholder in the template string
            Example:
                custom_template = {
                    "template_text": "Instruction: {content}\nOutput:",
                    "placeholder": "content"
                }
            If provided, this template is used instead of the default template.
    
    Returns:
        dict:
            A dictionary containing tokenized fields (e.g., "input_ids",
            "attention_mask") compatible with LM Compressor / GPTQ calibration.
    """
    
    
    DEFAULT_TEMPLATES = {
    "general": "{text}",
    "chat": "User: {text}\nAssistant:",    
    "instruction": (
        "Instruction: {text}\n"
        "Input:\n"
        "Output:"
    ),
    "code": (
        "# Task description:\n"
        "{text}\n"
        "# Solution:"
    )
    }
    tokenizer.pad_token = tokenizer.eos_token    
    try:
        texts = examples[input_column]
        if isinstance(texts, str):
            texts = [texts] # huggingface tokenizer expects a list 
    except (KeyError, TypeError):
        raise ValueError(
            f"Expected `examples` to contain a {column} field. "
            f"Please ensure your dataset has a {column} column."
        )
    
    # Choose template: user-defined or default
    if custom_template is None:
        # Use default template
        template = DEFAULT_TEMPLATES.get(model_type, "{text}")
        placeholder = "text"
    else:
        # use custom template
        if not isinstance(custom_template, dict) or \
        "template_text" not in custom_template or \
        "placeholder" not in custom_template:
            raise ValueError(
                "custom_template must be a dict containing keys 'template_text' and 'placeholder'."
            )
        template = custom_template["template_text"]
        placeholder = custom_template.get("placeholder")
    
    
    if custom_template is not None:
        # check if the provided place holder exists in the custom template
        if "{" + placeholder + "}" not in template:
            raise ValueError(
                f"Custom template does not contain placeholder {{{placeholder}}}"
            )
    # apply template
    texts = [template.format(**{placeholder: text}) for text in texts]
    
            
            
    # Tokenize
    return tokenizer(
        texts,
        truncation=True,
        max_length=max_length,
        padding="max_length"
    )


def generate(model: str, 
             prompt: str,
             host: str = "127.0.0.1",
             port: int = 8000,             
             api_key: str = "empty",
             max_tokens: int = 256,
             seed: int = 42,
             temperature = 0.7
            ):
    """
    Query a locally running vLLM server using the OpenAI-compatible API.

    Parameters
    ----------
    model : str
        Name of the model served by vLLM (the folder name of the compressed model).
    messages : list[dict]
        Chat messages in OpenAI format: [{"role": "user", "content": "..."}]
    host : str, optional
        Host where the vLLM server is running. Defaults to "127.0.0.1".
    port : int, optional
        Port where the vLLM server is listening. Defaults to 8000.
    temperature : float, optional
        Sampling temperature for generation.
    max_tokens : int, optional
        Maximum number of tokens to generate.
    seed : int or None, optional
        Seed for reproducible sampling.

    Returns
    -------
    str
        The assistant's generated text.
    """

    # Construct the OpenAI-compatible base URL internally
    base_url = f"http://{host}:{port}/v1"
    
    # initialize an OpenAI client
    llm = OpenAI(base_url=base_url, api_key=api_key)

    messages = [{"role": "system", "content": "You are a helpful assistan."}]
    user_message = {"role": "user", "content": prompt}
    messages.append(user_message)

    # Make request
    response = llm.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
    )

    return response.choices[0].message.content

def extract_task_metrics(results):
    """
    Extracts per-task metrics from the 'results' section of an lm-eval result JSON.
    Removes only the 'alias' key and keeps everything else.
    """

    task_results = results.get("results", {})
    cleaned = {}

    for task_name, metrics in task_results.items():
        # Create a new dictionary excluding the "alias" key
        cleaned_metrics = {
            key: value
            for key, value in metrics.items()
            if key != "alias"
        }

        cleaned[task_name] = cleaned_metrics

    return cleaned

import pandas as pd

def evaluate(
    model_path: str,
    tasks: list[str],
    model: str = "hf",
    num_fewshot: int = 0,
    device: str = None,
    limit: Union[int, float, None] = None,
    apply_chat_template: bool = False,
    verbosity: str = None,                       
    log_samples: bool = False,
    batch_size: Union[int, str] = None   
):
   
    """
    Evaluate a language model on specified tasks using lm-eval-harness.

    Parameters
    ----------
    model_path : str
        Path to the pretrained model or HuggingFace model.
    tasks : list[str]
        List of task names to evaluate.
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
    
    if device is None: # check device
        device = "cuda" if torch.cuda.is_available() else "cpu" 
    if limit is None:
        limit = None if device=="cuda" else 4
    if batch_size is None:
        batch_size = "auto" if device=="cuda" else 4
        
    model_args={"pretrained": model_path}

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
                batch_size=batch_size                                         
            )
    except Exception as e:
            raise RuntimeError(f"Could not run accuracy evaluation : {e}")
        
    return results
                             
def save_pickle(path, data):
    os.makedirs(path, exist_ok=True)
    with open(f"{path}/results.pkl", "wb") as f:
        pickle.dump(data, f)

def load_pickle(path):
    with open(f"{path}/results.pkl", "rb") as f:
        return pickle.load(f)