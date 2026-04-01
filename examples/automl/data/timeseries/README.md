# Time series sample data

## Electricity demand (primary tutorial dataset)

The file **`input_data/electricity_industry_a_forecasting.csv`** is derived from open data published in [IBM watsonx-ai-samples](https://github.com/IBM/watsonx-ai-samples/tree/master/cloud/data):

- **Source:** [`cloud/data/electricity/electricity_usage.csv`](https://github.com/IBM/watsonx-ai-samples/blob/master/cloud/data/electricity/electricity_usage.csv) (columns `date`, `industry_a_usage`).
- **Transformation:** A constant series id was added and columns were renamed so the CSV matches the [autogluon timeseries training pipeline](https://github.com/red-hat-data-services/pipelines-components/tree/autox/pipelines/training/automl/autogluon_timeseries_training_pipeline) expectation: `item_id`, `timestamp`, `target`. All rows use `item_id` = `industry_a` (single series).

Use this file with `id_column`=`item_id`, `timestamp_column`=`timestamp`, `target`=`target`, and no known covariates unless you enrich the data yourself.

## Synthetic multi-series (optional)

**`input_data/timeseries_sales.csv`** — small synthetic dataset aligned with the pipeline component [test data](https://github.com/red-hat-data-services/pipelines-components/blob/autox/pipelines/training/automl/autogluon_timeseries_training_pipeline/tests/data/timeseries_sales.csv) on branch `autox`; includes optional covariate `promo` for `known_covariates_names`.
