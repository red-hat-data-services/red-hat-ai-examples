# Model Compression and Evaluation on Red Hat OpenShift AI (RHOAI)

The compression and optimization of pretrained, off-the-shelf large language models (LLMs) is essential for organizations to reduce the hardware and energy requirements of their AI applications. This set of examples will introduce RHOAI users (Machine Learning Engineers and Data Scientists) to model compression using two tools in the open-source VLLM project:

1. [`llm-compressor`](https://github.com/vllm-project/llm-compressor) to compress models.
2. The [`vllm`](https://github.com/vllm-project/vllm) deployment engine to evaluate the performance of compressed models.

While research in model compression is continually evolving and growing increasingly complex, the examples require only a basic understanding of Python and the [HuggingFace software ecosystem](https://huggingface.co/docs/transformers/index). By the end, users should know how to run and compare the performance of different compression techniques, and how to customize to their own dataset or pretrained model.

> [!NOTE]
> We also publish compressed versions of popular LLMs to HuggingFace that can be downloaded directly at <https://huggingface.co/RedHatAI>

## Contents

Two pathways are provided:

1. [A Jupyter Notebook](workbench_example.ipynb) that can be used with the workbench image available at <https://quay.io/repository/opendatahub/llmcompressor-workbench>.

2. [An example pipeline](oneshot_pipeline.py) splits the notebook up into components that can be run as a Data Science Pipeline, with the runtime image available at <https://quay.io/repository/opendatahub/llmcompressor-pipeline-runtime>. The goal of this is to highlight how multiple compression algorithms can be compared in parallel, with compressed model artifacts and evaluation results easily shareable with stakeholders in a single web UI.

## Prerequisites

These examples assume the user has access to a Data Science Project on a Red Hat OpenShift AI cluster. The [Data Science Pipelines feature](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/2.19/html/working_with_data_science_pipelines/index) must be enabled in your project to run the pipeline. Users must `pip install -r requirements.txt` in order to run `oneshot_pipeline.py`.

### Accessing HuggingFace Hub Models

Many popular open-source models on the HuggingFace Model Hub are [gated](https://huggingface.co/docs/hub/en/models-gated), requiring users to provide basic information and accept a EULA before being granted access to download the model. Users must [generate a token](https://huggingface.co/docs/hub/en/security-tokens) to access models, and provide that token in workbenches and pipelines.

In workbenches, users can embed the token directly in the notebook:

```python
import os
os.environ["HF_TOKEN"] = "<your token here>"
```

In pipelines, users need to create a secret that can be passed as an env var to the running container. The example pipeline demonstrates this, provided the user has created a secret for the project:

1. In OpenShift console, select Secrets on left sidebar.
2. Click Create -> Key/value secret with
    - Secret name: `hf-hub-secret`
    - Key: `HF_TOKEN`
    - Value: `<your token here>`

With this, the token will be added whenever the task is modified accordingly:

```python
kubernetes.use_secret_as_env(
    calibrated_task,
    secret_name="hf-hub-secret",
    secret_key_to_env={"HF_TOKEN": "HF_TOKEN"},
)
```

### Using Accelerated Hardware

Data-free compression flows can typically run in a short amount of time on CPU, but calibrated compression often requires accelerated hardware. The examples demonstrate both, and the images are built to be compatible with NVIDIA GPUs with [compute capability](https://developer.nvidia.com/cuda-gpus) 7.0 or higher.

> [!NOTE]
> Certain features in `vllm` require higher compute capability -- <https://docs.vllm.ai/en/stable/features/compatibility_matrix.html>

As a best practice, RHOAI clusters configure GPU nodes with [taints](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/) so that tasks that don't require GPUs are not generally deployed to them. The pipeline example assumes cluster nodes with NVIDIA A10 devices are also configured with a taint `NVIDIA-A10G-SHARED`. To ensure the task is deployed to that node, we add a toleration:

```python
kubernetes.add_toleration(
    calibrated_task,
    key="nvidia.com/gpu",
    operator="Equal",
    value="NVIDIA-A10G-SHARED",
    effect="NoSchedule",
)
```

Users may have to update this to match the taint configured by the cluster administrator, or remove if the taint does not exist.
