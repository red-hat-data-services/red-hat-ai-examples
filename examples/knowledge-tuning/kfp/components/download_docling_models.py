from kfp import dsl

DOCLING_BASE_IMAGE = "quay.io/fabianofranz/docling-ubi9:2.54.0"


@dsl.component(base_image=DOCLING_BASE_IMAGE)
def download_docling_models(
    output_path: dsl.Output[dsl.Artifact],
    pipeline_type: str = "standard",
    remote_model_endpoint_enabled: bool = False,
):
    from pathlib import Path  # pylint: disable=import-outside-toplevel

    from docling.utils.model_downloader import (
        download_models,
    )  # pylint: disable=import-outside-toplevel

    output_path_p = Path(output_path.path)
    output_path_p.mkdir(parents=True, exist_ok=True)

    if pipeline_type == "standard":
        # Standard pipeline: download traditional models
        print("Downloading standard pipeline models...")
        download_models(
            output_dir=output_path_p,
            progress=True,
            with_layout=True,
            with_tableformer=True,
            with_easyocr=True,
        )
    elif pipeline_type == "vlm" and remote_model_endpoint_enabled:
        # VLM pipeline with remote model endpoint: Download minimal required models
        # Only models set are what lives in fabianofranz repo
        # TODO: figure out what needs to be downloaded or removed
        download_models(
            output_dir=output_path_p,
            progress=False,
            force=False,
            with_layout=True,
            with_tableformer=True,
            with_code_formula=False,
            with_picture_classifier=False,
            with_smolvlm=False,
            with_smoldocling=False,
            with_smoldocling_mlx=False,
            with_granite_vision=False,
            with_easyocr=False,
        )
    elif pipeline_type == "vlm":
        # VLM pipeline with local models: Download VLM models for local inference
        # TODO: set models downloaded by model name passed into KFP pipeline ex: smoldocling OR granite-vision
        download_models(
            output_dir=output_path_p,
            with_smolvlm=True,
            with_smoldocling=True,
            progress=False,
            force=False,
            with_layout=False,
            with_tableformer=False,
            with_code_formula=False,
            with_picture_classifier=False,
            with_smoldocling_mlx=False,
            with_granite_vision=False,
            with_easyocr=False,
        )
    else:
        raise ValueError(
            f"Invalid pipeline_type: {pipeline_type}. Must be 'standard' or 'vlm'"
        )
