# LoRA/QLoRA Fine-Tuning with Training Hub

This notebook demonstrates how to use Training Hub's LoRA (Low-Rank Adaptation) and QLoRA capabilities for parameter-efficient fine-tuning using Red Hat OpenShift AI. We'll train a model to convert natural language questions into SQL queries using the popular [sql-create-context](https://huggingface.co/datasets/b-mc2/sql-create-context) dataset.

**Known issues**

- Multi-node distributed is not currently supported as LoRA via Training Hub relies on Unsloth which does not currently support it.
- QLORA currently does not support 8 bit quantization mode, only 4bit quantization is supported because of limitations of unsloth.

## What is LoRA?

LoRA (Low-Rank Adaptation) is a parameter-efficient fine-tuning technique that:

- Freezes the pre-trained model weights
- Injects trainable low-rank matrices into each layer
- Reduces trainable parameters by ~10,000x compared to full fine-tuning
- Enables fine-tuning large models on consumer GPUs

**QLoRA** extends LoRA by adding 4-bit quantization, further reducing memory requirements while maintaining quality.

## Training Task: Natural Language to SQL

We'll train the model to understand database schemas and generate SQL queries from natural language questions. For example:

**Input:**

```text
Table: employees (id, name, department, salary)
Question: What is the average salary in the engineering department?
```

**Output:**

```sql
SELECT AVG(salary) FROM employees WHERE department = 'engineering'
```

## Execution modes

## Note

LORA/QLORA supports:

- **Interactive Notebooks (Single Node Fine Tuning)**: training runs directly in a workbench on a single pod, demonstrated by `lora-interactive-notebook.ipynb`.

## Hardware requirements to run the example notebook

### Workbench Requirements (interactive mode)

| Image Type | Use Case | GPU | CPU | Memory | Notes |
|------------|----------|-----|-----|--------|-------|
| CUDA PyTorch Python 3.12 | NVIDIA GPU training | 1× GPU | 4 cores | 32Gi | Recommended for faster training |

**Note**

- Interactive mode is recommended for smaller training jobs.

**Note**

- Workbench GPU is optional but recommended for faster model evaluation
- Evaluation was performed on L40S GPU however, it will work on smaller/larger configurations.
- Workbench resources and accelerator are configurable in `Create Workbench` view on RHOAI Platform

**Note**

- Storage can be created in `Create Workbench` view on RHOAI Platform, however, dynamic RWX provisioner is required to be configured prior to creating shared file storage in RHOAI.

## Setup

### Setup Workbench

- **Access the OpenShift AI dashboard**, for example from the top navigation bar menu:
  ![](./docs/01.png)

- Log in, then go to **_Projects_** and create a project:
  ![](./docs/02.png)

- Once the project is created, click on **_Create a workbench_**:
  ![](./docs/03.png)

- Then create a workbench with the following settings:
  - Select the appropriate Workbench based on interactive . See options above:
    ![](./docs/04a.png)

  - Similarly, you may want to add a **Hardware Profile** for reuse within the Workbench settings
    ![](./docs/04b.png)

  - Select the Hardware profile just created:
    ![](./docs/04c.png)
    > [!NOTE]
    > An accelerator (GPU) is required in interactive mode as the training happens on the workbench pod.

  - Review the storage configuration and click "Create workbench":
    ![](./docs/04e.png)

- From "Workbenches" page, click on **_Open_** when the workbench you've just created becomes ready:
  ![](./docs/05.png)

**Important**

- By default:
  - For the interactive example an accelerator is required for the WorkBench to execute the fine tuning with LORA.

### Running the example notebooks

- From the workbench, clone this repository, i.e., `https://red-hat-data-services/red-hat-ai-examples.git`
  ![](./docs/06.png)
- Navigate to the `examples/fine-tuning/lora` directory and open the [`lora_sft-interactive-notebook.ipynb`](./lora_sft-interactive-notebook.ipynb) notebook.
