import kfp
import kfp.kubernetes
from components.document_processing import document_processing
from components.download_docling_models import download_docling_models
from components.knowledge_generation import (
    generate_detailed_summaries,
    generate_document_based_qa,
    generate_extractive_summaries,
    generate_key_facts_summary,
    merge_all_outputs_component,
)
from components.knowledge_mixing import knowledge_mixing
from kfp import compiler, dsl
from kfp_components.components.training.finetuning import train_model

PVC_SIZE = "80Gi"
PVC_STORAGE_CLASS = "nfs-csi"
PVC_ACCESS_MODES = ["ReadWriteMany"]


@dsl.pipeline(
    name="knowledge-tuning-pipeline",
    description="A pipeline for knowledge tuning using document processing.",
    pipeline_config=dsl.PipelineConfig(
        workspace=dsl.WorkspaceConfig(
            size=PVC_SIZE,
            kubernetes=dsl.KubernetesWorkspaceConfig(
                pvcSpecPatch={
                    "accessModes": PVC_ACCESS_MODES,
                    "storageClassName": PVC_STORAGE_CLASS,
                }
            ),
        ),
    ),
)
def convert_pipeline(
    #  Document processing parameters
    web_urls: str = "https://fintrac-canafe.canada.ca/guidance-directives/client-clientele/Guide11/11-eng",
    chunk_max_tokens: int = 512,
    chunk_overlap_tokens: int = 50,
    domain: str = "None",
    domain_outline: str = "None",
    icl_document: str = "None",
    icl_query1: str = "None",
    icl_query2: str = "None",
    icl_query3: str = "None",
    # Knowledge generation parameters
    model_name: str = "openai/gpt-oss-20b",
    api_key: str = "",
    api_base: str = "",
    seed_data_subsample: int = 0,
    enable_reasoning: bool = True,
    number_of_summaries: int = 1,
    max_concurrency: int = 5,
    inference_timeout: int = 2500,
    # Knowledge Mixing parameters
    tokenizer_model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
    cut_size: str = "1,5,10",
    qa_per_doc: int = 3,
    save_gpt_oss_format: bool = False,
    # Model Training parameters
    student_model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
    training_resource_gpu_per_worker: int = 8,
    training_num_epochs: int = 1,
    training_effective_batch_size: int = 32,
    training_resource_memory_per_worker: str = "40Gi",
):

    # Step 1 : Document Processing
    # Download models first - they'll be saved as an artifact
    artifacts = download_docling_models()
    artifacts.set_caching_options(True)

    # Document processing will use models from the artifact via DOCLING_CACHE_DIR env var
    document_processing_task = document_processing(
        artifacts_path=artifacts.outputs["output_path"],
        chunk_max_tokens=chunk_max_tokens,
        web_urls=web_urls,
        chunk_overlap_tokens=chunk_overlap_tokens,
        domain=domain,
        document_outline=domain_outline,
        icl_document=icl_document,
        icl_query1=icl_query1,
        icl_query2=icl_query2,
        icl_query3=icl_query3,
    )
    document_processing_task.set_caching_options(False)

    # Step 2: Knowledge Generation
    # Knowledge Generation - Generate 4 different types of datasets
    detailed_summary_task = generate_detailed_summaries(
        input_dataset=document_processing_task.outputs["output_path"],
        model_name=model_name,
        api_key=api_key,
        api_base=api_base,
        seed_data_subsample=seed_data_subsample,
        enable_reasoning=enable_reasoning,
        max_concurrency=max_concurrency,
        inference_timeout=inference_timeout,
        number_of_summaries=number_of_summaries,
    )
    detailed_summary_task.set_caching_options(False)

    extractive_summary_task = generate_extractive_summaries(
        input_dataset=document_processing_task.outputs["output_path"],
        model_name=model_name,
        api_key=api_key,
        api_base=api_base,
        seed_data_subsample=seed_data_subsample,
        enable_reasoning=enable_reasoning,
        number_of_summaries=number_of_summaries,
        max_concurrency=max_concurrency,
        inference_timeout=inference_timeout,
    )
    extractive_summary_task.set_caching_options(False)

    key_facts_summary_task = generate_key_facts_summary(
        input_dataset=document_processing_task.outputs["output_path"],
        model_name=model_name,
        api_key=api_key,
        api_base=api_base,
        seed_data_subsample=seed_data_subsample,
        enable_reasoning=enable_reasoning,
        max_concurrency=max_concurrency,
        inference_timeout=inference_timeout,
    )
    key_facts_summary_task.set_caching_options(False)

    document_based_qa_task = generate_document_based_qa(
        input_dataset=document_processing_task.outputs["output_path"],
        model_name=model_name,
        api_key=api_key,
        api_base=api_base,
        seed_data_subsample=seed_data_subsample,
        enable_reasoning=enable_reasoning,
        max_concurrency=max_concurrency,
        inference_timeout=inference_timeout,
    )
    document_based_qa_task.set_caching_options(False)

    # Extractive summary is heavy on the inference server
    # So its not feasible to parallize this process with the dataset
    extractive_summary_task.after(
        document_based_qa_task, detailed_summary_task, key_facts_summary_task
    )

    merged_dataset_task = merge_all_outputs_component(
        extractive_data=extractive_summary_task.outputs["output_path"],
        detailed_data=detailed_summary_task.outputs["output_path"],
        key_facts_data=key_facts_summary_task.outputs["output_path"],
        doc_qa_data=document_based_qa_task.outputs["output_path"],
    )
    merged_dataset_task.set_caching_options(False)

    # Step 3: Knowledge Mixing
    # Knowledge Mixing
    knowledge_mixing_task = knowledge_mixing(
        datasets_path=merged_dataset_task.outputs["merged_output"],
        tokenizer_model_name=tokenizer_model_name,
        cut_size=cut_size,
        qa_per_doc=qa_per_doc,
        save_gpt_oss_format=save_gpt_oss_format,
    )
    knowledge_mixing_task.set_caching_options(False)

    # Step 4:
    # Model Finetuning
    train_model_task = train_model(
        pvc_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
        dataset=knowledge_mixing_task.outputs["dataset_file"],
        training_base_model=student_model_name,
        training_resource_gpu_per_worker=training_resource_gpu_per_worker,
        training_num_epochs=training_num_epochs,
        training_effective_batch_size=training_effective_batch_size,
        training_resource_memory_per_worker=training_resource_memory_per_worker,
    )

    # Pass the required secrets to the training step
    kfp.kubernetes.use_secret_as_env(
        task=train_model_task,
        secret_name="kubernetes-credentials",  # pragma: allowlist secret
        secret_key_to_env={
            "KUBERNETES_SERVER_URL": "KUBERNETES_SERVER_URL",
            "KUBERNETES_AUTH_TOKEN": "KUBERNETES_AUTH_TOKEN",  # pragma: allowlist secret
            "HF_TOKEN": "HF_TOKEN",  # pragma: allowlist secret
        },
        optional=False,
    )


if __name__ == "__main__":
    compiler.Compiler().compile(
        pipeline_func=convert_pipeline,
        package_path="knowledge_tuning_pipeline.yaml",
    )
