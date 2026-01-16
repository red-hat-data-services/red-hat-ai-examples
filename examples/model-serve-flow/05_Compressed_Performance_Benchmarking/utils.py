from openai import OpenAI


def generate(
    model: str,
    prompt: str,
    host: str = "127.0.0.1",
    port: int = 8000,
    api_key: str = "empty",
    max_tokens: int = 256,
    seed: int = 42,
    temperature=0.7,
):
    """
    Query a locally running vLLM server using the OpenAI-compatible API.

    Parameters
    ----------
    model : str
        Path to the model served by vLLM (the folder name of the compressed model).
    prompt : str
        The input text prompt to send to the model.
    host : str, optional
        Host where the vLLM server is running. Defaults to "127.0.0.1".
    port : int, optional
        Port where the vLLM server is listening. Defaults to 8000.
    api_key : str, optional
        API key for authentication. Defaults to "empty".
    max_tokens : int, optional
        Maximum number of tokens to generate. Defaults to 256.
    seed : int, optional
        Seed for reproducible sampling. Defaults to 42.
    temperature : float, optional
        Sampling temperature for generation. Defaults to 0.7.

    Returns
    -------
    str
        The assistant's generated text.
    """

    # Construct the OpenAI-compatible base URL internally
    base_url = f"http://{host}:{port}/v1"

    # initialize an OpenAI client
    llm = OpenAI(base_url=base_url, api_key=api_key)

    messages = [{"role": "system", "content": "You are a helpful assistant."}]
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


def stream(
    model: str,
    prompt: str,
    host: str = "127.0.0.1",
    port: int = 8000,
    api_key: str = "empty",
    max_tokens: int = 256,
    seed: int = 42,
    temperature=0.7,
):
    """Stream response token by token.
    Args:
    ----------
    model : str
        Path to the model served by vLLM (the folder name of the compressed model).
    prompt : str
        The input text prompt to send to the model.
    host : str, optional
        Host where the vLLM server is running. Defaults to "127.0.0.1".
    port : int, optional
        Port where the vLLM server is listening. Defaults to 8000.
    api_key : str, optional
        API key for authentication. Defaults to "empty".
    max_tokens : int, optional
        Maximum number of tokens to generate. Defaults to 256.
    seed : int, optional
        Seed for reproducible sampling. Defaults to 42.
    temperature : float, optional
        Sampling temperature for generation. Defaults to 0.7.

    yields: str: Yields response token by token.
    """
    base_url = f"http://{host}:{port}/v1"
    llm = OpenAI(base_url=base_url, api_key=api_key)

    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    user_message = {"role": "user", "content": prompt}
    messages.append(user_message)

    stream = llm.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
        stream=True,
    )
    for chunk in stream:
        if content := chunk.choices[0].delta.content:
            yield content
