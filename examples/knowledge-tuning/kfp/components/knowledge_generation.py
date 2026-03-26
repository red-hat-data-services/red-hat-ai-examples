from kfp import dsl
from kfp.dsl import Dataset, Input, Output

BASE_IMAGE = "quay.io/fabianofranz/docling-ubi9:2.54.0"


@dsl.component(
    base_image=BASE_IMAGE,
    packages_to_install=[
        "nest-asyncio",
        "sdg-hub>=0.6.0",
        "datasets>=3.6.0",
    ],
)
def generate_extractive_summaries(
    input_dataset: Input[dsl.Artifact],
    output_path: Output[dsl.Artifact],
    model_name: str,
    api_key: str,
    api_base: str,
    seed_data_subsample: int = 0,
    enable_reasoning: bool = False,
    number_of_summaries: int = 5,
    max_concurrency: int = 5,
    inference_timeout: int = 920,
):
    """Generate document-based QA knowledge tuning data."""

    import os

    import nest_asyncio
    import pandas as pd
    from sdg_hub import Flow, FlowRegistry

    nest_asyncio.apply()

    from pathlib import Path

    OUTPUT_DIR = Path(output_path.path)  # Path to the workspace directory

    OUTPUT_DIR.mkdir(
        parents=True, exist_ok=True
    )  # Create the output directory if it doesn't exist

    os.environ["LITELLM_REQUEST_TIMEOUT"] = str(inference_timeout)

    print("INFERENCE TIMEOUT SET : -- > ", os.environ["LITELLM_REQUEST_TIMEOUT"])

    # Load the seed data that was generated when you ran the Data Processing notebook

    seed_data_file = os.path.join(input_dataset.path, "seed_data.jsonl")
    print("Seed data file path:", seed_data_file)
    quality_corpus = pd.read_json(seed_data_file, lines=True)

    if seed_data_subsample > 0:
        quality_corpus = quality_corpus.iloc[:seed_data_subsample]

    print(f"Generating document-based QA for {len(quality_corpus)} documents...")

    FlowRegistry.discover_flows()
    flow_path = FlowRegistry.get_flow_path(
        "Extractive Summary Knowledge Tuning Dataset Generation Flow"
    )
    flow = Flow.from_yaml(flow_path)

    flow.set_model_config(
        model=model_name,
        api_base=api_base,
        api_key=api_key,
        enable_reasoning=enable_reasoning,
    )

    runtime_params = {
        "gen_extractive_summary": {"n": number_of_summaries},
    }
    if enable_reasoning:
        runtime_params["gen_extractive_summary"]["max_tokens"] = 6000
        runtime_params["question_generation"] = {"max_tokens": 1024}
    # runtime_params = {}
    # if enable_reasoning:
    #     runtime_params = {
    #         "question_generation": {"max_tokens": 1024},
    #         "gen_detailed_summary": {"n": number_of_summaries, "max_tokens": 6000},
    #     }
    # else:
    #     runtime_params = {"gen_extractive_summary": {"n": number_of_summaries}}

    print("Starting generation...")
    generated_data = flow.generate(
        quality_corpus, runtime_params=runtime_params, max_concurrency=max_concurrency
    )

    generated_data.to_json(OUTPUT_DIR / "gen.jsonl", orient="records", lines=True)
    print(f"Generated {len(generated_data)} document QA records")
    print(f"Saved to: {OUTPUT_DIR}")


@dsl.component(
    base_image=BASE_IMAGE,
    packages_to_install=[
        "nest-asyncio",
        "sdg-hub>=0.6.0",
        "datasets>=3.6.0",
    ],
)
def generate_detailed_summaries(
    input_dataset: Input[dsl.Artifact],
    output_path: Output[dsl.Artifact],
    model_name: str,
    api_key: str,
    api_base: str,
    seed_data_subsample: int = 0,
    enable_reasoning: bool = False,
    max_concurrency: int = 5,
    number_of_summaries: int = 5,
    inference_timeout: int = 920,
):
    import os

    import nest_asyncio
    import pandas as pd
    from sdg_hub import Flow, FlowRegistry

    nest_asyncio.apply()

    from pathlib import Path

    OUTPUT_DIR = Path(output_path.path)  # Path to the workspace directory

    OUTPUT_DIR.mkdir(
        parents=True, exist_ok=True
    )  # Create the output directory if it doesn't exist

    os.environ["LITELLM_REQUEST_TIMEOUT"] = str(inference_timeout)

    print("INFERENCE TIMEOUT SET : -- > ", os.environ["LITELLM_REQUEST_TIMEOUT"])

    # Load the seed data that was generated when you ran the Data Processing notebook

    seed_data_file = os.path.join(input_dataset.path, "seed_data.jsonl")
    print("Seed data file path:", seed_data_file)
    quality_corpus = pd.read_json(seed_data_file, lines=True)

    if seed_data_subsample > 0:
        quality_corpus = quality_corpus.iloc[:seed_data_subsample]

    print(f"Generating detailed summaries for {len(quality_corpus)} documents...")

    FlowRegistry.discover_flows()
    flow_path = FlowRegistry.get_flow_path(
        "Detailed Summary Knowledge Tuning Dataset Generation Flow"
    )
    flow = Flow.from_yaml(flow_path)

    flow.set_model_config(
        model=model_name,
        api_base=api_base,
        api_key=api_key,
        enable_reasoning=enable_reasoning,
    )

    runtime_params = {"gen_detailed_summary": {"n": number_of_summaries}}

    if enable_reasoning:
        runtime_params = {
            "question_generation": {"max_tokens": 1024},
            "gen_detailed_summary": {"n": number_of_summaries, "max_tokens": 6000},
        }

    print("Starting generation...")
    generated_data = flow.generate(
        quality_corpus, runtime_params=runtime_params, max_concurrency=max_concurrency
    )

    generated_data.to_json(OUTPUT_DIR / "gen.jsonl", orient="records", lines=True)
    print(f"Generated {len(generated_data)} detailed summary records")
    print(f"Saved to: {OUTPUT_DIR}")


@dsl.component(
    base_image=BASE_IMAGE,
    packages_to_install=[
        "nest-asyncio",
        "sdg-hub>=0.6.0",
        "datasets>=3.6.0",
    ],
)
def generate_key_facts_summary(
    input_dataset: Input[dsl.Artifact],
    output_path: Output[dsl.Artifact],
    model_name: str,
    api_key: str,
    api_base: str,
    seed_data_subsample: int = 0,
    enable_reasoning: bool = False,
    max_concurrency: int = 5,
    inference_timeout: int = 920,
):
    import os

    import nest_asyncio
    import pandas as pd
    from sdg_hub import Flow, FlowRegistry

    nest_asyncio.apply()

    from pathlib import Path

    OUTPUT_DIR = Path(output_path.path)  # Path to the workspace directory

    OUTPUT_DIR.mkdir(
        parents=True, exist_ok=True
    )  # Create the output directory if it doesn't exist

    os.environ["LITELLM_REQUEST_TIMEOUT"] = str(inference_timeout)

    print("INFERENCE TIMEOUT SET : -- > ", os.environ["LITELLM_REQUEST_TIMEOUT"])

    # Load the seed data that was generated when you ran the Data Processing notebook

    seed_data_file = os.path.join(input_dataset.path, "seed_data.jsonl")
    print("Seed data file path:", seed_data_file)
    quality_corpus = pd.read_json(seed_data_file, lines=True)

    if seed_data_subsample > 0:
        quality_corpus = quality_corpus.iloc[:seed_data_subsample]

    print(f"Generating detailed summaries for {len(quality_corpus)} documents...")

    FlowRegistry.discover_flows()
    flow_path = FlowRegistry.get_flow_path(
        "Key Facts Knowledge Tuning Dataset Generation Flow"
    )
    flow = Flow.from_yaml(flow_path)

    flow.set_model_config(
        model=model_name,
        api_base=api_base,
        api_key=api_key,
        enable_reasoning=enable_reasoning,
    )

    runtime_params = {}
    if enable_reasoning:
        runtime_params = {"generate_key_fact_qa": {"max_tokens": 6000}}

    print("Starting generation...")
    generated_data = flow.generate(
        quality_corpus, runtime_params=runtime_params, max_concurrency=max_concurrency
    )

    generated_data.to_json(OUTPUT_DIR / "gen.jsonl", orient="records", lines=True)
    print(f"Generated {len(generated_data)} key facts records")
    print(f"Saved to: {OUTPUT_DIR}")


@dsl.component(
    base_image=BASE_IMAGE,
    packages_to_install=[
        "nest-asyncio",
        "sdg-hub>=0.6.0",
        "datasets>=3.6.0",
    ],
)
def generate_document_based_qa(
    input_dataset: Input[dsl.Artifact],
    output_path: Output[dsl.Artifact],
    model_name: str,
    api_key: str,
    api_base: str,
    seed_data_subsample: int = 0,
    enable_reasoning: bool = False,
    max_concurrency: int = 5,
    inference_timeout: int = 920,
):
    import os

    import nest_asyncio
    import pandas as pd
    from sdg_hub import Flow, FlowRegistry

    nest_asyncio.apply()

    from pathlib import Path

    OUTPUT_DIR = Path(output_path.path)  # Path to the workspace directory

    OUTPUT_DIR.mkdir(
        parents=True, exist_ok=True
    )  # Create the output directory if it doesn't exist

    os.environ["LITELLM_REQUEST_TIMEOUT"] = str(inference_timeout)

    print("INFERENCE TIMEOUT SET : -- > ", os.environ["LITELLM_REQUEST_TIMEOUT"])

    # Load the seed data that was generated when you ran the Data Processing notebook

    seed_data_file = os.path.join(input_dataset.path, "seed_data.jsonl")
    print("Seed data file path:", seed_data_file)
    quality_corpus = pd.read_json(seed_data_file, lines=True)

    if seed_data_subsample > 0:
        quality_corpus = quality_corpus.iloc[:seed_data_subsample]

    print(f"Generating detailed summaries for {len(quality_corpus)} documents...")

    FlowRegistry.discover_flows()
    flow_path = FlowRegistry.get_flow_path(
        "Document Based Knowledge Tuning Dataset Generation Flow"
    )
    flow = Flow.from_yaml(flow_path)

    flow.set_model_config(
        model=model_name,
        api_base=api_base,
        api_key=api_key,
        enable_reasoning=enable_reasoning,
    )

    runtime_params = {}
    if enable_reasoning:
        runtime_params = {"question_generation": {"max_tokens": 1024}}

    print("Starting generation...")
    generated_data = flow.generate(
        quality_corpus, runtime_params=runtime_params, max_concurrency=max_concurrency
    )

    generated_data.to_json(OUTPUT_DIR / "gen.jsonl", orient="records", lines=True)
    print(f"Generated {len(generated_data)} document QA records")
    print(f"Saved to: {OUTPUT_DIR}")


@dsl.component(base_image=BASE_IMAGE, packages_to_install=["datasets"])
def merge_all_outputs_component(
    extractive_data: Input[Dataset],
    detailed_data: Input[Dataset],
    key_facts_data: Input[Dataset],
    doc_qa_data: Input[Dataset],
    merged_output: Output[Dataset],
):
    """Combine all generated data into a single output."""
    import os
    from pathlib import Path

    from datasets import load_dataset

    print("Loading all datasets...")

    # Load each dataset
    extractive = load_dataset(
        "json", data_files=os.path.join(extractive_data.path, "*.jsonl"), split="train"
    )
    detailed = load_dataset(
        "json", data_files=os.path.join(detailed_data.path, "*.jsonl"), split="train"
    )
    key_facts = load_dataset(
        "json", data_files=os.path.join(key_facts_data.path, "*.jsonl"), split="train"
    )
    doc_qa = load_dataset(
        "json", data_files=os.path.join(doc_qa_data.path, "*.jsonl"), split="train"
    )

    # Combine all datasets
    print(f"  - Extractive: {len(extractive)} records")
    print(f"  - Detailed: {len(detailed)} records")
    print(f"  - Key Facts: {len(key_facts)} records")
    print(f"  - Doc QA: {len(doc_qa)} records")

    dataset_output_folders = [
        "extractive_summary",
        "detailed_summary",
        "key_facts_to_qa",
        "document_based_qa",
    ]
    for dataset_folder in dataset_output_folders:
        dataset_output_dir = Path(merged_output.path) / dataset_folder
        dataset_output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created output directory for {dataset_folder}")

    extractive.to_json(
        os.path.join(merged_output.path, "extractive_summary", "gen.jsonl"),
        orient="records",
        lines=True,
    )
    detailed.to_json(
        os.path.join(merged_output.path, "detailed_summary", "gen.jsonl"),
        orient="records",
        lines=True,
    )
    key_facts.to_json(
        os.path.join(merged_output.path, "key_facts_to_qa", "gen.jsonl"),
        orient="records",
        lines=True,
    )
    doc_qa.to_json(
        os.path.join(merged_output.path, "document_based_qa", "gen.jsonl"),
        orient="records",
        lines=True,
    )

    print(f"Merged output saved to: {merged_output.path}")
