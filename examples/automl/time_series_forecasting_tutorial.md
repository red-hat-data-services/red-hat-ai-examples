
# 📚 Tutorial: Forecast with AutoML time series

**Scenario:** You want to **forecast electricity usage** for an industrial segment over time — a typical operations and capacity-planning use case. You will use **open, public sample data** from [IBM watsonx-ai-samples](https://github.com/IBM/watsonx-ai-samples/tree/master/cloud/data), run the **AutoGluon time series training pipeline** on Red Hat OpenShift AI, compare models on a leaderboard, and use the generated **time series predictor notebook** to explore forecasts.

Each row of the training file must include a **series identifier** (`item_id`), a **timestamp**, and a numeric **target** to forecast. Optional columns can be **known covariates** (known in advance for the forecast horizon). This tutorial’s primary dataset is a **single series** (one `item_id` for all rows).

This walkthrough covers: creating a project, S3 connections for results and training data, configuring the Pipeline Server, attaching connections to a workbench, uploading your time series file, adding the pipeline definition, running it with time-series parameters, and viewing leaderboard and notebook artifacts. **Time series** pipeline source and parameters: [pipelines-components](https://github.com/red-hat-data-services/pipelines-components/tree/autox) (branch **`autox`**).

## Table of contents

- [📈 Use case and dataset](#use-case-and-dataset)
- [🏗️ Create a new project](#create-a-new-project)
- [💾 Create the S3 connections](#create-the-s3-connections)
- [⚙️ Configure the Pipeline Server](#configure-the-pipeline-server)
- [🔗 Create workbench with connections attached](#create-workbench-with-connections-attached)
- [⬆️ Upload the time series dataset to S3](#upload-the-time-series-dataset-to-s3)
- [📋 Add the time series AutoML pipeline as a Pipeline Definition](#add-the-time-series-automl-pipeline-as-a-pipeline-definition)
- [▶️ Run the pipeline with required inputs](#run-the-pipeline-with-required-inputs)
- [📊 View the leaderboard](#view-the-leaderboard)
- [📓 Time series predictor notebook](#time-series-predictor-notebook)
- [📚 Optional: Model Registry and deployment](#optional-model-registry-and-deployment)

<a id="use-case-and-dataset"></a>

## 📈 Use case and dataset

- **Use case:** **Industrial electricity demand forecasting** — predict future **industry A** usage from historical daily (or regular) readings, supporting planning and analytics workflows.
- **Public data:** [IBM watsonx-ai-samples](https://github.com/IBM/watsonx-ai-samples/tree/master/cloud/data) hosts sample datasets for watsonx tutorials. Under [`cloud/data/electricity/`](https://github.com/IBM/watsonx-ai-samples/tree/master/cloud/data/electricity), [`electricity_usage.csv`](https://github.com/IBM/watsonx-ai-samples/blob/master/cloud/data/electricity/electricity_usage.csv) provides **`date`** and **`industry_a_usage`**.
- **Pipeline shape:** The [autogluon timeseries training pipeline](https://github.com/red-hat-data-services/pipelines-components/tree/autox/pipelines/training/automl/autogluon_timeseries_training_pipeline) expects **`id_column`**, **`timestamp_column`**, and **`target`** (and optional known covariates). The raw IBM file is **two columns only** (one implicit series).
- **File in this repo:** **[electricity_industry_a_forecasting.csv](data/timeseries/input_data/electricity_industry_a_forecasting.csv)** — preprocessed from the IBM file above: constant **`item_id`** = `industry_a`, **`timestamp`** (from `date`), **`target`** (from `industry_a_usage`). Upload this to S3 for the tutorial, or reproduce the same layout from the [raw CSV](https://raw.githubusercontent.com/IBM/watsonx-ai-samples/master/cloud/data/electricity/electricity_usage.csv) by adding an `item_id` column and renaming columns to match your `id_column` / `timestamp_column` / `target` parameters.

See also [data/timeseries/README.md](data/timeseries/README.md) for provenance and an optional **multi-series** sample ([timeseries_sales.csv](data/timeseries/input_data/timeseries_sales.csv)) with a `promo` covariate.

<a id="create-a-new-project"></a>

## 🏗️ Create a new project

| Step | Action |
|------|--------|
| **①** | Log in to Red Hat OpenShift AI. |
| **②** | From the OpenShift AI dashboard, go to **Projects** (or **Data science projects**) and create a new project (for example, `automl-timeseries-forecast`). |

<a id="create-the-s3-connections"></a>

## 💾 Create the S3 connections

Create two S3-compatible connections: one for pipeline **results** (artifacts, leaderboard) and one for **training data**. Use the results connection when you [configure the Pipeline Server](#configure-the-pipeline-server).

**Results storage connection**

| Step | Action |
|------|--------|
| **①** | In your project, open **Connections** and click **Create connection**. |
| **②** | Select **S3 compatible object storage - v1**. |
| **③** | Enter a **Connection name** (for example, `automl-ts-results-s3`). |
| **④** | Fill in **Endpoint**, **Bucket**, **Region**, **Access key**, **Secret key**. |
| **⑤** | Click **Create**. |

**Training data connection**

| Step | Action |
|------|--------|
| **①** | Create another connection with a distinct name (for example, `automl-ts-data-s3`) for the bucket that holds your CSV (or Parquet) file. |
| **②** | Note the **Connection name**; you will use it as `train_data_secret_name` in the pipeline run. |

For connection details, see [Using connections](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.2/html/working_on_projects/using-connections_projects) in the Red Hat OpenShift AI documentation.

<a id="configure-the-pipeline-server"></a>

## ⚙️ Configure the Pipeline Server

| Step | Action |
|------|--------|
| **①** | Open your project → **Pipelines** → **Configure pipeline server**. |
| **②** | In **Object storage connection**, use the same credentials as your **results** S3 connection (or select that connection if the UI allows). |
| **③** | In **Database**, choose **Default database on the cluster** for development, or **External MySQL** for production-style workloads. |
| **④** | Create the Pipeline Server and wait until it is ready. |

See [Working with data science pipelines](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.2/html/working_with_ai_pipelines/working_with_ai_pipelines) for details.

<a id="create-workbench-with-connections-attached"></a>

## 🔗 Create workbench with connections attached

| Step | Action |
|------|--------|
| **①** | Create a **Workbench** in the project. |
| **②** | **Attach** both the results and training data connections so you can download artifacts or notebooks later without restarting the workbench. |

<a id="upload-the-time-series-dataset-to-s3"></a>

## ⬆️ Upload the time series dataset to S3

| Step | Action |
|------|--------|
| **①** | Use the **electricity** tutorial file: [electricity_industry_a_forecasting.csv](data/timeseries/input_data/electricity_industry_a_forecasting.csv) (`item_id`, `timestamp`, `target`), derived from [IBM watsonx-ai-samples electricity data](https://github.com/IBM/watsonx-ai-samples/tree/master/cloud/data/electricity) as described in [Use case and dataset](#use-case-and-dataset). |
| **②** | Upload the CSV to the S3 bucket for your **training data** connection. Note the **object key** (e.g. `timeseries/input_data/electricity_industry_a_forecasting.csv`). |
| **③** | You will pass **bucket name**, **object key**, and column names into the pipeline run in the next section. |

**Optional — multi-series sample:** [timeseries_sales.csv](data/timeseries/input_data/timeseries_sales.csv) includes **`promo`** as a candidate **known covariate**; map `known_covariates_names` to `["promo"]` if you use that file (see [data/timeseries/README.md](data/timeseries/README.md)).

**Your own data:** CSV or Parquet must include columns for series id, timestamp, and target; map them with `id_column`, `timestamp_column`, and `target`. Optional **known covariates** go in `known_covariates_names`. See the pipeline [README](https://github.com/red-hat-data-services/pipelines-components/blob/autox/pipelines/training/automl/autogluon_timeseries_training_pipeline/README.md) on branch `autox`.

<a id="add-the-time-series-automl-pipeline-as-a-pipeline-definition"></a>

## 📋 Add the time series AutoML pipeline as a Pipeline Definition

| Step | Action |
|------|--------|
| **①** | Obtain a **compiled** pipeline YAML for `autogluon-timeseries-training-pipeline`. Source: [pipelines-components](https://github.com/red-hat-data-services/pipelines-components/tree/autox/pipelines/training/automl/autogluon_timeseries_training_pipeline) on branch **`autox`**. From a Python environment with the repository’s dependencies (see that repo’s [README](https://github.com/red-hat-data-services/pipelines-components/blob/autox/README.md)), run `python pipeline.py` in that folder to generate `pipeline.yaml` next to `pipeline.py` (see the `__main__` block in `pipeline.py`). |
| **②** | In Red Hat OpenShift AI, open **Pipelines** for your project. |
| **③** | Upload the YAML as a new **Pipeline Definition**, following [Managing AI pipelines](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.2/html/working_with_ai_pipelines/managing-ai-pipelines_ai-pipelines). |

Pipeline stages (summary): load data from S3 → **per-series temporal splits** → **model selection** on a selection split → **parallel refit** of top-N models → **leaderboard** HTML. Details: [autogluon_timeseries_training_pipeline README](https://github.com/red-hat-data-services/pipelines-components/blob/autox/pipelines/training/automl/autogluon_timeseries_training_pipeline/README.md).

<a id="run-the-pipeline-with-required-inputs"></a>

## ▶️ Run the pipeline with required inputs

| Step | Action |
|------|--------|
| **①** | From **Pipelines**, create a run for the time series pipeline definition. |
| **②** | Set parameters to match your data. See the table below for the **electricity** tutorial file ([electricity_industry_a_forecasting.csv](data/timeseries/input_data/electricity_industry_a_forecasting.csv)). |
| **③** | Ensure the **Pipeline Server** uses your **results** S3 connection so artifacts are stored correctly. |
| **④** | Start the run and wait until it completes. |

**Pipeline parameters (example for `electricity_industry_a_forecasting.csv`):**

| Parameter | Example |
|-----------|---------|
| `train_data_secret_name` | Your **training data** connection name |
| `train_data_bucket_name` | Bucket from that connection |
| `train_data_file_key` | Object key (e.g. `timeseries/input_data/electricity_industry_a_forecasting.csv`) |
| `target` | `target` |
| `id_column` | `item_id` |
| `timestamp_column` | `timestamp` |
| `known_covariates_names` | Omit, or empty — this file has no covariate columns |
| `prediction_length` | `7` or `14` (forecast horizon; integer ≥ 1) |
| `top_n` | `3` |

**Example: multi-series data with `known_covariates_names`**

Use [timeseries_sales.csv](data/timeseries/input_data/timeseries_sales.csv) if you want a run that includes a **known covariate** (`promo`). Upload it under an object key such as `timeseries/input_data/timeseries_sales.csv`, then set:

| Parameter | Example |
|-----------|---------|
| `train_data_secret_name` | Your **training data** connection name |
| `train_data_bucket_name` | Bucket from that connection |
| `train_data_file_key` | `timeseries/input_data/timeseries_sales.csv` |
| `target` | `target` |
| `id_column` | `item_id` |
| `timestamp_column` | `timestamp` |
| `known_covariates_names` | `["promo"]` |
| `prediction_length` | `6` (or another horizon; you must be able to provide known covariates for all forecast steps) |
| `top_n` | `3` |

In the Pipelines UI, list parameters are often entered as a **JSON array** (e.g. the text `["promo"]`). From Python, match the upstream [pipeline README](https://github.com/red-hat-data-services/pipelines-components/blob/main/pipelines/training/automl/autogluon_timeseries_training_pipeline/README.md) example: `known_covariates_names=["promo"]`.

**Prediction when covariates were used:** If the model was trained with `known_covariates_names`, each forecast needs **future values** of those columns for every `item_id` over `prediction_length`. Provide them in the structure AutoGluon expects—usually via the refit artifact **time series notebook** or `TimeSeriesPredictor.predict` with a `TimeSeriesDataFrame` that includes those covariate columns for future timestamps. See [AutoGluon TimeSeries — forecasting quickstart](https://auto.gluon.ai/stable/tutorials/timeseries/forecasting-quickstart.html).

The pipeline uses a **12Gi** workspace PVC by default in the upstream `pipeline.py`; ensure your cluster can provision that volume for the run.

<a id="view-the-leaderboard"></a>

## 📊 View the leaderboard

| Step | Action |
|------|--------|
| **①** | Open the completed run → **Artifacts**. |
| **②** | Open the **leaderboard** HTML (from the leaderboard evaluation step). |
| **③** | Compare top models by the evaluation metric reported by the selection stage. |

<a id="time-series-predictor-notebook"></a>

## 📓 Time series predictor notebook

Each refitted top model can emit a **time series notebook** (template: `timeseries_notebook.ipynb` in the [autogluon_timeseries_models_full_refit](https://github.com/red-hat-data-services/pipelines-components/tree/autox/components/training/automl/autogluon_timeseries_models_full_refit) component on branch `autox`). Download it from the run artifacts under the refit task output for the model you care about, upload it to your workbench, and run it against the predictor path stored with that artifact.

For layout and component behavior, see the component [README](https://github.com/red-hat-data-services/pipelines-components/blob/autox/components/training/automl/autogluon_timeseries_models_full_refit/README.md) on branch `autox`.

<a id="optional-model-registry-and-deployment"></a>

## 📚 Optional: Model Registry and deployment

The time series pipeline writes **model artifacts** (predictors, metrics, notebooks) to your pipeline artifact store; it does **not** register models automatically. To register a refitted time-series predictor in **Model Registry** or deploy with **KServe**, follow [Working with model registries](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.2/html/working_with_model_registries/working-with-model-registries_model-registry) and [Deploying models on the model serving platform](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.2/html/deploying_models/deploying_models#deploying-models-on-the-model-serving-platform_rhoai-user) in the Red Hat OpenShift AI documentation. Use the predictor paths and related files from your **`autogluon-timeseries-training-pipeline`** refit task outputs as the model source when registering or deploying.

**Serving runtime:** Use the **same AutoGluon KServe Serving Runtime** as for tabular AutoML (same container image and cluster setup). Build the image and create the Serving Runtime as in [Prepare the ServingRuntime for AutoGluon with KServe](churn_prediction_tutorial.md#prepare-the-servingruntime-for-autogluon-with-kserve) in the tabular churn tutorial, then pick that runtime when you **Deploy model**. The difference for time series is the **predictor type** and often the **inference request shape** (for example payloads or flows that match `TimeSeriesPredictor` rather than tabular AutoGluon). Prefer the refit task’s **time series notebook** and [AutoGluon TimeSeries](https://auto.gluon.ai/stable/tutorials/timeseries/forecasting-quickstart.html) to validate predictions end to end, including **known covariates** at prediction time when the model was trained with `known_covariates_names`.

---

## Pipeline reference

- **Branch:** [`autox`](https://github.com/red-hat-data-services/pipelines-components/tree/autox) — [pipelines-components](https://github.com/red-hat-data-services/pipelines-components)
- **Pipeline:** [autogluon_timeseries_training_pipeline](https://github.com/red-hat-data-services/pipelines-components/tree/autox/pipelines/training/automl/autogluon_timeseries_training_pipeline) (name: `autogluon-timeseries-training-pipeline`)
- **Stability:** alpha (see upstream README)
