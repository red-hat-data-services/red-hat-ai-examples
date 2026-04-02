# AutoML

**AutoML** on Red Hat OpenShift AI ships as **two Kubeflow pipeline definitions** in [pipelines-components](https://github.com/red-hat-data-services/pipelines-components): **tabular** classification/regression (`autogluon-tabular-training-pipeline`) and **time series** forecasting (`autogluon-timeseries-training-pipeline`). You provide data in S3 and the parameters for the pipeline you run; AutoGluon trains and compares models, ranks them on a leaderboard, and produces artifacts (including notebooks). See [What you need to provide](#what-you-need-to-provide), [Example scenarios](#example-scenarios), and the tutorials below.

## Status

**[Developer Preview](https://access.redhat.com/support/offerings/devpreview)** — This feature is not yet supported with Red Hat production service level agreements (SLAs) and may change. It provides early access for testing and feedback.

---

## Table of contents

- [Status](#status)
- [About AutoML](#about-automl)
  - [What AutoML gives you](#what-automl-gives-you)
  - [What AutoML supports](#what-automl-supports)
  - [How it works under the hood](#how-it-works-under-the-hood)
    - [Tabular pipeline flow](#tabular-pipeline-flow)
    - [Time series pipeline flow](#time-series-pipeline-flow)
- [What you need to provide](#what-you-need-to-provide)
  - [Tabular pipeline parameters](#tabular-pipeline-autogluon-tabular-training-pipeline)
  - [Time series pipeline parameters](#time-series-pipeline-autogluon-timeseries-training-pipeline)
- [What you get from a run](#what-you-get-from-a-run)
- [Example scenarios](#example-scenarios)
- [Prerequisites](#prerequisites)
- [Running AutoML](#running-automl)
- [Tutorial: Predict the Customer Churn](churn_prediction_tutorial.md)
- [Tutorial: Forecast with AutoML time series](time_series_forecasting_tutorial.md)
- [References](#references)

---

## About AutoML

### What AutoML gives you

Both pipelines automate training and evaluation end to end; you choose **tabular** or **time series** when you import and run the corresponding pipeline definition.

**Tabular** (`autogluon-tabular-training-pipeline`)

- **Data loading and splits** — CSV from S3 is sampled (up to 1GB), split into test vs train, then train is split into **selection** vs **extra** portions on a PVC workspace (see upstream README for defaults).
- **Training** — [AutoGluon](https://github.com/autogluon/autogluon) tabular ensembling (stacking and bagging) across many model families; top-N models are **refit** with extra training data for deployment-ready `TabularPredictor` artifacts.
- **Outputs** — HTML leaderboard; per-model `_FULL` artifacts; `automl_predictor_notebook.ipynb` for exploration.

**Time series** (`autogluon-timeseries-training-pipeline`)

- **Data loading and splits** — CSV or Parquet from S3; **per-series temporal** train/test split, then selection vs extra train rows per series on a PVC (see upstream README).
- **Training** — [AutoGluon TimeSeries](https://auto.gluon.ai/stable/tutorials/timeseries/forecasting-quickstart.html) models; optional **known covariates** for the forecast horizon; top-N **refit** with full train per series.
- **Outputs** — HTML leaderboard; `_FULL` time series predictor artifacts; time series predictor notebook from refit tasks.

**Common** — Run either pipeline from the AI Pipelines UI or Kubeflow Pipelines API; no custom training code is required. Model Registry and KServe are optional follow-on steps (serving shapes may differ by modality; see tutorials).

<a id="what-automl-supports"></a>

### What AutoML supports

AutoML supports **classification** (binary and multiclass) and **regression** for tabular data, and **time series forecasting** via a dedicated pipeline ([AutoGluon TimeSeries](https://auto.gluon.ai/stable/tutorials/timeseries/forecasting-quickstart.html) on a separate pipeline definition). Tabular runs use a label column and task type; time series runs use series id, timestamp, target, and forecast horizon (`prediction_length`).

| Area | Support |
|------|--------|
| **Data format** | CSV (tabular); CSV or Parquet for time series (columns for series id, timestamp, target) |
| **Data source** | S3-compatible object storage (via RHOAI Connections) |
| **Task types** | Tabular: classification (binary, multiclass), regression. Time series: forecasting with optional known covariates. |
| **Training** | AutoGluon (tabular ensembling; time series model selection and refit per pipeline README) |
| **What you get** | Trained model artifacts, HTML leaderboard, generated notebook(s) |
| **How you run it** | AI Pipelines UI, API (programmatic) |

You can register and serve the models AutoML produces using RHOAI Model Registry and KServe separately (tabular and time-series serving paths may differ; see tutorials).

**Not in scope:** Images, raw text as the primary modality, traditional hyperparameter tuning as the primary method, unsupervised learning.

### How it works under the hood

AutoML runs on Red Hat OpenShift AI, powered by AutoGluon and Kubeflow Pipelines. Data is read from S3 using credentials in a Kubernetes secret (typically from an RHOAI Connection). Model Registry and KServe are not part of the run. For full stage names, artifact paths, and defaults, see the README for each pipeline in [References](#references).

<a id="tabular-pipeline-flow"></a>

#### Tabular pipeline flow (`autogluon-tabular-training-pipeline`)

Stages from the [autogluon tabular training pipeline](https://github.com/red-hat-data-services/pipelines-components/tree/main/pipelines/training/automl/autogluon_tabular_training_pipeline): load CSV from S3 (sampled up to 1GB), split into test vs train, then split train into **selection** vs **extra** on a PVC workspace; run model selection on the selection split; **refit** each top-N model with `refit_full` using extra train data; emit leaderboard HTML and `_FULL` tabular model artifacts.

```mermaid
flowchart LR
    Start([Pipeline Start]) --> DataIngestion["Data Ingestion<br/>Load CSV from S3"]
    DataIngestion --> Preprocess["Preprocessing<br/>Split train / test"]
    Preprocess --> Training["AutoGluon Training<br/>Train & compare models"]
    Training --> SelectTopN["Model Selection<br/>Rank & select top-N"]
    SelectTopN --> Refit["Refit on Full Data<br/>Production-ready predictors"]
    Refit --> Artifacts["Artifacts Storage<br/>Leaderboard, models, notebook"]
    Artifacts --> End([Pipeline Complete])
    style Start fill:#2d8659,color:#fff,stroke-width:2px
    style End fill:#2d8659,color:#fff,stroke-width:2px
    style DataIngestion fill:#4a90d9,color:#fff,stroke-width:2px
    style Preprocess fill:#4a90d9,color:#fff,stroke-width:2px
    style Training fill:#4a90d9,color:#fff,stroke-width:2px
    style SelectTopN fill:#4a90d9,color:#fff,stroke-width:2px
    style Refit fill:#4a90d9,color:#fff,stroke-width:2px
    style Artifacts fill:#4a90d9,color:#fff,stroke-width:2px
```

<a id="time-series-pipeline-flow"></a>

#### Time series pipeline flow (`autogluon-timeseries-training-pipeline`)

Stages from the [autogluon time series training pipeline](https://github.com/red-hat-data-services/pipelines-components/tree/main/pipelines/training/automl/autogluon_timeseries_training_pipeline): load CSV or Parquet from S3; **per-series temporal** split (train vs holdout test), then split each series’ train rows into **selection** vs **extra** on a PVC; run AutoGluon TimeSeries **model selection**; **refit** each top-N model on the full train portion per series; emit leaderboard HTML and `_FULL` time series predictor artifacts (and notebooks).

```mermaid
flowchart LR
    Start([Pipeline Start]) --> TSLoad["Time series load<br/>CSV / Parquet from S3"]
    TSLoad --> TSSplit["Per-series temporal<br/>train / test split"]
    TSSplit --> TSSelect["TimeSeries model<br/>selection & top-N"]
    TSSelect --> TSRefit["Refit full train<br/>per series"]
    TSRefit --> TSArtifacts["Artifacts<br/>Leaderboard, predictors, notebook"]
    TSArtifacts --> End([Pipeline Complete])
    style Start fill:#2d8659,color:#fff,stroke-width:2px
    style End fill:#2d8659,color:#fff,stroke-width:2px
    style TSLoad fill:#4a90d9,color:#fff,stroke-width:2px
    style TSSplit fill:#4a90d9,color:#fff,stroke-width:2px
    style TSSelect fill:#4a90d9,color:#fff,stroke-width:2px
    style TSRefit fill:#4a90d9,color:#fff,stroke-width:2px
    style TSArtifacts fill:#4a90d9,color:#fff,stroke-width:2px
```

---

## What you need to provide

Provide S3 credentials (via a Kubernetes secret / RHOAI Connection), bucket, object key, and columns that match the pipeline you run. Parameter names match the compiled Kubeflow pipelines in [pipelines-components](https://github.com/red-hat-data-services/pipelines-components) (see each pipeline’s README).

<a id="tabular-pipeline-autogluon-tabular-training-pipeline"></a>

### Tabular pipeline (`autogluon-tabular-training-pipeline`)

| Parameter | Description |
|-----------|-------------|
| `train_data_secret_name` | Kubernetes secret name for S3 credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_ENDPOINT`, `AWS_DEFAULT_REGION`), typically from an RHOAI Connection. |
| `train_data_bucket_name` | Bucket containing the training CSV. |
| `train_data_file_key` | Object key of the CSV (features and label column). |
| `label_column` | Target column name in the CSV. |
| `task_type` | `binary`, `multiclass`, or `regression`. |

### Optional (tabular)

| Parameter | Default | Description |
|-----------|--------|-------------|
| `top_n` | `3` | How many top models to select for refit and leaderboard (positive integer). |

<a id="time-series-pipeline-autogluon-timeseries-training-pipeline"></a>

### Time series pipeline (`autogluon-timeseries-training-pipeline`)

Separate pipeline definition. Typical parameters:

| Parameter | Description |
|-----------|-------------|
| `train_data_secret_name` | Same S3 secret pattern as tabular. |
| `train_data_bucket_name` | Bucket containing the time series file. |
| `train_data_file_key` | Object key of the CSV or Parquet file. |
| `target` | Column to forecast (numeric). |
| `id_column` | Series identifier (mapped to `item_id` in the pipeline). |
| `timestamp_column` | Timestamp column (mapped to `timestamp`). |
| `prediction_length` | Forecast horizon (steps); integer ≥ 1 (default `1` in the pipeline API). |

### Optional (time series)

| Parameter | Default | Description |
|-----------|--------|-------------|
| `known_covariates_names` | `None` | Optional list of column names known for the forecast horizon (e.g. promotions). |
| `top_n` | `3` | Top models for refit and leaderboard. |

## What you get from a run

When a run completes, you get (for **tabular** or **time series**, depending on which pipeline you executed):

- **Leaderboard** — HTML ranking of refitted models. Tabular tasks use classification metrics (e.g. accuracy, ROC-AUC) or regression metrics (e.g. R²); time series models use the evaluation metric from the selection stage (see upstream README).
- **Trained models** — One `_FULL` artifact per top-N model: **tabular** `TabularPredictor` bundles; **time series** `TimeSeriesPredictor` bundles—ready to load or deploy.
- **Notebooks** — **Tabular** refit outputs include `automl_predictor_notebook.ipynb` under each model path; **time series** refit outputs include a time series predictor notebook (exact paths in each pipeline README under [pipelines-components](https://github.com/red-hat-data-services/pipelines-components)).

Artifacts are stored in the artifact store configured for your run (e.g., S3 via your Pipeline Server).

## Example scenarios

Use the **tabular** pipeline for row-oriented prediction (one row per entity, one label column). Use the **time series** pipeline when each series has a timestamp and a numeric target to forecast over `prediction_length` steps (optional known covariates). No training code is required for either path.

**Tabular:** A typical scenario is **predicting customer churn**: you have a table of customers (contract details, usage, demographics) and a column indicating who left. AutoML trains multiple models to predict that column, then gives you a leaderboard, so you can pick the best predictor and use it to flag at-risk customers or drive retention.

| Scenario | Your data | You predict | Outcome |
|----------|-----------|--------------|---------|
| **Customer churn** | Customer attributes, tenure, charges | Will the customer churn? (Yes/No) | Leaderboard + best model; use it to target retention. |
| **Fraud or risk** | Transaction or account features | Is it fraudulent / high risk? | Ranked models; deploy the best for real-time scoring. |
| **Regression** | Property or product features | Price, demand, or other numeric target | Best regression model and metrics (e.g. R²). |
| **Demand or capacity forecasting** | Time-indexed usage or demand (e.g. electricity by industry, or metrics per SKU/region: `item_id`, `timestamp`, `target`) | Future values over a horizon (`prediction_length`) | Leaderboard of time series models; predictor notebook; see [Tutorial: Forecast with AutoML time series](time_series_forecasting_tutorial.md). |

To try **tabular** AutoML yourself, follow the [Tutorial: Predict the Customer Churn](#tutorial-predict-the-customer-churn) with the Telco Customer Churn dataset. For **time series**, follow [Tutorial: Forecast with AutoML time series](time_series_forecasting_tutorial.md) using **`electricity_industry_a_forecasting.csv`** (derived from [IBM watsonx-ai-samples `cloud/data/electricity`](https://github.com/IBM/watsonx-ai-samples/tree/master/cloud/data/electricity)) under `data/timeseries/input_data/`, and the pipeline on branch [`main`](https://github.com/red-hat-data-services/pipelines-components/tree/main) in [pipelines-components](https://github.com/red-hat-data-services/pipelines-components).

---

## Prerequisites

- Red Hat OpenShift AI (RHOAI) installed and accessible, with Kubeflow Pipelines available (see [References](#references) for version).
- **Project** in RHOAI and **Pipeline Server** configured with object storage for runs and artifacts.
- **S3 connection** (RHOAI Connections) for training data so AutoML can read your file (**CSV** for tabular; **CSV or Parquet** for time series, per pipeline).

## Running AutoML

Create a pipeline run for the **tabular** or **time series** pipeline definition you imported (compile `pipeline.py` in each folder of [pipelines-components](https://github.com/red-hat-data-services/pipelines-components) to produce YAML, then register it in OpenShift AI). Pass the parameters listed under [What you need to provide](#what-you-need-to-provide) for that definition. Then use the Kubeflow Pipelines API or RHOAI Pipelines UI to submit the run.

When the run finishes, open the run’s artifacts to get the leaderboard, trained models, and notebook. From there, you can pick a model and, if needed, register it in Model Registry and/or deploy it with KServe (see [Deploying models on the single-model serving platform](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_cloud_service/1/html/deploying_models/deploying_models_on_the_single_model_serving_platform)).

---

## Tutorial: Predict the Customer Churn

**Scenario:** You have (or download) the **Telco Customer Churn** dataset: one row per customer, with features like contract type, tenure, charges, and a **Churn** column (Yes/No). The goal is to train a model that predicts **Churn**, so you can identify at-risk customers and use the best model from the leaderboard for retention or deployment.

**Step-by-step guide:** The full tutorial walks you through creating a project, S3 connections for results and training data, a workbench with connections attached, adding the AutoML pipeline and dataset, running AutoML with the right settings, viewing the leaderboard, and optionally registering and deploying the best model. Follow the tutorial here: **[Churn prediction tutorial](churn_prediction_tutorial.md)**.

<a id="tutorial-forecast-with-automl-time-series"></a>

## Tutorial: Forecast with AutoML time series

**Scenario:** You forecast **industrial electricity demand** using public sample data from [IBM watsonx-ai-samples](https://github.com/IBM/watsonx-ai-samples/tree/master/cloud/data) (prepared as `item_id`, `timestamp`, `target` in S3) and want **AutoGluon TimeSeries** models trained and compared on Red Hat OpenShift AI via the **autogluon-timeseries-training-pipeline** from [pipelines-components](https://github.com/red-hat-data-services/pipelines-components/tree/main) (branch **`main`**).

**Step-by-step guide:** The tutorial covers project setup, S3 and Pipeline Server configuration, uploading the electricity CSV, compiling and importing the pipeline YAML, running with parameters such as `prediction_length` (and optional `known_covariates_names` if you switch to the multi-series sample), and viewing the leaderboard and time series notebook artifacts. Follow it here: **[Time series forecasting tutorial](time_series_forecasting_tutorial.md)**.

## References

- [pipelines-components](https://github.com/red-hat-data-services/pipelines-components) — Kubeflow pipeline and component sources (branch **`main`**); AutoML pipeline READMEs list **Kubeflow Pipelines >= 2.15.2** and **Kubernetes >= 1.28**
- [AutoGluon tabular training pipeline](https://github.com/red-hat-data-services/pipelines-components/tree/main/pipelines/training/automl/autogluon_tabular_training_pipeline) — `autogluon-tabular-training-pipeline`; parameters, PVC workspace, splits, artifacts (**alpha** per upstream README)
- [AutoGluon time series training pipeline](https://github.com/red-hat-data-services/pipelines-components/tree/main/pipelines/training/automl/autogluon_timeseries_training_pipeline) — `autogluon-timeseries-training-pipeline`; temporal splits, `prediction_length`, optional `known_covariates_names` (**alpha** per upstream README)
- [AutoGluon](https://github.com/autogluon/autogluon) — AutoML engine used for training and ensembling
- [KServe (LukaszCmielowski/kserve)](https://github.com/LukaszCmielowski/kserve) — Dockerfile (`python/autogluon.Dockerfile`) and layout used to build the AutoGluon serving image for model deployment
- [Deploying models on the model serving platform](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.2/html/deploying_models/deploying_models#deploying-models-on-the-model-serving-platform_rhoai-user) — register and serve models after AutoML
- [KServe V1 Protocol](https://kserve.github.io/website/docs/concepts/architecture/data-plane/v1-protocol) — request/response format and endpoints for `/v1/models/{model_name}:predict`
