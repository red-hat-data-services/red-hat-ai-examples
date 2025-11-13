"""
Kubeflow Pipeline for Knowledge Generation using SDG Hub

SIMPLE APPROACH - No Docker Required!
KFP will automatically install SDG Hub from Git.

This pipeline converts the knowledge_generation notebook into a KFP pipeline
with components for seed data creation and multiple knowledge generation flows.
"""

from kfp import compiler, dsl, kubernetes
from kfp.dsl import Dataset, Input, Output

BASE_IMAGE = "image-registry.openshift-image-registry.svc:5000/redhat-ods-applications/jupyter-minimal-cpu-py312-ubi9:2025.1"


@dsl.component(
    base_image=BASE_IMAGE,
    packages_to_install=[
        "datasets",
        "nest-asyncio",
    ],
)
def create_seed_data_component(output_dataset: Output[Dataset]):
    """Load or create seed data from QuALITY Benchmark dataset."""
    import os

    from datasets import load_dataset

    seed_data_path = os.getenv("SEED_DATA_PATH", "seed_data.jsonl")

    def create_seed_data_from_quality_benchmark(seed_data_path: str):
        """Create seed data from QuALITY Benchmark dataset and save to file."""

        print("Loading QuALITY Benchmark dataset...")
        quality_corpus = (
            load_dataset("zitongyang/entigraph-quality-corpus", split="train")
            .remove_columns(["entity", "entigraph"])
            .rename_columns({"raw": "document", "uid": "document_outline"})
        )

        # Define seed examples for knowledge tuning
        seed_examples = {
            "icl_document": (
                "The coastal town of Willow Creek, once renowned for its pristine beaches, now struggles with rampant pollution. Plastic debris and oil spills have devastated marine life, prompting a decline in tourism and fishing industries. Residents have organized weekly clean-up initiatives, but the scale of the problem overwhelms their efforts.",
                "Technologists at the local university have developed an AI-powered buoy system to combat this. The buoys, equipped with solar panels and filtration technology, can identify and absorb oil spills while collecting microplastics. Data from the buoys is shared publicly, raising awareness and pressuring corporations to adopt sustainable practices. Though costly, the project has sparked hope for revitalizing the ecosystem and economy.",
            ),
            "icl_query_1": "How does the technological solution address the economic *and* environmental challenges highlighted in the document?",
            "icl_query_2": "What implicit values or priorities do the community's actions (clean-up initiatives) and the technologists' project reflect, and how do these align or contrast?",
            "icl_query_3": "Imagine the buoy project succeeds. What unintended consequences might arise from its impact, considering document's themes?",
            "domain": "articles/essays",
        }

        quality_corpus = quality_corpus.map(lambda x: seed_examples)

        # Save to file
        quality_corpus.to_json(seed_data_path, orient="records", lines=True)
        print(f"Created seed data at: {seed_data_path}")

        return quality_corpus

    # Load seed data. If one is not provided, create it from the quality benchmark dataset.
    if not os.path.exists(seed_data_path):
        print(f"{seed_data_path} not found. Creating seed data...")
        quality_corpus = create_seed_data_from_quality_benchmark(
            seed_data_path=seed_data_path
        )
    else:
        print(f"Loading existing seed data from {seed_data_path}")
        quality_corpus = load_dataset("json", data_files=seed_data_path, split="train")

    # Subsample the seed data. Useful for debugging.
    subsample = int(os.getenv("SEED_DATA_SUBSAMPLE", "0"))
    if subsample > 0:
        quality_corpus = quality_corpus.select(range(subsample))
        print(f"Subsampled to {subsample} samples")

    subsample = int(os.getenv("SEED_DATA_SUBSAMPLE", "0"))
    if subsample > 0:
        quality_corpus = quality_corpus.select(
            range(min(subsample, len(quality_corpus)))
        )

    quality_corpus.to_json(output_dataset.path, orient="records", lines=True)
    print(f"Saved seed data to: {output_dataset.path}")


@dsl.component(
    base_image=BASE_IMAGE,
    packages_to_install=[
        "datasets",
        "nest-asyncio",
        "sdg_hub[examples]",  # Install SDG Hub from Git
    ],
)
def generate_document_based_qa_component(
    input_dataset: Input[Dataset],
    output_dataset: Output[Dataset],
):
    """Generate document-based QA knowledge tuning data."""
    import os

    import nest_asyncio
    from datasets import load_dataset
    from sdg_hub import Flow, FlowRegistry

    nest_asyncio.apply()

    enable_reasoning = os.getenv("ENABLE_REASONING", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    model_provider = os.getenv("MODEL_PROVIDER", "hosted_vllm")
    if model_provider == "hosted_vllm":
        hosted_model = os.getenv(
            "VLLM_MODEL", "hosted_vllm/meta-llama/Llama-3.3-70B-Instruct"
        )
        api_base = os.getenv("API_BASE_URL", "http://localhost:8000/v1")
        api_key = os.getenv("VLLM_API_KEY", "EMPTY")
    elif model_provider == "openai":
        hosted_model = f"openai/{os.getenv('OPENAI_MODEL', 'google/gemini-2.5-flash-lite-preview-09-2025')}"
        api_base = os.getenv("API_BASE_URL", "https://openrouter.ai/api/v1")
        api_key = os.getenv("OPENAI_API_KEY", "EMPTY")
    max_concurrency = int(os.getenv("MAX_CONCURRENCY", "50"))

    print("Loading input dataset...")
    quality_corpus = load_dataset("json", data_files=input_dataset.path, split="train")

    print(f"Generating document-based QA for {len(quality_corpus)} documents...")

    FlowRegistry.discover_flows()
    flow_path = FlowRegistry.get_flow_path(
        "Document Based Knowledge Tuning Dataset Generation Flow"
    )
    flow = Flow.from_yaml(flow_path)

    flow.set_model_config(
        model=hosted_model,
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

    generated_data.to_json(output_dataset.path, orient="records", lines=True)
    print(f"Generated {len(generated_data)} document QA records")
    print(f"Saved to: {output_dataset.path}")


@dsl.component(
    base_image=BASE_IMAGE,
    packages_to_install=[
        "datasets",
        "nest-asyncio",
        "sdg_hub[examples]",  # Install SDG Hub from Git
    ],
)
def generate_key_facts_component(
    input_dataset: Input[Dataset], output_dataset: Output[Dataset]
):
    """Generate key facts knowledge tuning data."""
    import os

    import nest_asyncio
    from datasets import load_dataset
    from sdg_hub import Flow, FlowRegistry

    nest_asyncio.apply()

    enable_reasoning = os.getenv("ENABLE_REASONING", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    model_provider = os.getenv("MODEL_PROVIDER", "hosted_vllm")
    if model_provider == "hosted_vllm":
        hosted_model = os.getenv(
            "VLLM_MODEL", "hosted_vllm/meta-llama/Llama-3.3-70B-Instruct"
        )
        api_base = os.getenv("API_BASE_URL", "http://localhost:8000/v1")
        api_key = os.getenv("VLLM_API_KEY", "EMPTY")
    elif model_provider == "openai":
        hosted_model = f"openai/{os.getenv('OPENAI_MODEL', 'google/gemini-2.5-flash-lite-preview-09-2025')}"
        api_base = os.getenv("API_BASE_URL", "https://openrouter.ai/api/v1")
        api_key = os.getenv("OPENAI_API_KEY", "EMPTY")
    max_concurrency = int(os.getenv("MAX_CONCURRENCY", "50"))

    print("Loading input dataset...")
    quality_corpus = load_dataset("json", data_files=input_dataset.path, split="train")

    print(f"Generating key facts for {len(quality_corpus)} documents...")

    FlowRegistry.discover_flows()
    flow_path = FlowRegistry.get_flow_path(
        "Key Facts Knowledge Tuning Dataset Generation Flow"
    )
    flow = Flow.from_yaml(flow_path)

    flow.set_model_config(
        model=hosted_model,
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

    generated_data.to_json(output_dataset.path, orient="records", lines=True)
    print(f"Generated {len(generated_data)} key facts records")
    print(f"Saved to: {output_dataset.path}")


@dsl.component(
    base_image=BASE_IMAGE,
    packages_to_install=[
        "datasets",
        "nest-asyncio",
        "sdg_hub[examples]",  # Install SDG Hub from Git
    ],
)
def generate_detailed_summary_component(
    input_dataset: Input[Dataset], output_dataset: Output[Dataset]
):
    """Generate detailed summary knowledge tuning data."""
    import os

    import nest_asyncio
    from datasets import load_dataset
    from sdg_hub import Flow, FlowRegistry

    nest_asyncio.apply()
    model_provider = os.getenv("MODEL_PROVIDER", "hosted_vllm")
    enable_reasoning = os.getenv("ENABLE_REASONING", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    if model_provider == "hosted_vllm":
        hosted_model = os.getenv(
            "VLLM_MODEL", "hosted_vllm/meta-llama/Llama-3.3-70B-Instruct"
        )
        api_base = os.getenv("API_BASE_URL", "http://localhost:8000/v1")
        api_key = os.getenv("VLLM_API_KEY", "EMPTY")
    elif model_provider == "openai":
        hosted_model = f"openai/{os.getenv('OPENAI_MODEL', 'google/gemini-2.5-flash-lite-preview-09-2025')}"
        api_base = os.getenv("API_BASE_URL", "https://openrouter.ai/api/v1")
        api_key = os.getenv("OPENAI_API_KEY", "EMPTY")
    number_of_summaries = int(os.getenv("NUMBER_OF_SUMMARIES", "50"))
    max_concurrency = int(os.getenv("MAX_CONCURRENCY", "50"))

    print("Loading input dataset...")
    quality_corpus = load_dataset("json", data_files=input_dataset.path, split="train")

    print(f"Generating detailed summaries for {len(quality_corpus)} documents...")

    FlowRegistry.discover_flows()
    flow_path = FlowRegistry.get_flow_path(
        "Detailed Summary Knowledge Tuning Dataset Generation Flow"
    )
    flow = Flow.from_yaml(flow_path)

    flow.set_model_config(
        model=hosted_model,
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

    generated_data.to_json(output_dataset.path, orient="records", lines=True)
    print(f"Generated {len(generated_data)} detailed summary records")
    print(f"Saved to: {output_dataset.path}")


@dsl.component(
    base_image="image-registry.openshift-image-registry.svc:5000/redhat-ods-applications/jupyter-minimal-cpu-py312-ubi9:2025.1",
    packages_to_install=[
        "datasets",
        "nest-asyncio",
        "sdg_hub[examples]",  # Install SDG Hub from Git
    ],
)
def generate_extractive_summary_component(
    input_dataset: Input[Dataset], output_dataset: Output[Dataset]
):
    """Generate extractive summary knowledge tuning data."""
    import os

    import nest_asyncio
    from datasets import load_dataset

    # Import SDG Hub - now available!
    from sdg_hub import Flow, FlowRegistry

    nest_asyncio.apply()

    # Read environment variables (injected by Kubernetes Secret)
    enable_reasoning = os.getenv("ENABLE_REASONING", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    model_provider = os.getenv("MODEL_PROVIDER", "hosted_vllm")
    if model_provider == "hosted_vllm":
        hosted_model = os.getenv(
            "VLLM_MODEL", "hosted_vllm/meta-llama/Llama-3.3-70B-Instruct"
        )
        api_base = os.getenv("API_BASE_URL", "http://localhost:8000/v1")
        api_key = os.getenv("VLLM_API_KEY", "EMPTY")
    elif model_provider == "openai":
        hosted_model = f"openai/{os.getenv('OPENAI_MODEL', 'google/gemini-2.5-flash-lite-preview-09-2025')}"
        api_base = os.getenv("API_BASE_URL", "https://openrouter.ai/api/v1")
        api_key = os.getenv("OPENAI_API_KEY", "EMPTY")
    number_of_summaries = int(os.getenv("NUMBER_OF_SUMMARIES", "50"))
    max_concurrency = int(os.getenv("MAX_CONCURRENCY", "50"))

    print("Loading input dataset...")
    quality_corpus = load_dataset("json", data_files=input_dataset.path, split="train")

    print(f"Model: {hosted_model}")
    print(f"API base: {api_base}")
    print(f"API key: {api_key}")
    print(f"Enable reasoning: {enable_reasoning}")
    print(f"Generating extractive summaries for {len(quality_corpus)} documents...")
    print(f"Number of summaries: {number_of_summaries}")
    print(f"Max concurrency: {max_concurrency}")

    # Discover and load the flow
    FlowRegistry.discover_flows()
    flow_path = FlowRegistry.get_flow_path(
        "Extractive Summary Knowledge Tuning Dataset Generation Flow"
    )
    flow = Flow.from_yaml(flow_path)

    # Set model configuration from environment variables
    flow.set_model_config(
        model=hosted_model,
        api_base=api_base,
        api_key=api_key,
        enable_reasoning=enable_reasoning,
    )

    # Configure runtime parameters
    runtime_params = {"gen_extractive_summary": {"n": number_of_summaries}}

    if enable_reasoning:
        runtime_params = {
            "question_generation": {"max_tokens": 1024},
            "gen_extractive_summary": {"n": number_of_summaries, "max_tokens": 6000},
        }

    # Generate data
    print("Starting generation...")
    generated_data = flow.generate(
        quality_corpus, runtime_params=runtime_params, max_concurrency=max_concurrency
    )

    # Save output
    generated_data.to_json(output_dataset.path, orient="records", lines=True)
    print(f"Generated {len(generated_data)} extractive summary records")
    print(f"Saved to: {output_dataset.path}")


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

    from datasets import load_dataset

    print("Loading all datasets...")

    # Load each dataset
    extractive = load_dataset("json", data_files=extractive_data.path, split="train")
    detailed = load_dataset("json", data_files=detailed_data.path, split="train")
    key_facts = load_dataset("json", data_files=key_facts_data.path, split="train")
    doc_qa = load_dataset("json", data_files=doc_qa_data.path, split="train")

    # Combine all datasets
    print(f"  - Extractive: {len(extractive)} records")
    print(f"  - Detailed: {len(detailed)} records")
    print(f"  - Key Facts: {len(key_facts)} records")
    print(f"  - Doc QA: {len(doc_qa)} records")

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


@dsl.pipeline(
    name="Knowledge Generation Pipeline",
    description="Generate knowledge tuning datasets using SDG Hub",
)
def knowledge_generation_pipeline():
    """
    Knowledge generation pipeline that creates multiple types of training data.

    Environment variables (from Kubernetes Secret 'sdg-pipeline-config'):
    - MODEL_PROVIDER: Model provider (hosted_vllm, openai, ollama, maas)
    - VLLM_MODEL: Model name/path
    - API_BASE_URL: API base URL
    - VLLM_API_KEY: API key
    - ENABLE_REASONING: Enable reasoning mode (true/false)
    - SEED_DATA_PATH: Path to seed data file (default: seed_data.jsonl)
    - SEED_DATA_SUBSAMPLE: Number of samples to subsample (0 = no subsampling)

    Args:
        run_on_validation: Whether to use validation subset
        num_samples: Number of samples to process (0 = all)
        number_of_summaries: Number of summaries to generate per document
        seed_data_path: Path to seed data file
    """

    # Step 1: Create or load seed data
    seed_data_task = create_seed_data_component()

    # Step 2-5: Generate different types of data in parallel
    extractive_summary_task = generate_extractive_summary_component(
        input_dataset=seed_data_task.outputs["output_dataset"]
    )

    detailed_summary_task = generate_detailed_summary_component(
        input_dataset=seed_data_task.outputs["output_dataset"],
    )

    key_facts_task = generate_key_facts_component(
        input_dataset=seed_data_task.outputs["output_dataset"],
    )

    document_qa_task = generate_document_based_qa_component(
        input_dataset=seed_data_task.outputs["output_dataset"],
    )

    generation_tasks = [
        extractive_summary_task,
        detailed_summary_task,
        key_facts_task,
        document_qa_task,
    ]

    for task in generation_tasks:
        kubernetes.use_secret_as_env(
            task,
            secret_name="sdg-pipeline-config",
            secret_key_to_env={
                "MODEL_PROVIDER": "MODEL_PROVIDER",
                "VLLM_MODEL": "VLLM_MODEL",
                "API_BASE_URL": "API_BASE_URL",
                "VLLM_API_KEY": "VLLM_API_KEY",
                "OPENAI_MODEL": "OPENAI_MODEL",
                "OPENAI_API_KEY": "OPENAI_API_KEY",
                "ENABLE_REASONING": "ENABLE_REASONING",
                "NUMBER_OF_SUMMARIES": "NUMBER_OF_SUMMARIES",
                "MAX_CONCURRENCY": "MAX_CONCURRENCY",
                "LITELLM_REQUEST_TIMEOUT": "LITELLM_REQUEST_TIMEOUT",
            },
        )

    # Also apply environment variables to the seed data task
    kubernetes.use_secret_as_env(
        seed_data_task,
        secret_name="sdg-pipeline-config",
        secret_key_to_env={
            "SEED_DATA_PATH": "SEED_DATA_PATH",
            "SEED_DATA_SUBSAMPLE": "SEED_DATA_SUBSAMPLE",
        },
    )

    # NEW: Merge all outputs into one file
    merge_all_outputs_component(
        extractive_data=extractive_summary_task.outputs["output_dataset"],
        detailed_data=detailed_summary_task.outputs["output_dataset"],
        key_facts_data=key_facts_task.outputs["output_dataset"],
        doc_qa_data=document_qa_task.outputs["output_dataset"],
    )


if __name__ == "__main__":
    # Compile the pipeline
    compiler.Compiler().compile(
        pipeline_func=knowledge_generation_pipeline,
        package_path="knowledge_generation_pipeline.yaml",
    )
    print("Pipeline compiled successfully to knowledge_generation_pipeline.yaml")
    print("\nNext steps:")
    print("1. Create Kubernetes Secret:")
    print(
        "   kubectl create secret generic sdg-pipeline-config --from-env-file=.env -n kubeflow"
    )
    print("2. Upload pipeline to Kubeflow and run it!")
