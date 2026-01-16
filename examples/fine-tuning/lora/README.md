# LoRA/QLoRA Fine-Tuning with Training Hub

This notebook demonstrates how to use Training Hub's LoRA (Low-Rank Adaptation) and QLoRA capabilities for parameter-efficient fine-tuning. We'll train a model to convert natural language questions into SQL queries using the popular [sql-create-context](https://huggingface.co/datasets/b-mc2/sql-create-context) dataset.

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
```
Table: employees (id, name, department, salary)
Question: What is the average salary in the engineering department?
```

**Output:**
```sql
SELECT AVG(salary) FROM employees WHERE department = 'engineering'
```

## Hardware Requirements

This notebook is designed to run on a single GPU:
- **Minimum**: 16GB VRAM (with QLoRA 4-bit quantization)
- **Recommended**: 24GB VRAM (for faster training with larger batch sizes)
- Works on: A10, A100, L4, L40S, RTX 3090/4090, and similar GPUs