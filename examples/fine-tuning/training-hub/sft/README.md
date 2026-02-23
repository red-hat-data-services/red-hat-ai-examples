# SFT Fine-Tuning with Kubeflow Training on OpenShift AI

This example provides an overview of the [SFT algorithm from Training Hub](https://github.com/Red-Hat-AI-Innovation-Team/training_hub?tab=readme-ov-file#supervised-fine-tuning-sft) and an example on how to use it with Red Hat OpenShift AI.

## Execution modes

Training Hub SFT supports two execution modes:

- **Interactive Notebooks (Single Node Fine Tuning)**: training runs directly in a workbench on a single pod, demonstrated by `sft-interactive-notebook.ipynb`.
- **Training Jobs (Distributed Fine Tuning with Kubeflow Trainer)**: training runs as distributed jobs across multiple nodes/pods via Kubeflow Trainer, demonstrated by `sft-distributed.ipynb`.

While workbench setup is similar for both, we highlight specific configuration differences below.

To learn more about execution modes, see the [fine-tuning execution modes overview](../../README.md#execution-modes).

## RHOAI compatibility

This example is compatible with RHOAI version 3.3. For a version compatible with RHOAI 3.2 see [this README](../rhoai-3.2/training-hub/sft/README.md). For RHOAI 3.0 see [this README](../rhoai-3.0/training-hub/sft/README.md).

> [!IMPORTANT]
> This example has been tested with the configurations listed in the [validation](#validation) section.
> If you have different hardware configuration you can check [training-hub memory estimator](https://github.com/Red-Hat-AI-Innovation-Team/training_hub/tree/main/examples#memory-estimation-experimental--in-development) to validate your
> hardware configuration will be sufficient to run this example.

## Requirements

- An OpenShift cluster with OpenShift AI (RHOAI) 3.3 installed:
  - The `dashboard` and `workbenches` components enabled
  - The `trainer` component should be enabled if running the distributed notebook.
- Sufficient worker nodes for your configuration(s) with NVIDIA GPUs (Ampere-based or newer recommended).
- (Distributed Example only) A dynamic storage provisioner supporting RWX PVC provisioning. Talk to your cluster administrator about RWX storage options.

## Setup

## Hardware requirements to run the example notebook

### Workbench Requirements

| Image Type | Use Case | GPU | CPU | Memory | Notes |
|------------|----------|-----|-----|--------|-------|
| CUDA PyTorch Python 3.12 | NVIDIA GPU training | 1× GPU | 4 cores | 32Gi | Recommended for faster training/evaluation |

> [!NOTE]
>
> - **Interactive notebooks (single node fine tuning)** are recommended for smaller training jobs.
> - For larger training jobs, consider the **training jobs (distributed fine tuning with Kubeflow Trainer)** approach.

### Setup Workbench

- Access the OpenShift AI dashboard, for example from the top navigation bar menu:
![](./images/01.png)
- Log in, then go to _Data Science Projects_ and create a project:
![](./images/02.png)
- Once the project is created, click on _Create a workbench_:
![](./images/03.png)
- Then create a workbench with the following settings:
  - Select the `Jupyter | PyTorch | CUDA | Python 3.12`  notebook image:
    ![](./images/04a.png)
  - Add a **Hardware Profile** for reuse within the Workbench settings
    ![](./images/04b.png)
  - Select the Hardware profile just created
    ![](./images/04c.png)
    > [!NOTE]
    > Adding an accelerator (GPU) is only needed in distributed mode to test the fine-tuned model from within the workbench so you can spare an accelerator if needed. An accelerator (GPU) is needed in interactive mode as the training happens on the workbench pod.
  - Create a storage that'll be shared between the workbench and the fine-tuning runs. (Only required for distributed)
    Make sure it uses a storage class with RWX capability and give it enough size according to the size of the model you want to fine-tune. For interactive mode, the default storage is sufficient.
    ![](./images/04d.png)
    ![](./images/04e.png)
    > [!NOTE]
    > You can attach an existing shared storage if you already have one instead.
  - Review the configuration and click "Create workbench":
    ![](./images/04f.png)

### Running the example notebooks

- From "Workbenches" page, click on _Open_ when the workbench you've just created becomes ready:
  ![](./images/05.png)
- From the workbench, clone this repository, i.e., `https://red-hat-data-services/red-hat-ai-examples.git`
- Navigate to the `examples/fine-tuning/training-hub/sft` directory and open the [`sft-interactive-notebook.ipynb`](./sft-interactive-notebook.ipynb) notebook or [`sft-distributed.ipynb`](./sft-distributed.ipynb) as required

> [!IMPORTANT]
>
> - You will need a Hugging Face token if using gated models:
>   - The examples use gated Llama models that require a token (e.g., <https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct>)
>   - Set the `HF_TOKEN` environment variable in your job configuration
>   - Note: You can skip the token if switching to non-gated models
> - This example supports Kueue integration for workload management:
>   - When using Kueue:
>     - Follow the [Configure Kueue (Optional)](#configure-kueue-optional) section to set up required resources
>     - Add the local-queue name label to your job configuration to enforce workload management
>   - You can skip Kueue usage by:
>
>       > [!NOTE]
>       > Kueue Enablement via Validating Admission Policy was introduced in RHOAI 2.21. You can skip this section if using an earlier RHOAI release version.
>
>     - Disabling the existing `kueue-validating-admission-policy-binding`
>     - Omitting the local-queue-name label in your job configuration

You can now proceed with the instructions from the notebook. Enjoy!

### Configure Kueue (Optional)

> [!NOTE]
> This section is only required if you plan to use Kueue for workload management  or
> Kueue is not already configured in your cluster.
> Resources below can be found in the [distributed-workloads repository](https://github.com/opendatahub-io/distributed-workloads/tree/main/workshops/kueue)

- Update the `nodeLabels` in the `workshops/kueue/resources/resource_flavor.yaml` file to match your AI worker nodes
- Create the ResourceFlavor:

    ```console
    oc apply -f workshops/kueue/resources/resource_flavor.yaml
    ```

- Create the ClusterQueue:

    ```console
    oc apply -f workshops/kueue/resources/team1_cluster_queue.yaml
    ```

- Create a LocalQueue in your namespace:

    ```console
    oc apply -f workshops/kueue/resources/team1_local_queue.yaml -n <your-namespace>
    ```

## Validation

This example has been validated with the following configurations:

### Qwen2.5 1.5B Instruct - TableGPT Dataset - Training-Hub - 4x NVIDIA A100/80G

- Infrastructure:
  - OpenShift AI 3.0
  - 8x NVIDIA-A100-SXM4-80GB
- Configuration:

    ```yaml
  # ################################################################################
  # # 🤖 Model + Data Paths                                                          #
  # ################################################################################
  base_model: "/mnt/shared/Qwen/Qwen2.5-1.5B-Instruct"
  dataset_path: "/mnt/shared/table-gpt-data/train/train_All_5000.jsonl"
  checkpoints_path: "/mnt/shared/checkpoints"
  # for quicker multi-process loading of datasets set this to /dev/shm
  data_output_path: "/mnt/shared/traininghub-sft-data"

  # ################################################################################
  # # 🏋️‍♀️ Training Hyperparameters                                                     #
  # ################################################################################
  # Standard parameters
  batch_size: 128
  learning_rate: 5.0e-6  # You can also write this as 0.000005
  num_epochs: 1
  lr_scheduler: "cosine"
  warmpup_steps: 0
  seed: 42

  # ################################################################################
  # # 🏎️ Performance Hyperparameters                                                  #
  # ################################################################################
  max_tokens_per_gpu: 10000
  max_seq_len: 8192

  # ################################################################################
  # # 💾 Checkpointing Settings                                                      #
  # ################################################################################
  checkpoint_at_epoch: true
  save_full_optim_state: false

  # ###############################################################################
  # # 🔥 TORCHRUN SETTINGS will be injected automatically by Kubeflow Trainer      #
  # ###############################################################################
    ```

- Job:

    ```yaml
    num_workers: 4
    num_procs_per_worker: 1
    resources_per_worker:
      "nvidia.com/gpu": 1
      "memory": 64Gi
      "cpu": 4
    base_image: quay.io/modh/training:py312-cuda128-torch280
    env_vars:
      "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"
      "NCCL_DEBUG": "INFO"
    ```

### Qwen2.5 7B Instruct - TableGPT Dataset - Training-Hub - 4x NVIDIA A100/80G

- Infrastructure:
  - OpenShift AI 3.0
  - 8x NVIDIA-A100-SXM4-80GB
- Configuration:

    ```yaml
  # ################################################################################
  # # 🤖 Model + Data Paths                                                          #
  # ################################################################################
  base_model: "/mnt/shared/Qwen/Qwen2.5-7B-Instruct"
  dataset_path: "/mnt/shared/table-gpt-data/train/train_All_5000.jsonl"
  checkpoints_path: "/mnt/shared/checkpoints"
  # for quicker multi-process loading of datasets set this to /dev/shm
  data_output_path: "/mnt/shared/traininghub-sft-data"

  # ################################################################################
  # # 🏋️‍♀️ Training Hyperparameters                                                     #
  # ################################################################################
  # Standard parameters
  batch_size: 128
  learning_rate: 5.0e-6  # You can also write this as 0.000005
  num_epochs: 1
  lr_scheduler: "cosine"
  warmpup_steps: 0
  seed: 42

  # ################################################################################
  # # 🏎️ Performance Hyperparameters                                                  #
  # ################################################################################
  max_tokens_per_gpu: 10000
  max_seq_len: 8192

  # ################################################################################
  # # 💾 Checkpointing Settings                                                      #
  # ################################################################################
  checkpoint_at_epoch: true
  save_full_optim_state: false

  # ###############################################################################
  # # 🔥 TORCHRUN SETTINGS will be injected automatically by Kubeflow Trainer      #
  # ###############################################################################
    ```

- Job:

    ```yaml
    num_workers: 4
    num_procs_per_worker: 1
    resources_per_worker:
      "nvidia.com/gpu": 1
      "memory": 64Gi
      "cpu": 4
    base_image: quay.io/modh/training:py312-cuda128-torch280
    env_vars:
      "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"
      "NCCL_DEBUG": "INFO"
    ```

### Qwen2.5 14B Instruct - TableGPT Dataset - Training-Hub - 4x NVIDIA A100/80G

- Infrastructure:
  - OpenShift AI 3.0
  - 8x NVIDIA-A100-SXM4-80GB
- Configuration:

    ```yaml
  # ################################################################################
  # # 🤖 Model + Data Paths                                                          #
  # ################################################################################
  base_model: "/mnt/shared/Qwen/Qwen2.5-14B-Instruct"
  dataset_path: "/mnt/shared/table-gpt-data/train/train_All_5000.jsonl"
  checkpoints_path: "/mnt/shared/checkpoints"
  # for quicker multi-process loading of datasets set this to /dev/shm
  data_output_path: "/mnt/shared/traininghub-sft-data"

  # ################################################################################
  # # 🏋️‍♀️ Training Hyperparameters                                                     #
  # ################################################################################
  # Standard parameters
  batch_size: 128
  learning_rate: 5.0e-6  # You can also write this as 0.000005
  num_epochs: 1
  lr_scheduler: "cosine"
  warmpup_steps: 0
  seed: 42

  # ################################################################################
  # # 🏎️ Performance Hyperparameters                                                  #
  # ################################################################################
  max_tokens_per_gpu: 10000
  max_seq_len: 8192

  # ################################################################################
  # # 💾 Checkpointing Settings                                                      #
  # ################################################################################
  checkpoint_at_epoch: true
  save_full_optim_state: false

  # ###############################################################################
  # # 🔥 TORCHRUN SETTINGS will be injected automatically by Kubeflow Trainer      #
  # ###############################################################################
    ```

- Job:

    ```yaml
    num_workers: 4
    num_procs_per_worker: 1
    resources_per_worker:
      "nvidia.com/gpu": 1
      "memory": 64Gi
      "cpu": 4
    base_image: quay.io/modh/training:py312-cuda128-torch280
    env_vars:
      "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"
      "NCCL_DEBUG": "INFO"
    ```
