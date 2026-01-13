
# Knowledge Tuning example

Welcome! This repository contains a self-contained Knowledge Tuning example that uses the InstructLab methodology.

By following the steps in this example, you learn how to inject domain-specific knowledge into an AI model, improving its accuracy and relevance for an example use case.

## Overview of the example end-to-end workflow

In this example workflow, you complete the following modules sequentially in your workbench environment, as illustrated in Figure 1 and Figure 2:

1. Base Model Evaluation - Run the base model before you train, to evaluate its preliminary performance.
2. Data Processing — Convert a URL page to structured Markdown format by using Docling. Chunk text and produce a small seed dataset.
3. Knowledge Generation — Expand the seed dataset and generate more question and answer (Q&A) pairs by using an LLM teacher model.
4. Knowledge Mixing — Combine generated Q&A pairs and summaries into training mixes.
5. Model Training — Fine-tune a model by using the training mixes.
6. Evaluation — Run the trained model and generated datasets against held-out test data.

*Figure 1. End-to-end workflow overview*

![End-to-end workflow overview diagram](../../assets/usecase/knowledge-tuning/Overall%20Flow.png)

*Figure 2. End-to-end workflow details*

![End-to-end workflow detailed diagram](../../assets/usecase/knowledge-tuning/Detailed%20Flow.png)

## About the example use case

A Canadian bank wants its employees to use the bank’s internal chatbot app to obtain accurate information about the client identification methods required by the Financial Transactions and Reports Analysis Centre of Canada (FINTRAC).

A general-purpose language model lacks the specific, nuanced knowledge of Canadian anti-money laundering (AML) regulations. When asked a detailed, specific question, it is likely to provide a generic or incorrect answer.

In this example, your goal is to fine-tune a base model on the official FINTRAC guidance so that it provides accurate, context-specific answers that reflect the actual regulations.

## About the models

This example follows the Teacher-Student model paradigm. The student model (also known as the base model) is `RedHatAI/Llama-3.1-8B-Instruct`. The teacher model is `openai/gpt-oss-120b`. The teacher model is a large, complex, and highly accurate model that serves as a source of knowledge. It generates training data for the smaller student model. The student model learns from the teacher’s outputs to improve its performance. Both models in this example are open-source and do not require API keys to access them.

## About the example Git repo structure

The files for each module in the workflow are organized in subfolders of this Git repository, under the `examples/knowledge-tuning/` folder. Each subfolder contains a notebook, a `pyproject.toml` file for dependencies, an `.env.example` file for environment variables, and a `README.md` file.

## Next step

Proceed to [Setup](./00_Setup/00_Setup_README.md).
