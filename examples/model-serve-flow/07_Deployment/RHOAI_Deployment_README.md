# Deploying Compressed Large Language Models on Red Hat OpenShift AI

**Overview:**

This guide covers the final step of our workflow - deploying a compressed LLaMA 3.1 8B INT8 model using Red Hat OpenShift AI.
The model has already been compressed, validated for accuracy, and benchmarked for performance.
Now, we will deploy it on a RHOAI cluster, retrieve the necessary endpoints and token, and verify that it is serving requests, either via curl or the OpenAI SDK.

## Prerequisites

Before deploying the model, ensure the following conditions are met:

1. You have access to a RHOAI cluster.
2. A project is already created in Red Hat OpenShift AI.
3. The compressed and validated model is stored in cluster storage (PVC) attatched to the project.
4. Any running workbench using the same PVC is stopped, as a PVC cannot be shared between an active workbench and a model deployment.
5. CPU and GPU resources are available in the cluster.

## Steps to deply a model

### Step 1: Open the Project

1. Open your project in Red Hat OpenShift AI (for example, model-serve-3).
2. Navigate to the `Deployments tab`.
3. Click `Deploy Model`.

![Shown here](../assets/RHOAI_Deployment/01.png)

### Step 2: Configure Model Details

Fill out the **Model Details** section:

1. Set **Model location** to `Cluster Storage`.
2. In **Model path**, specify the path to the compressed model stored in the PVC.

**Example:** In this example, the compressed model is located at the following path:

```text
red-hat-ai-examples/examples/model-serve-flow/Llama_3.1_8B_Instruct_int8_dynamic
```

1. For **Model type**, select `Generative AI model (Examople LLM)`
2. Click **Next** to proceed to the `Model Deployment` Section

![Shown here](../assets/RHOAI_Deployment/02.png)

### Step 3: Configure Model Deployment

Fill out the **Model Deployment** section:

1. Provide a value for **Model deployment name**.
Example: `llama-3.1-8b-int8"`
2. Set `Hardware Profile` to `Nvidia GPU Accelerator`
3. Configure compute resources:

    a. Expand the **Custom resource requests and limits** dropdown.

    b. Set CPU and memory requests and limits based on the model size and expected workload.

    c. Specify the number of GPUs to allocate.

4. Set the `Serving runtime` to `vLLM NVIDIA GPU ServingRuntime KServe`
5. Set the number of replicas (can be left as 1).
6. Click **Next** to go to `Advanced Settings`

![Shown here](../assets/RHOAI_Deployment/03.png)

### Step 4: Configure Advanced Settings

Fill out the **Advanced Settings** section:

1. Under **Model access**, enable `Make model deployment available through an external route`.
2. Under **Token authentication**, enable `Require token authentication`.
3. Under **Configuration parameters**, enable`Add custom runtime environment variables` which will give an option to add new enviroment variables.

    Add the following environment variable:

    Name: `VLLM_LOGGING_LEVEL`
    Value: `DEBUG`

4. Select `Rolling update` as the **Deployment strategy**
5. Click **Next** and review the deployment details.

![Shown here](../assets/RHOAI_Deployment/04.png)

### Step 5: Deploy the Model

1. Click **Deploy Model**.
2. Return to the Deployments tab.
3. The model deployment (for example, llama-31-8b-int8") will initially show a status of `Starting`.
4. After a few minutes, the status should change to `Started`, indicating the model is ready to serve requests.

### Step 6: Retrieve Endpoints and Token

After the deployment status shows Started, you need the endpoints and token to interact with the model:

1. In the **Deployments** tab, locate your model deployment (for example, llama-3.1-8b-int8).
2. Click on the **dropdown** for the deployment to expand details.
3. Copy the token.
4. Click on the **internal and external endpoints** to get the endpoints. Use the `internal endpoint` when accessing the model from within the cluster and the `external enpoint` from outside the cluster.

![Retrieve token](../assets/RHOAI_Deployment/05.png)

![Retrieve endpoints](../assets/RHOAI_Deployment/06.png)

## Validating the Deployment

Once the deployment status is **Started**, you can verify that the model is serving requests using one of the following methods.

### 1. Verify using a curl request

You can test the deployment directly from the terminal:

```text
curl -X POST "<external_endpoint>/v1/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer "<your_token>" \
  -d '{
    "model": "llama-31-8b-int8",
    "prompt": "What is photosynthesis?",
    "max_tokens": 128,
    "temperature": 0.5
  }'
```

Replace <external_endpoint> with your model deployment route and <your_token> with your API token.
A valid response confirms that the model is deployed and serving requests.

A valid reponse looks something like this:

```bash
{
  "id": "1",
  "object": "text_completion",
  "created": 1767956024,
  "model": "llama-31-8b-int8",
  "choices": [
    {
      "index": 0,
      "text": " Photosynthesis is the process by which plants, algae, and some bacteria convert light energy from the sun into chemical energy in the form of glucose. This process occurs in specialized organelles called chloroplasts, which contain the pigment chlorophyll that absorbs light energy.\nPhotosynthesis is essential for life on Earth as it provides the energy and organic compounds needed to support the food chain. Without photosynthesis, plants would not be able to produce the glucose they need to grow and thrive, and animals would not have a source of food.\nThe overall equation for photosynthesis is:\n6 CO2 + 6 H2O + light energy →",
      "logprobs": null,
      "finish_reason": "length",
      "stop_reason": null,
      "token_ids": null,
      "prompt_logprobs": null,
      "prompt_token_ids": null
    }
  ],
  {
  "service_tier": null,
  "system_fingerprint": null,
  "usage": {
    "prompt_tokens": 6,
    "total_tokens": 134,
    "completion_tokens": 128,
    "prompt_tokens_details": null
  },
  "kv_transfer_params": null
}
```

### 2. Verify using the OpenAI SDK

If you prefer to test the deployment programmatically, you can use the OpenAI Python SDK.

Run the following code to test the deployment using OpenAI Python SDK.

```python
!pip install openai

from openai import OpenAI

api_key = "<your_token>"
internal_url = "<your_internal_endpoint>/v1"
external_url = "<external_endpoint>/v1"

# Use external_url if accessing the model from outside the cluster
# Use internal_url if you are accessing the model from within the same OpenShift cluster
client = OpenAI(
    base_url=external_url,
    api_key=api_key
)

response = client.completions.create(
    model="llama-31-8b-int8",
    prompt="What is photosynthesis?",
    max_tokens=128,
    temperature=0.5
)

print(response.choices[0].text)
```

## Debugging Deployment using OpenShift Console

For debugging any issues during deployment, follow the steps below:

Go to Openshift Console

Click on **Workloads**, then select **Pods**.

   ![Shown here](../assets/RHOAI_Deployment/07.png)

Search for your project name to view the list of pods.

Click on your project.

   ![Shown here](../assets/RHOAI_Deployment/08.png)

Click on **Pods** again to list all pods associated with the project.

Locate the deployment pod using the name specified during model deployment.

   ![Shown here](../assets/RHOAI_Deployment/09.png)

Click on the pod name and navigate to the Logs tab to monitor its logs.

  ![Shown here](../assets/RHOAI_Deployment/10.png)
