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


def tokenize_for_calibration(
    examples,
    input_column,
    tokenizer,
    max_length,
    model_type="general",
    custom_template=None,  # dictionary with 'text' and 'mapping'
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
        input_column (str):
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
        "instruction": ("Instruction: {text}\nInput:\nOutput:"),
        "code": ("# Task description:\n{text}\n# Solution:"),
    }
    tokenizer.pad_token = tokenizer.eos_token
    try:
        texts = examples[input_column]
        if isinstance(texts, str):
            texts = [texts]  # huggingface tokenizer expects a list
    except (KeyError, TypeError) as err:
        raise ValueError(
            f"Expected `examples` to contain a {input_column} field. "
            f"Please ensure your dataset has a {input_column} column."
        ) from err

    # Choose template: user-defined or default
    if custom_template is None:
        # Use default template
        template = DEFAULT_TEMPLATES.get(model_type, "{text}")
        placeholder = "text"
    else:
        # use custom template
        if (
            not isinstance(custom_template, dict)
            or "template_text" not in custom_template
            or "placeholder" not in custom_template
        ):
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
        texts, truncation=True, max_length=max_length, padding="max_length"
    )
