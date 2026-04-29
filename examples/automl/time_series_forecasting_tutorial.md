# 📚 Tutorial: Forecast with AutoML time series

**Scenario:** You want to **forecast electricity usage** for an industrial segment over time — a typical operations and capacity-planning use case. You will use **open, public sample data** from [IBM watsonx-ai-samples](https://github.com/IBM/watsonx-ai-samples/tree/master/cloud/data), run the **AutoGluon time series training pipeline** on Red Hat OpenShift AI, compare models on a leaderboard, and use the generated **time series predictor notebook** to explore forecasts.

Each row of the training file must include a **series identifier** (`item_id`), a **timestamp**, and a numeric **target** to forecast. Optional columns can be **known covariates** (known in advance for the forecast horizon). This tutorial’s primary dataset is a **single series** (one `item_id` for all rows).

This walkthrough covers: creating a project, S3 connections for results and training data, configuring the Pipeline Server, creating a workbench with the **results** connection attached during setup (so you can reach pipeline artifacts without a restart), uploading your time series file, adding the pipeline definition, running it with time-series parameters, and viewing leaderboard and notebook artifacts. **Time series** pipeline source and parameters: [pipelines-components](https://github.com/red-hat-data-services/pipelines-components/tree/rhoai-3.4) (branch `rhoai-3.4`).

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
- [📚 Model Registry](#model-registry)
- [⚙️ Prepare the ServingRuntime for AutoGluon with KServe](#prepare-the-servingruntime-for-autogluon-with-kserve)
- [🚀 Model Deployment](#model-deployment)
- [🎯 Deployment Scoring](#deployment-scoring)


<a id="use-case-and-dataset"></a>

## 📈 Use case and dataset

- **Use case:** **Industrial electricity demand forecasting** — predict future **industry A** usage from historical daily (or regular) readings, supporting planning and analytics workflows.
- **Public data:** [IBM watsonx-ai-samples](https://github.com/IBM/watsonx-ai-samples/tree/master/cloud/data) hosts sample datasets for watsonx tutorials. Under [cloud/data/electricity/](https://github.com/IBM/watsonx-ai-samples/tree/master/cloud/data/electricity), [electricity_usage.csv](https://github.com/IBM/watsonx-ai-samples/blob/master/cloud/data/electricity/electricity_usage.csv) provides `date` and `industry_a_usage` columns.
- **Pipeline shape:** The [AutoGluon Time Series training pipeline](https://github.com/red-hat-data-services/pipelines-components/tree/rhoai-3.4/pipelines/training/automl/autogluon_timeseries_training_pipeline) expects `id_column`, `timestamp_column`, and `target` (and optional known covariates). The raw IBM file is **two columns only** (one implicit series).
- **File in this repo:** **[electricity_industry_a_forecasting.csv](data/timeseries/input_data/electricity_industry_a_forecasting.csv)** — preprocessed from the IBM file above: constant `item_id` = `industry_a`, `timestamp` (from `date`), `target` (from `industry_a_usage`). Upload this to S3 for the tutorial, or reproduce the same layout from the [raw CSV](https://raw.githubusercontent.com/IBM/watsonx-ai-samples/master/cloud/data/electricity/electricity_usage.csv) by adding an `item_id` column and renaming columns to match your `id_column` / `timestamp_column` / `target` parameters.

See also [data/timeseries/README.md](data/timeseries/README.md) for provenance and an optional **multi-series** sample ([timeseries_sales.csv](data/timeseries/input_data/timeseries_sales.csv)) with a `promo` covariate.

<a id="create-a-new-project"></a>

## 🏗️ Create a new project

    
| Step  | Action                                                                                                                    |
| ----- | ------------------------------------------------------------------------------------------------------------------------- |
| **①** | Log in to Red Hat OpenShift AI.                                                                                           |
| **②** | From the OpenShift AI dashboard, go to **Projects** and create a new project (for example, `automl-timeseries-forecast`). |



<a id="create-the-s3-connections"></a>

## 💾 Create the S3 connections

Create two S3-compatible connections: one for pipeline **results** (artifacts, leaderboard) and one for **training data**. Use the results connection when you [configure the Pipeline Server](#configure-the-pipeline-server).

**Results storage connection**


| Step  | Action                                                                        |
| ----- | ----------------------------------------------------------------------------- |
| **①** | In your project, open **Connections** and click **Create connection**.        |
| **②** | Select **S3 compatible object storage - v1**.                                 |
| **③** | Enter a **Connection name** (for example, `automl-ts-results-s3`).            |
| **④** | Fill in **Endpoint**, **Bucket**, **Region**, **Access key**, **Secret key**. |
| **⑤** | Click **Create**.                                                             |


**Training data connection**


| Step  | Action                                                                                                                     |
| ----- | -------------------------------------------------------------------------------------------------------------------------- |
| **①** | Create another connection with a distinct name (for example, `automl-ts-data-s3`) for the bucket that holds your CSV file. |
| **②** | Note the **Connection name**; you will use it as `train_data_secret_name` in the pipeline run.                             |


For connection details, see [Using connections](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.4/html/working_on_projects/using-connections_projects) in the Red Hat OpenShift AI documentation.

<a id="configure-the-pipeline-server"></a>

## ⚙️ Configure the Pipeline Server


| Step  | Action                                                                                                                                                     |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **①** | Open your project → **Pipelines** → **Configure pipeline server**.                                                                                         |
| **②** | In **Object storage connection**, use the same credentials as your **results** S3 connection (or select that connection if the UI allows).                 |
| **③** | In **Advanced Settings** → **Database**, choose **Default database on the cluster** for development, or **External MySQL** for production-style workloads. |
| **④** | Create the Pipeline Server and wait until it is ready.                                                                                                     |


See [Working with data science pipelines](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.4/html/working_with_ai_pipelines/index) for details.

## 🔗 Create workbench with connections attached


| Step  | Action                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **①** | In the project, go to **Workbenches** and create a **Workbench** (notebook environment). Choose an image and resource size as needed.                                                                                                                                                                                                                                                                                                               |
| **②** | During workbench setup, use **Attach existing connections** to attach the **results** S3 connection you created above, so the workbench can access the results bucket (e.g. to download the leaderboard or artifacts later) without a restart. Only the **results** connection can be attached during workbench creation; the **training data** connection is used by the pipeline via run parameters when reading data from S3, not attached here. |
| **③** | Save and launch the workbench. For full steps, see [Creating a project and workbench](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.4/html/getting_started_with_red_hat_openshift_ai_self-managed/creating-a-workbench-select-ide_get-started) in the Red Hat OpenShift AI documentation.                                                                                                                            |

<a id="upload-the-time-series-dataset-to-s3"></a>

## ⬆️ Upload the time series dataset to S3


| Step  | Action                                                                                                                                                                                                                                                                                                                                                                                     |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **①** | Use the **electricity** tutorial file: [electricity_industry_a_forecasting.csv](data/timeseries/input_data/electricity_industry_a_forecasting.csv) (`item_id`, `timestamp`, `target`), derived from [IBM watsonx-ai-samples electricity data](https://github.com/IBM/watsonx-ai-samples/tree/master/cloud/data/electricity) as described in [Use case and dataset](#use-case-and-dataset). |
| **②** | Upload the CSV to the S3 bucket for your **training data** connection. Note the **object key** (e.g. `timeseries/input_data/electricity_industry_a_forecasting.csv`).                                                                                                                                                                                                                      |
| **③** | You will pass **bucket name**, **object key**, and column names into the pipeline run in the next section.                                                                                                                                                                                                                                                                                 |


**Optional — multi-series sample:** [timeseries_sales.csv](data/timeseries/input_data/timeseries_sales.csv) includes `promo` as a candidate **known covariate**; map `known_covariates_names` to `["promo"]` if you use that file (see [data/timeseries/README.md](data/timeseries/README.md)).

**Your own data:** CSV  must include columns for series id, timestamp, and target; map them with `id_column`, `timestamp_column`, and `target`. Optional **known covariates** go in `known_covariates_names`. See the pipeline [README](https://github.com/red-hat-data-services/pipelines-components/blob/rhoai-3.4/pipelines/training/automl/autogluon_timeseries_training_pipeline/README.md) file.


<a id="add-the-time-series-automl-pipeline-as-a-pipeline-definition"></a>

## 📋 Add the time series AutoML pipeline as a Pipeline Definition


| Step  | Action                                                                                                                                                                                                                                                                     |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **①** | Obtain a **compiled** pipeline YAML for `autogluon-timeseries-training-pipeline` from [pipelines-components](https://github.com/red-hat-data-services/pipelines-components/blob/rhoai-3.4/pipelines/training/automl/autogluon_timeseries_training_pipeline/pipeline.yaml). |
| **②** | In Red Hat OpenShift AI, open **Develop & train**, then **Pipelines** for your project.                                                                                                                                                                                    |
| **③** | Upload the YAML as a new **Pipeline Definition**, following [Managing AI pipelines](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.4/html/working_with_ai_pipelines/managing-ai-pipelines_ai-pipelines).                                     |

<a id="run-the-pipeline-with-required-inputs"></a>

## ▶️ Run the pipeline with required inputs


| Step  | Action                                                                                                                                                                                                      |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **①** | From **Develop & train** -> **Pipelines**, create a run for the time series pipeline definition.                                                                                                            |
| **②** | Set parameters to match your data. See the table below for the **electricity** tutorial file ([electricity_industry_a_forecasting.csv](data/timeseries/input_data/electricity_industry_a_forecasting.csv)). |
| **③** | Ensure the **Pipeline Server** uses your **results** S3 connection so artifacts are stored correctly.                                                                                                       |
| **④** | Start the run and wait until it completes.                                                                                                                                                                  |


**Pipeline parameters (example for `electricity_industry_a_forecasting.csv`):**


| Parameter                | Example                                                                          |
| ------------------------ | -------------------------------------------------------------------------------- |
| `train_data_secret_name` | Your **training data** connection name                                           |
| `train_data_bucket_name` | Bucket from that connection                                                      |
| `train_data_file_key`    | Object key (e.g. `timeseries/input_data/electricity_industry_a_forecasting.csv`) |
| `target`                 | `target`                                                                         |
| `id_column`              | `item_id`                                                                        |
| `timestamp_column`       | `timestamp`                                                                      |
| `known_covariates_names` | Omit, or empty — this file has no covariate columns                              |
| `prediction_length`      | `7` or `14` (forecast horizon; integer ≥ 1)                                      |
| `top_n`                  | `3`                                                                              |


**Example: multi-series data with `known_covariates_names`**

Use [timeseries_sales.csv](data/timeseries/input_data/timeseries_sales.csv) if you want a run that includes a **known covariate** (`promo`). Upload it under an object key such as `timeseries/input_data/timeseries_sales.csv`, then set:


| Parameter                | Example                                                                                       |
| ------------------------ | --------------------------------------------------------------------------------------------- |
| `train_data_secret_name` | Your **training data** connection name                                                        |
| `train_data_bucket_name` | Bucket from that connection                                                                   |
| `train_data_file_key`    | `timeseries/input_data/timeseries_sales.csv`                                                  |
| `target`                 | `target`                                                                                      |
| `id_column`              | `item_id`                                                                                     |
| `timestamp_column`       | `timestamp`                                                                                   |
| `known_covariates_names` | `["promo"]`                                                                                   |
| `prediction_length`      | `6` (or another horizon; you must be able to provide known covariates for all forecast steps) |
| `top_n`                  | `3`                                                                                           |


In the Pipelines UI, list parameters are often entered as a **JSON array** (e.g. the text `["promo"]`). From Python, match the upstream [pipeline README](https://github.com/red-hat-data-services/pipelines-components/blob/rhoai-3.4/pipelines/training/automl/autogluon_timeseries_training_pipeline/README.md) example: `known_covariates_names=["promo"]`.

**Prediction when covariates were used:** If the model was trained with `known_covariates_names`, each forecast needs **future values** of those columns for every `item_id` over `prediction_length`. Provide them in the structure AutoGluon expects—usually via the refit artifact **time series notebook** or `TimeSeriesPredictor.predict` with a `TimeSeriesDataFrame` that includes those covariate columns for future timestamps. See [AutoGluon TimeSeries — forecasting quickstart](https://auto.gluon.ai/stable/tutorials/timeseries/forecasting-quickstart.html).

**The pipeline uses a 12Gi workspace PVC by default in the upstream** `pipeline.py`**; ensure your cluster can provision that volume for the run.**


<a id="view-the-leaderboard"></a>

## 📊 View the leaderboard


| Step  | Action                                                                                                                                                                                |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **①** | Open the **completed run** (for example **Develop & train** > **Pipelines** > **Runs**, then select your run).                                                                        |
| **②** | In the **pipeline run graph**, click the last node named `**html_artifact`**.                                                                                                         |
| **③** | In the node panel, preview the leaderboard by clicking **Artifact URI** (opens the HTML leaderboard so you can compare top models by the evaluation metric from the selection stage). |

<a id="time-series-predictor-notebook"></a>

## 📓 Time series predictor notebook

Each refitted top model can emit a **time series predictor notebook** (e.g. `automl_predictor_notebook.ipynb`) that loads and uses the selected AutoGluon `TimeSeriesPredictor` for forecasts, evaluation, and exploration. You can download this notebook from the run artifacts, upload it to your workbench, run it, and customize it as needed.

The notebook is saved under `model_artifact/<model_name_FULL>/notebooks`, where the refit output root is a path like `autogluon-timeseries-training-pipeline/<run_id>/autogluon-timeseries-models-full-refit/<task_id>/model_artifact/` (one such path per refitted model). For example: `...<run_id>/autogluon-timeseries-models-full-refit/<task_id>/model_artifact/<model_name_FULL>/notebooks/automl_predictor_notebook.ipynb`.

**Alternatively:** Open the leaderboard HTML as described in [View the leaderboard](#view-the-leaderboard). The **Notebook** column in the leaderboard table lists the URI (or artifact path) for each model’s `automl_predictor_notebook.ipynb`, so you can copy that location without walking the refit task outputs in the run UI.

> [!tip]  
> `run_id` can be found in **Develop & train** > **Pipelines** > **Runs** > **your_name_run** > **Details Tab**


| Step  | Action                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **①** | Once the AutoML run completes, check the [leaderboard](#view-the-leaderboard) to find the S3 storage path for each model's generated notebook in column "Notebook".                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| **②** | **Download** the notebook to your local machine from the artifact store (S3) if you have access (e.g. via the workbench S3 connection from **[Create workbench with connections attached](#create-workbench-with-connections-attached)**). The notebook is under a path like `...<run_id>/autogluon-timeseries-models-full-refit/<task_id>/model_artifact/<model_name_FULL>/notebooks/automl_predictor_notebook.ipynb` (see the [autogluon_timeseries_models_full_refit component](https://github.com/red-hat-data-services/pipelines-components/tree/rhoai-3.4/components/training/automl/autogluon_timeseries_models_full_refit) for the exact layout). |
| **③** | Open your **workbench** (the notebook environment you created in **[Create workbench with connections attached](#create-workbench-with-connections-attached)**). In JupyterLab, click the **Upload** button (upload icon) in the File Browser sidebar, select the downloaded `.ipynb` file, and upload it. The notebook appears in your workbench file tree.                                                                                                                                                                                                                                                                                              |
| **④** | Open the notebook and **run** it cell by cell. Ensure the workbench has access to the same S3 bucket (or the path configured in the notebook) so it can load the `TimeSeriesPredictor` and any data the notebook expects. If you attached the **results** connection when creating the workbench (see **[Create workbench with connections attached](#create-workbench-with-connections-attached)**), that bucket is already available.                                                                                                                                                                                                                   |
| **⑤** | **Customize** if required: edit the model path or artifact location to point to a specific refitted model (e.g. `WeightedEnsemble_FULL`), add cells for extra visualizations or metrics, change sample data, or adapt the notebook for your own workflows. Save the notebook in the workbench when done.                                                                                                                                                                                                                                                                                                                                                  |


For creating and importing notebooks in the workbench, see [Creating and importing notebooks](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.4/html/working_in_your_data_science_ide/working_in_jupyterlab#creating-and-importing-jupyter-notebooks_ide) in the Red Hat OpenShift AI documentation.

<a id="model-registry"></a>

## 📚 Model Registry

The [autogluon-timeseries-training-pipeline](https://github.com/red-hat-data-services/pipelines-components/blob/rhoai-3.4/pipelines/training/automl/autogluon_timeseries_training_pipeline/pipeline.py) does **model selection** and then **full refit** for top models. The pipeline writes artifacts to S3 but does **not** register models automatically. To version and deploy a chosen model, register it manually in **Red Hat OpenShift AI Model Registry**.

The key difference vs tabular is the predictor artifact path. For time series, use a predictor path like:
`...<run_id>/autogluon-timeseries-models-full-refit/<task_id>/model_artifact/<model_name_FULL>/predictor`

You can get this path directly from the leaderboard HTML: open [View the leaderboard](#view-the-leaderboard), then copy the value from the **Predictor** column for the model you want to register.


| Step  | Action                                                                                                                                                                                                                                                                                                                            |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **①** | From the OpenShift AI dashboard, go to **AI Hub** -> **Models** -> **Registry** and select your model registry.                                                                                                                                                                                                                   |
| **②** | Click **Register model**. In the **Register model** dialog, under **Model location**, select **Object storage** (S3-compatible).                                                                                                                                                                                                  |
| **③** | Enter **Model name** and optional **Description**. Enter **Version name** and set **Source model format** as used in your environment for AutoGluon models.                                                                                                                                                                       |
| **④** | Enter **Endpoint**, **Bucket**, **Region**, and **Path** to one refitted time-series predictor root (for example, `.../<model_name_FULL>/predictor`). You can use **Autofill from connection** to fill object-storage credentials from your results connection. You can paste the path from the leaderboard **Predictor** column. |
| **⑤** | Click **Register**. The model appears in Model Registry and is ready for versioning, promotion, and deployment.                                                                                                                                                                                                                   |


For more on registry setup and prerequisites, see [Working with model registries](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.4/html/working_with_model_registries/working-with-model-registries_model-registry).

<a id="prepare-the-servingruntime-for-autogluon-with-kserve"></a>

## ⚙️ Prepare the ServingRuntime for AutoGluon with KServe

This part is the same as tabular AutoML. Reuse the same runtime and follow the same steps:
[Prepare the ServingRuntime for AutoGluon with KServe](churn_prediction_tutorial.md#prepare-the-servingruntime-for-autogluon-with-kserve).

<a id="model-deployment"></a>

## 🚀 Model Deployment

After the AutoGluon ServingRuntime is created (see [Prepare the ServingRuntime for AutoGluon with KServe](#prepare-the-servingruntime-for-autogluon-with-kserve)), deploy from the model you registered in [Model Registry](#model-registry):


| Step  | Action                                                                                                                                                           |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **①** | From the OpenShift AI dashboard, go to **AI Hub** → **Models** → **Registry** and open the model registry where you registered the model.                        |
| **②** | Select the model you registered in [Model Registry](#model-registry). Click **Actions** → **Deploy**, then follow the dialog until you reach **Deploy a model**. |
| **③** | In **Deploy a model**, for **Model type**, choose **Predictive model**. For **Model framework**, choose **autogluon - 1**.                                       |
| **④** | Under **Deployment resource**, select **AutoGluon ServingRuntime for KServe**.                                                                                   |
| **⑤** | Set the deployment name and review **Advanced settings** for options such as token authentication or an external route. |
| **⑥** | Read the **warning** below: if it applies, add the runtime environment variables under **Advanced settings** before deploying. Then click **Deploy model**. |


> [!warning]
> **Custom id or timestamp column names**  
> Inference defaults to JSON keys **`item_id`** and **`timestamp`**. If your training CSV used different columns like: **`id_column`** or **`timestamp_column`**, you **must** set **`AUTOGLUON_TS_ID_COLUMN`** and **`AUTOGLUON_TS_TIMESTAMP_COLUMN`** before deploy (**Advanced settings** → **Configuration parameters** → **Add custom runtime environment variables** → **+ Add variable**). Use your pipeline run values (same names as in the dataset):
>
> | Role | Default JSON key | Environment variable | Value |
> | --- | --- | --- | --- |
> | Series id | `item_id` | `AUTOGLUON_TS_ID_COLUMN` | Your `id_column` (e.g. `d_id`) |
> | Timestamp | `timestamp` | `AUTOGLUON_TS_TIMESTAMP_COLUMN` | Your `timestamp_column` (e.g. `date`) |
>
> No env vars are needed if your data already uses `item_id` and `timestamp`.


<a id="deployment-scoring"></a>

## 🎯 Deployment Scoring

After deployment is running, call the inference endpoint from deployment details. Time-series requests can differ from tabular payloads, so validate request shape with the generated predictor notebook and `TimeSeriesPredictor` examples. If your **`id_column`** or **`timestamp_column`** were not `item_id` / `timestamp`, configure the env vars from [Model Deployment](#model-deployment) (step **⑥**) when you deploy.

Example request for this tutorial (**`item_id`**, **`timestamp`**, **`target`**):

- `DEPLOYMENT_URL` - inference URL from deployment details (base URL only; the sample appends `/v1/models/<MODEL_NAME>:predict`).
- `MODEL_NAME` - deployed model resource name.
- `YOUR_TOKEN` - include only when token authentication is enabled; otherwise remove the `Authorization` header.

```bash
   curl -X POST \
   "<DEPLOYMENT_URL>/v1/models/<MODEL_NAME>:predict" \
   -H "Content-Type: application/json" \
   -H "Authorization: Bearer <YOUR_TOKEN>" \
   -d '{
    "instances": [
        {
            "item_id": "industry_a",
            "timestamp": "2021-08-18",
            "target": 47.2642021
        },
        {
            "item_id": "industry_a",
            "timestamp": "2021-08-19",
            "target": 47.88765448
        },
        {
            "item_id": "industry_a",
            "timestamp": "2021-08-20",
            "target": 48.6093501
        },
        {
            "item_id": "industry_a",
            "timestamp": "2021-08-21",
            "target": 48.48047505
        },
        {
            "item_id": "industry_a",
            "timestamp": "2021-08-22",
            "target": 47.76307524
        }
    ]
   }'
```

Example response:

```json
{
   "predictions":[
      {
         "item_id":"industry_a",
         "timestamp":"2021-08-23T00:00:00",
         "mean":47.76307524,
         "0.1":46.993928415183454,
         "0.2":47.257960723421256,
         "0.3":47.44834659378267,
         "0.4":47.61102430019208,
         "0.5":47.76307524,
         "0.6":47.91512617980792,
         "0.7":48.07780388621733,
         "0.8":48.26818975657874,
         "0.9":48.532222064816544
      },
      {
         "item_id":"industry_a",
         "timestamp":"2021-08-24T00:00:00",
         "mean":47.76307524,
         "0.1":46.675337368888236,
         "0.2":47.04873544010281,
         "0.3":47.31798172005212,
         "0.4":47.54804273875206,
         "0.5":47.76307524,
         "0.6":47.97810774124794,
         "0.7":48.20816875994788,
         "0.8":48.47741503989719,
         "0.9":48.85081311111176
      },
      {
         "item_id":"industry_a",
         "timestamp":"2021-08-25T00:00:00",
         "mean":47.76307524,
         "0.1":46.43087386093746,
         "0.2":46.888191233645024,
         "0.3":47.217949234154204,
         "0.4":47.49971528691408,
         "0.5":47.76307524,
         "0.6":48.026435193085916,
         "0.7":48.308201245845794,
         "0.8":48.637959246354974,
         "0.9":49.09527661906254
      },
      {
         "item_id":"industry_a",
         "timestamp":"2021-08-26T00:00:00",
         "mean":47.76307524,
         "0.1":46.2247815903669,
         "0.2":46.75284620684251,
         "0.3":47.13361794756533,
         "0.4":47.45897336038416,
         "0.5":47.76307524,
         "0.6":48.06717711961584,
         "0.7":48.39253253243467,
         "0.8":48.773304273157486,
         "0.9":49.301368889633096
      },
      {
         "item_id":"industry_a",
         "timestamp":"2021-08-27T00:00:00",
         "mean":47.76307524,
         "0.1":46.04321065503208,
         "0.2":46.633604844507985,
         "0.3":47.059320592591554,
         "0.4":47.42307900254676,
         "0.5":47.76307524,
         "0.6":48.10307147745324,
         "0.7":48.466829887408444,
         "0.8":48.89254563549201,
         "0.9":49.48293982496792
      },
      {
         "item_id":"industry_a",
         "timestamp":"2021-08-28T00:00:00",
         "mean":47.76307524,
         "0.1":45.87905798191762,
         "0.2":46.52580241270948,
         "0.3":46.9921506493306,
         "0.4":47.39062802255995,
         "0.5":47.76307524,
         "0.6":48.13552245744005,
         "0.7":48.533999830669394,
         "0.8":49.00034806729052,
         "0.9":49.64709249808238
      },
      {
         "item_id":"industry_a",
         "timestamp":"2021-08-29T00:00:00",
         "mean":47.76307524,
         "0.1":45.72810401984045,
         "0.2":46.42666784552403,
         "0.3":46.9303815116409,
         "0.4":47.360786266654586,
         "0.5":47.76307524,
         "0.6":48.16536421334541,
         "0.7":48.595768968359096,
         "0.8":49.09948263447597,
         "0.9":49.79804646015955
      }
   ]
}
```

- **Notebook source:** use the model-specific notebook from [Time series predictor notebook](#time-series-predictor-notebook).
- **API/reference:** see [AutoGluon TimeSeries forecasting quickstart](https://auto.gluon.ai/stable/tutorials/timeseries/forecasting-quickstart.html) and [KServe V1 Protocol](https://kserve.github.io/website/docs/concepts/architecture/data-plane/v1-protocol).

---

## Pipeline reference

- **Branch:** [rhoai-3.4](https://github.com/red-hat-data-services/pipelines-components/tree/rhoai-3.4) — [pipelines-components](https://github.com/red-hat-data-services/pipelines-components)
- **Pipeline:** [autogluon_timeseries_training_pipeline](https://github.com/red-hat-data-services/pipelines-components/tree/rhoai-3.4/pipelines/training/automl/autogluon_timeseries_training_pipeline) (name: `autogluon-timeseries-training-pipeline`)
- **Stability:** beta (see upstream README)

