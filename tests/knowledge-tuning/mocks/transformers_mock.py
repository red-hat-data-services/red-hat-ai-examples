"""Mock classes for HuggingFace transformers."""

from unittest.mock import MagicMock


class MockTokenizer:
    """Mock tokenizer for testing."""

    def __init__(self):
        self.vocab = {"<pad>": 0, "<unk>": 1, "test": 2, "token": 3}

    def encode(self, text: str) -> list[int]:
        """Mock encode method."""
        # Simple mock: return list of token IDs based on text length
        return list(range(len(text.split())))

    def apply_chat_template(self, messages: list[dict], tokenize: bool = False) -> str:
        """Mock apply_chat_template method."""
        # Return a simple string representation
        if tokenize:
            return self.encode(str(messages))
        return str(messages)

    def decode(self, token_ids: list[int], skip_special_tokens: bool = True) -> str:
        """Mock decode method."""
        return " ".join([f"token_{i}" for i in token_ids])


class MockModel:
    """Mock model for testing."""

    def __init__(self):
        self.device = "cpu"
        self.config = MagicMock()

    def generate(self, **kwargs):
        """Mock generate method."""
        # Return mock tensor-like object
        mock_output = MagicMock()
        mock_output.shape = [1, 10]  # Mock shape
        return mock_output

    def save_pretrained(self, path: str):
        """Mock save_pretrained method."""
        pass

    def to(self, device: str):
        """Mock to method."""
        self.device = device
        return self


def create_mock_transformers():
    """Create mock transformers module."""
    mock_transformers = MagicMock()
    mock_transformers.AutoTokenizer.from_pretrained = MagicMock(
        return_value=MockTokenizer()
    )
    mock_transformers.AutoModelForCausalLM.from_pretrained = MagicMock(
        return_value=MockModel()
    )
    return mock_transformers


def create_mock_torch():
    """Create mock torch module."""
    mock_torch = MagicMock()
    mock_torch.float16 = "float16"
    mock_torch.cuda = MagicMock()
    mock_torch.cuda.is_available = MagicMock(return_value=False)
    mock_torch.no_grad = MagicMock()
    return mock_torch
