from kfp import dsl
from kfp.dsl import Input, Output

BASE_IMAGE = "quay.io/opendatahub/odh-training-th04-cpu-torch29-py312-rhel9:cpu-3.3"


@dsl.component(
    base_image=BASE_IMAGE,
    packages_to_install=[
        "datasets>=4.2.0",
        "python-dotenv>=1.1.1",
        "polars>=1.31.0",
        "tabulate>=0.9.0",
        "transformers>=4.57.1",
        "torch==2.8.0",
    ],
)
def knowledge_mixing(
    datasets_path: Input[dsl.Artifact],
    output_path: Output[dsl.Artifact],
    dataset_file: Output[dsl.Dataset],
    tokenizer_model_name: str = "RedHatAI/Llama-3.1-8B-Instruct",
    cut_size: str = "1,5,10",
    qa_per_doc: int = 3,
    save_gpt_oss_format: bool = False,
) -> str:

    #########################################
    # UTILITY FUNCTION FOR KNOWLEDGE MIXING #
    #########################################
    import json
    import os
    from pathlib import Path
    from typing import Any, List, Optional

    import polars as pl
    from datasets import Dataset, concatenate_datasets, load_dataset
    from tabulate import tabulate
    from transformers import AutoTokenizer

    os.environ["HF_HOME"] = str(Path(output_path.path) / "tokenizer_model")

    def get_avg_summaries_per_raw_doc(df: pl.DataFrame) -> float:
        """
        Calculate average summaries per raw document in the dataset.

        Args:
            df: Input dataframe with document and raw_document columns

        Returns:
            Average number of summaries per raw document
        """
        # Calculate average summaries per raw document
        summary_counts = df.group_by("raw_document").agg(
            pl.col("document").n_unique().alias("unique_summaries")
        )
        avg_summaries = summary_counts["unique_summaries"].mean()

        return avg_summaries

    def sample_doc_qa(
        df: pl.DataFrame, n_docs_per_raw: int = 50, qa_per_doc: int = 3
    ) -> pl.DataFrame:
        """
        Sample Q&A pairs from documents with optional reasoning.

        Note: 'document' column contains summaries, 'raw_document' contains original documents.
        n_docs_per_raw is the number of unique summaries to sample per raw document.

        Args:
            df: Input dataframe with document and Q&A data
            n_docs_per_raw: Maximum number of unique summaries to sample per raw document (cut size)
            qa_per_doc: Maximum number of Q&A pairs per document/summary

        Returns:
            Sampled dataframe with Q&A pairs
        """
        # Validate required columns
        required_cols = [
            "question",
            "response",
            "document",
            "raw_document",
            "document_outline",
        ]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Check if cut size is feasible
        avg_summaries = get_avg_summaries_per_raw_doc(df)
        if avg_summaries < n_docs_per_raw:
            print(
                f" Warning: Cut size {n_docs_per_raw} exceeds available summaries (avg: {avg_summaries:.1f} per raw document)"
            )

        # Create Q&A pair structure
        df = df.with_columns([pl.struct(["question", "response"]).alias("qa_pair")])

        # Handle optional reasoning column
        agg_cols = [
            pl.col("qa_pair"),
            pl.col("raw_document").first(),
            pl.col("document_outline").first(),
        ]

        if "parse_response_dict_reasoning_content" in df.columns:
            df = df.with_columns([
                pl.col("parse_response_dict_reasoning_content").alias("reasoning")
            ])
            agg_cols.append(pl.col("reasoning").first())

        # Group by document (summaries) and aggregate Q&A pairs
        df = df.group_by("document").agg(agg_cols)

        # Sample unique summaries per raw document
        sampled_docs = df.group_by("raw_document").map_groups(
            lambda g: g.sample(n=min(n_docs_per_raw, g.height))
        )

        # Limit Q&A pairs per summary and explode
        sampled_docs = sampled_docs.with_columns(
            pl.col("qa_pair").list.slice(0, qa_per_doc)
        ).explode(pl.col("qa_pair"))

        # Extract question and response from struct
        sampled_docs = sampled_docs.with_columns([
            pl.col("qa_pair").struct.field("question").alias("question"),
            pl.col("qa_pair").struct.field("response").alias("response"),
        ]).drop("qa_pair")

        return sampled_docs

    def _clean_response_text(df: pl.DataFrame) -> pl.DataFrame:
        """Clean response text by removing markers and whitespace."""
        return df.with_columns(
            pl
            .col("response")
            .str.replace_all(r"\[END\]", "")
            .str.replace_all(r"\[ANSWER\]", "")
            .str.strip_chars()
            .alias("response")
        )

    def _create_metadata(df: pl.DataFrame) -> pl.Expr:
        """Create metadata JSON structure."""
        return (
            pl
            .struct([
                pl.col("document").alias("sdg_document"),
                pl.lit("document_knowledge_qa").alias("dataset"),
                pl.col("raw_document"),
            ])
            .map_elements(json.dumps)
            .alias("metadata")
        )

    def _create_messages_with_reasoning(record: dict) -> List[dict]:
        """Create message structure with reasoning (thinking)."""
        return [
            {
                "role": "user",
                "content": f"{record['document_outline']}\n{record['document']}\n\n{record['question']}",
                "thinking": None,
            },
            {
                "role": "assistant",
                "content": record["response"],
                "thinking": record["reasoning"],
            },
        ]

    def _create_messages_with_reasoning_no_document(record: dict) -> List[dict]:
        """Create message structure with reasoning."""
        return [
            {
                "role": "user",
                "content": f"In {record['document_outline']}, {record['question']}",
                "thinking": None,
            },
            {
                "role": "assistant",
                "content": record["response"],
                "thinking": record["reasoning"],
            },
        ]

    def _create_messages_without_reasoning(record: dict) -> List[dict]:
        """Create message structure without reasoning."""
        return [
            {
                "role": "user",
                "content": f"{record['document_outline']}\n{record['document']}\n\n{record['question']}",
                "thinking": None,
            },
            {"role": "assistant", "content": record["response"], "thinking": ""},
        ]

    def _create_messages_without_reasoning_no_document(record: dict) -> List[dict]:
        """Create message structure without reasoning."""
        return [
            {
                "role": "user",
                "content": f"In {record['document_outline']}, {record['question']}",
                "thinking": None,
            },
            {"role": "assistant", "content": record["response"], "thinking": ""},
        ]

    def generate_knowledge_qa_dataset(
        generated_dataset: pl.DataFrame,
        keep_columns: Optional[List[str]] = None,
        pre_training: bool = False,
        dataset_name: str = "document_knowledge_qa",
        keep_document_in_context: bool = False,
    ) -> pl.DataFrame:
        """
        Generate knowledge Q&A dataset in chat format.

        Args:
            generated_dataset: Input dataframe with Q&A data
            keep_columns: Additional columns to keep in output
            pre_training: Whether to add unmask column for pre-training
            dataset_name: Name for the dataset metadata

        Returns:
            Formatted dataset with messages and metadata
        """
        if keep_columns is None:
            keep_columns = []

        # Validate required columns
        required_cols = [
            "question",
            "response",
            "document",
            "document_outline",
            "raw_document",
        ]
        missing_cols = [
            col for col in required_cols if col not in generated_dataset.columns
        ]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Clean response text
        generated_dataset = _clean_response_text(generated_dataset)

        # Create base columns
        base_columns = [_create_metadata(generated_dataset)]

        # Handle reasoning column
        has_reasoning = "reasoning" in generated_dataset.columns

        # TODO: Fix the name of reasoning column, test with reasoning model
        if has_reasoning and not keep_document_in_context:
            message_columns = [
                "question",
                "response",
                "document",
                "document_outline",
                "reasoning",
            ]
            messages_expr = (
                pl
                .struct(message_columns)
                .map_elements(_create_messages_with_reasoning_no_document)
                .alias("messages")
            )
        elif has_reasoning and keep_document_in_context:
            message_columns = [
                "question",
                "response",
                "document",
                "document_outline",
                "reasoning",
            ]
            messages_expr = (
                pl
                .struct(message_columns)
                .map_elements(_create_messages_with_reasoning)
                .alias("messages")
            )
        elif keep_document_in_context:
            message_columns = ["question", "response", "document", "document_outline"]
            messages_expr = (
                pl
                .struct(message_columns)
                .map_elements(_create_messages_without_reasoning)
                .alias("messages")
            )
        else:
            message_columns = ["question", "response", "document", "document_outline"]
            messages_expr = (
                pl
                .struct(message_columns)
                .map_elements(_create_messages_without_reasoning_no_document)
                .alias("messages")
            )

        base_columns.append(messages_expr)

        # Apply transformations
        knowledge_ds = generated_dataset.with_columns(base_columns)

        # Select final columns
        final_columns = keep_columns + ["messages", "metadata"]
        knowledge_ds = knowledge_ds.select(final_columns)
        # Add unmask column for pre-training if needed
        if pre_training:
            knowledge_ds = knowledge_ds.with_columns(pl.lit(True).alias("unmask"))
        else:
            knowledge_ds = knowledge_ds.with_columns(pl.lit(False).alias("unmask"))

        return knowledge_ds

    def count_len_in_tokens(
        df: pl.DataFrame, tokenizer: Any, column_name: str = "messages"
    ) -> pl.DataFrame:
        """
        Count token length of messages using tokenizer.

        Args:
            df: Input dataframe
            tokenizer: HuggingFace tokenizer with apply_chat_template method
            column_name: Column containing messages to tokenize

        Returns:
            Dataframe with added token_length column
        """
        if column_name not in df.columns:
            raise ValueError(f"Column '{column_name}' not found in dataframe")

        def apply_chat_template(messages: List[dict]) -> str:
            """Apply chat template to messages."""
            return tokenizer.apply_chat_template(messages, tokenize=False)

        def count_tokens(text: str) -> int:
            """Count tokens in text."""
            return len(tokenizer.encode(text))

        return df.with_columns(
            pl
            .col(column_name)
            .map_elements(apply_chat_template, return_dtype=pl.String)
            .map_elements(count_tokens, return_dtype=pl.Int32)
            .alias("token_length")
        )

    def load_tokenizer(student_model):
        """Initialize and return tokenizer."""
        print(f"Loading tokenizer: {student_model}")
        return AutoTokenizer.from_pretrained(student_model, trust_remote_code=True)

    def filter_gpt_oss_dataset(ds):
        """Apply GPT OSS format filtering to dataset."""
        original_size = len(ds)

        # Filter out problematic questions
        ds = ds.filter(
            lambda x: (
                "..." not in x["question"]
                and "<question>" not in x["question"]
                and "<Insert question here>" not in x["question"]
            )
        )

        # Clean response text
        ds = ds.map(
            lambda x: {
                "response": x["response"]
                .replace("[ANSWER]", "")
                .replace("[END]", "")
                .strip()
            }
        )

        filtered_size = len(ds)
        print(
            f"  Filtered {original_size - filtered_size} samples (kept {filtered_size})"
        )
        return ds

    def load_summary_dataset(summary_type):
        """Load a single summary dataset."""
        file_path = os.path.join(datasets_path.path, f"{summary_type}")

        # Check if file exists
        if not Path(file_path).exists():
            print(f"  Warning: File not found: {file_path}")
            return None

        print(f"Loading {summary_type} from: {file_path}")
        ds = load_dataset("json", data_dir=file_path, split="train")

        if summary_type == "document_based_qa":
            ds = ds.rename_column("base_document", "raw_document")
        # Apply filtering if needed
        if save_gpt_oss_format:
            ds = filter_gpt_oss_dataset(ds)

        print(f"  Loaded {summary_type}: {len(ds)} samples")
        return ds.to_polars()

    def load_all_summary_datasets():
        """Load all summary type datasets."""
        summary_types = [
            "extractive_summary",
            "detailed_summary",
            "key_facts_to_qa",
            "document_based_qa",
        ]

        summary_datasets = {}

        for summary_type in summary_types:
            dataset = load_summary_dataset(summary_type)
            if dataset is not None:
                summary_datasets[summary_type] = dataset

        if not summary_datasets:
            raise ValueError("No datasets were successfully loaded!")

        return summary_datasets

    def validate_cuts_for_datasets(summary_datasets, cuts):
        """Validate which cut sizes are feasible for each dataset."""
        feasible_cuts = set(cuts)

        print(" Validating cut sizes against available data...")
        for summary_type, df in summary_datasets.items():
            if summary_type in ["key_facts_to_qa", "document_based_qa"]:
                print(f"\n Skipping {summary_type}:")
                continue
            print(f"\n Checking {summary_type}:")

            for cut in cuts:
                avg_summaries = get_avg_summaries_per_raw_doc(df)
                is_feasible = avg_summaries >= cut
                status = " Feasible" if is_feasible else " Too large"
                print(
                    f"  Cut {cut}: {status} (avg summaries per raw doc: {avg_summaries:.1f})"
                )

                if not is_feasible:
                    feasible_cuts.discard(cut)

        final_cuts = sorted(list(feasible_cuts))
        if len(final_cuts) < len(cuts):
            removed_cuts = set(cuts) - feasible_cuts
            print(f"\n  Removing infeasible cuts: {sorted(list(removed_cuts))}")

        print(f"\n Final feasible cuts: {final_cuts}")
        return final_cuts

    def process_single_summary_type(summary_type, df, cut, tokenizer, qa_per_doc):
        """Process a single summary type dataset."""
        try:
            print(f"  Processing {summary_type}...")
            if summary_type == "key_facts_to_qa":
                # Skip the sampling step for keys facts QA dataset as we discard the generated summary and only keep the qa pairs
                # Generate knowledge Q&A dataset
                generated_dataset = generate_knowledge_qa_dataset(
                    df,
                    keep_columns=[
                        "question",
                        "document_outline",
                        "raw_document",
                        "document",
                    ],
                    pre_training=True,
                    keep_document_in_context=False,
                )
            else:
                if summary_type != "document_based_qa":
                    # Sample documents and Q&A pairs (validation already done)
                    df_cut = sample_doc_qa(
                        df, n_docs_per_raw=cut, qa_per_doc=qa_per_doc
                    )
                else:
                    df_cut = df

                # Generate knowledge Q&A dataset
                generated_dataset = generate_knowledge_qa_dataset(
                    df_cut,
                    keep_columns=[
                        "question",
                        "document_outline",
                        "raw_document",
                        "document",
                    ],
                    pre_training=True,
                    keep_document_in_context=True,
                )

            # Count tokens
            generated_dataset = count_len_in_tokens(generated_dataset, tokenizer)

            # Convert back to HuggingFace dataset
            generated_dataset = Dataset.from_polars(generated_dataset)

            # Calculate statistics
            unique_docs = len(set(generated_dataset["document"]))
            unique_raw_docs = len(set(generated_dataset["raw_document"]))
            generated_cut_size = (
                unique_docs / unique_raw_docs if unique_raw_docs > 0 else 0
            )

            stats = {
                "samples": len(generated_dataset),
                "unique_docs": unique_docs,
                "unique_raw_docs": unique_raw_docs,
                "avg_docs_per_raw": generated_cut_size,
                "total_tokens": sum(generated_dataset["token_length"]),
            }

            print(
                f"     Processed {len(generated_dataset)} samples ({generated_cut_size:.1f} summaries per raw doc)"
            )
            return generated_dataset, stats

        except Exception as e:
            print(f"     Error processing {summary_type}: {e}")
            return None, None

    def combine_and_save_datasets(all_datasets, cut_stats, cut, output_dir):
        """Combine datasets and save to file."""
        if not all_datasets:
            print(f"   No datasets processed for cut size {cut}")
            return None

        try:
            # Combine all summary types for this cut
            combined_dataset = concatenate_datasets(all_datasets)
            total_tokens = sum(combined_dataset["token_length"])

            # Save combined dataset
            output_path = os.path.join(output_dir, f"combined_cut_{cut}x.jsonl")
            combined_dataset.to_json(output_path, orient="records", lines=True)

            # Print results
            print("\n\n\n\n", "=" * 50)
            print(f"   Saved to: {output_path}")
            print(f"   Total samples: {len(combined_dataset)}")
            print(f"   Total tokens: {total_tokens:,}")

            # Print detailed statistics
            print("   Summary statistics:")
            for summary_type, stats in cut_stats.items():
                print(
                    f"    {summary_type}: {stats['samples']} samples, {stats['total_tokens']:,} tokens"
                )

            return (cut, total_tokens, len(combined_dataset))

        except Exception as e:
            print(f"   Error combining datasets for cut {cut}: {e}")
            return None

    def process_single_cut(cut, summary_datasets, tokenizer, output_dir, qa_per_doc):
        """Process all summary types for a single cut size."""
        print(f"\n Processing cut size: {cut}")
        all_datasets = []
        cut_stats = {}

        for summary_type, df in summary_datasets.items():
            dataset, stats = process_single_summary_type(
                summary_type, df, cut, tokenizer, qa_per_doc
            )

            if dataset is not None and stats is not None:
                all_datasets.append(dataset)
                cut_stats[summary_type] = stats

        return combine_and_save_datasets(all_datasets, cut_stats, cut, output_dir)

    def process_and_mix_datasets(
        cuts, summary_datasets, tokenizer, output_dir, qa_per_doc
    ):
        """Process and mix datasets with different cut sizes."""
        # First validate which cuts are feasible
        feasible_cuts = validate_cuts_for_datasets(summary_datasets, cuts)

        if not feasible_cuts:
            print("\n No feasible cuts found! Check your data or reduce cut sizes.")
            return []

        token_count = []

        print(f"\nProcessing {len(feasible_cuts)} feasible cut sizes...")
        for cut in feasible_cuts:
            result = process_single_cut(
                cut, summary_datasets, tokenizer, output_dir, qa_per_doc
            )
            if result is not None:
                token_count.append(result)

        return token_count

    def print_final_summary(token_count):
        """Print final summary table."""
        if token_count:
            print("\n" + "=" * 50)
            print(" FINAL SUMMARY")
            print("=" * 50)
            print(
                tabulate(
                    token_count,
                    headers=["Cut Size", "Total Tokens", "Total Samples"],
                    tablefmt="github",
                    numalign="right",
                )
            )
        else:
            print("\n No datasets were successfully processed!")

    #########################################
    # MAIN LOGIC FOR KNOWLEDGE MIXING TASK #
    #########################################

    cuts = [int(x.strip()) for x in cut_size.split(",")]
    # Load tokenizer and datasets
    try:
        tokenizer = load_tokenizer(tokenizer_model_name)
        summary_datasets = load_all_summary_datasets()
        # After loading each dataset

        for _summary_type, dataset in summary_datasets.items():
            print(f" Columns: {list(dataset.columns)}")
            for column in list(dataset.columns):
                print(f"          - {column}")

            print(f" Sample record keys: {list(dataset.head(1).to_dicts()[0].keys())}")
        print(f"\n Successfully loaded {len(summary_datasets)} summary datasets")
    except Exception as e:
        print(f" Error during initialization: {e}")
        raise

    # Process datasets
    token_count = process_and_mix_datasets(
        cuts, summary_datasets, tokenizer, output_path.path, qa_per_doc
    )

    # Print final summary
    print_final_summary(token_count)
    print("\n\n\n")
    # Find the biggest cut size possible when mixing
    import re

    # Find all files matching the pattern in the current directory
    files = Path(output_path.path).glob("combined_cut_*x.jsonl")

    print(files)
    # Extract the number 'N' from 'combined_cut_Nx.jsonl' and find the max
    biggest_file = max(
        files,
        key=lambda f: int(re.search(r"combined_cut_(\d+)x\.jsonl", f.name).group(1)),
        default=None,
    )

    import shutil

    if biggest_file:
        print(f"The file with the biggest cut size is: {biggest_file.name}")
        print(str(biggest_file))
        shutil.copy(biggest_file, dataset_file.path)
        return str(biggest_file)
    else:
        print("No matching files found.")
        raise ValueError(
            "No feasible cut sizes are found. No mixed datasets are generated."
        )
