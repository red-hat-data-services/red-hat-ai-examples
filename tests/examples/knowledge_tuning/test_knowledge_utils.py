"""Tests for utility functions in knowledge-tuning."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import polars as pl
import pytest

# Add the knowledge-tuning utils to path
repo_root = Path(__file__).parent.parent.parent.parent
utils_path = (
    repo_root / "examples" / "knowledge-tuning" / "04_Knowledge_Mixing" / "utils"
)
sys.path.insert(0, str(utils_path))

from knowledge_utils import (  # noqa: E402
    count_len_in_tokens,
    generate_knowledge_qa_dataset,
    get_avg_summaries_per_raw_doc,
    sample_doc_qa,
)


class TestGetAvgSummariesPerRawDoc:
    """Test get_avg_summaries_per_raw_doc function."""

    def test_basic_functionality(self):
        """Test basic calculation of average summaries."""
        df = pl.DataFrame({
            "raw_document": ["doc1", "doc1", "doc1", "doc2", "doc2"],
            "document": ["sum1", "sum2", "sum3", "sum4", "sum5"],
        })

        result = get_avg_summaries_per_raw_doc(df)
        assert isinstance(result, float)
        assert result > 0

    def test_single_raw_document(self):
        """Test with single raw document."""
        df = pl.DataFrame({
            "raw_document": ["doc1", "doc1"],
            "document": ["sum1", "sum2"],
        })

        result = get_avg_summaries_per_raw_doc(df)
        assert result == 2.0

    def test_data_contract_validation(self):
        """Test that function requires correct columns."""
        # Missing required columns
        df = pl.DataFrame({
            "wrong_col": ["val1", "val2"],
        })

        with pytest.raises((KeyError, pl.exceptions.ColumnNotFoundError)):
            get_avg_summaries_per_raw_doc(df)


class TestSampleDocQa:
    """Test sample_doc_qa function."""

    def test_required_columns_validation(self):
        """Test that function validates required columns."""
        df = pl.DataFrame({
            "question": ["q1"],
            "response": ["r1"],
            # Missing required columns
        })

        with pytest.raises(ValueError, match="Missing required columns"):
            sample_doc_qa(df)

    def test_data_format_validation(self):
        """Test that function validates data formats."""
        df = pl.DataFrame({
            "question": ["q1", "q2"],
            "response": ["r1", "r2"],
            "document": ["doc1", "doc2"],
            "raw_document": ["raw1", "raw2"],
            "document_outline": ["outline1", "outline2"],
        })

        result = sample_doc_qa(df, n_docs_per_raw=1, qa_per_doc=1)
        assert isinstance(result, pl.DataFrame)
        assert "question" in result.columns
        assert "response" in result.columns

    def test_with_reasoning_column(self):
        """Test function with reasoning column."""
        df = pl.DataFrame({
            "question": ["q1", "q2"],
            "response": ["r1", "r2"],
            "document": ["doc1", "doc2"],
            "raw_document": ["raw1", "raw2"],
            "document_outline": ["outline1", "outline2"],
            "parse_response_dict_reasoning_content": ["reason1", "reason2"],
        })

        result = sample_doc_qa(df, n_docs_per_raw=1, qa_per_doc=1)
        assert isinstance(result, pl.DataFrame)


class TestGenerateKnowledgeQaDataset:
    """Test generate_knowledge_qa_dataset function."""

    def test_required_columns_validation(self):
        """Test that function validates required columns."""
        df = pl.DataFrame({
            "question": ["q1"],
            # Missing required columns
        })

        with pytest.raises(ValueError, match="Missing required columns"):
            generate_knowledge_qa_dataset(df)

    def test_data_contract_validation(self):
        """Test data contract validation."""
        df = pl.DataFrame({
            "question": ["q1"],
            "response": ["r1"],
            "document": ["doc1"],
            "document_outline": ["outline1"],
            "raw_document": ["raw1"],
        })

        result = generate_knowledge_qa_dataset(df)
        assert isinstance(result, pl.DataFrame)
        assert "messages" in result.columns
        assert "metadata" in result.columns

    def test_json_schema_validation(self):
        """Test that output follows expected JSON schema."""
        df = pl.DataFrame({
            "question": ["q1"],
            "response": ["r1"],
            "document": ["doc1"],
            "document_outline": ["outline1"],
            "raw_document": ["raw1"],
        })

        result = generate_knowledge_qa_dataset(df)

        # Check messages structure - extract from Polars Series
        messages_series = result["messages"]
        # Convert to list and get first item
        messages_list = (
            messages_series.to_list()
            if isinstance(messages_series, pl.Series)
            else list(messages_series)
        )
        messages = messages_list[0]
        assert isinstance(messages, list)
        assert len(messages) >= 1
        assert "role" in messages[0]
        assert "content" in messages[0]

        # Check metadata structure - extract from Polars Series
        metadata_series = result["metadata"]
        metadata_list = (
            metadata_series.to_list()
            if isinstance(metadata_series, pl.Series)
            else list(metadata_series)
        )
        metadata = metadata_list[0]
        # Metadata should be a JSON string
        assert isinstance(metadata, str)
        metadata_dict = json.loads(metadata)
        assert "dataset" in metadata_dict

    def test_with_reasoning(self):
        """Test function with reasoning column."""
        df = pl.DataFrame({
            "question": ["q1"],
            "response": ["r1"],
            "document": ["doc1"],
            "document_outline": ["outline1"],
            "raw_document": ["raw1"],
            "reasoning": ["reason1"],
        })

        result = generate_knowledge_qa_dataset(df)
        assert isinstance(result, pl.DataFrame)
        assert "messages" in result.columns

    def test_pre_training_flag(self):
        """Test pre_training flag adds unmask column."""
        df = pl.DataFrame({
            "question": ["q1"],
            "response": ["r1"],
            "document": ["doc1"],
            "document_outline": ["outline1"],
            "raw_document": ["raw1"],
        })

        result = generate_knowledge_qa_dataset(df, pre_training=True)
        assert "unmask" in result.columns
        assert result["unmask"][0] is True

        result_no_pretrain = generate_knowledge_qa_dataset(df, pre_training=False)
        assert result_no_pretrain["unmask"][0] is False


class TestCountLenInTokens:
    """Test count_len_in_tokens function."""

    def test_column_validation(self):
        """Test that function validates column exists."""
        df = pl.DataFrame({
            "wrong_col": ["val1"],
        })

        mock_tokenizer = MagicMock()
        mock_tokenizer.apply_chat_template = MagicMock(return_value="test")
        mock_tokenizer.encode = MagicMock(return_value=[1, 2, 3])

        with pytest.raises(ValueError, match="Column 'messages' not found"):
            count_len_in_tokens(df, mock_tokenizer)

    def test_mocked_tokenizer(self):
        """Test function with mocked tokenizer."""
        import sys
        from pathlib import Path

        # Add mocks to path
        mocks_path = Path(__file__).parent / "mocks"
        sys.path.insert(0, str(mocks_path))
        from transformers_mock import MockTokenizer

        df = pl.DataFrame({
            "messages": [
                [{"role": "user", "content": "test"}],
                [{"role": "user", "content": "test2"}],
            ],
        })

        mock_tokenizer = MockTokenizer()
        result = count_len_in_tokens(df, mock_tokenizer, column_name="messages")

        assert isinstance(result, pl.DataFrame)
        assert "token_length" in result.columns
        assert len(result) == 2

    def test_tokenizer_mock_behavior(self):
        """Test that tokenizer mocks work correctly."""
        import sys
        from pathlib import Path

        # Add mocks to path
        mocks_path = Path(__file__).parent / "mocks"
        sys.path.insert(0, str(mocks_path))
        from transformers_mock import MockTokenizer

        tokenizer = MockTokenizer()

        # Test encode
        encoded = tokenizer.encode("test text")
        assert isinstance(encoded, list)
        assert len(encoded) > 0

        # Test apply_chat_template
        messages = [{"role": "user", "content": "test"}]
        template = tokenizer.apply_chat_template(messages, tokenize=False)
        assert isinstance(template, str)
