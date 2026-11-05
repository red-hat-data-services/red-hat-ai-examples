# Step 3: Use the Data Registry API from a workbench

[← Step 2: Register an asset](../02-register-data-asset/README.md) ·
[Step 4: Share access →](../04-share-registry-access/README.md) ·
[Guide index](../README.md)

This step turns the metadata created in Step 2 into a reproducible API exercise.
You create a project workbench, attach the same S3 connection, and run the
[guided notebook](data-registry-api-walkthrough.ipynb). The notebook reads the
collection and asset through the authenticated Data Registry API, checks the
connection reference and S3 path, then lists and downloads the synthetic FAQ
from SeaweedFS. This demonstrates the difference between *discovering data*
through the registry and *reading data* through a storage connection.

The notebook follows the discovery, reference-checking, download, and
verification sequence in the
[PDF volume example](https://gitlab.cee.redhat.com/data-strategy/data-registry-production/-/tree/main/notebook-examples/rhai-s3-pdf-volume-download).
This example uses one small Markdown document so you can see every step without
a separate producer script. No credentials or bearer tokens are printed.

## 1. Check prerequisites

Complete [Step 2](../02-register-data-asset/README.md). In
`data-registry-example`, confirm that the `customer-support` collection and
`customer-support-faq` asset appear, and that the `data-registry-storage`
connection exists. The S3 object must already be uploaded under
`examples/customer-support/`.

Ask an RHOAI administrator to confirm that project workbenches are enabled. On
an RHOAI 3.6 cluster, the `DataScienceCluster` field is
`spec.components.workbenches.workbenchesV2.managementState`. If it is
`Removed`, the **Workbenches** tab cannot create a workbench. An administrator
must set it to `Managed` through the supported cluster change process and wait
for the component to become ready. This is a cluster-wide component setting;
project owners should not change it as part of creating an asset.

```bash
oc get datasciencecluster default-dsc \
  -o jsonpath='{.spec.components.workbenches.workbenchesV2.managementState}{"\n"}'
```

The example assumes a Jupyter workbench image with Python 3, `requests`,
`boto3`, and `python-dotenv`. If the selected image lacks a package, install
the versions in [requirements.txt](requirements.txt) into the workbench kernel
using its approved package mirror before running the notebook. The optional
[`.env.example`](../.env.example) contains public names and paths only; the
attached connection supplies S3 credentials.

> **Screenshot to add:** Project **Workbenches** tab before creating the example.

## 2. Create and connect the workbench

In the RHOAI dashboard, open **Projects → data-registry-example → Workbenches**
and select **Create workbench**. Use these settings:

| Setting | Example selection | Why |
| --- | --- | --- |
| Name | `data-registry-api` | Makes this exercise easy to identify. |
| Image | Supported Jupyter/Python 3 data science image | Opens the supplied `.ipynb` in JupyterLab. |
| Size | Small, about 2 CPU and 4 GiB if available | Enough for API calls and a tiny document download; no GPU needed. |
| Storage | A 5 GiB persistent project volume | Keeps the notebook and downloaded file after a pod restart. |
| Connection | Attach existing `data-registry-storage` | Injects endpoint, bucket, and credentials from Step 2. |

Choose the image, size, and storage class offered by your installation. Attach
the **existing** connection during creation. If your UI offers attachment only
after creation, edit the workbench, select `data-registry-storage`, save, and
wait for its restart. Do not copy S3 keys into the notebook or a second Secret.
Start the workbench and wait until it shows **Running/Ready**, then open
JupyterLab.

> **Screenshot to add:** Create workbench form with name, image, size, and
> storage; then the connection selector with `data-registry-storage` selected.
>
> **Screenshot to add:** Ready workbench row and JupyterLab launcher.

## 3. Authorize the workbench in this project

The workbench's Kubernetes ServiceAccount is the API caller. Attaching an S3
connection gives the pod storage configuration, but does not give its
ServiceAccount Data Registry permissions. A project administrator should find
the ServiceAccount of the **new** workbench pod and grant only the
`feast-data-registry-admin` ClusterRole in `data-registry-example`. The notebook
creates one additional collection and asset through the API and references
the project connection, so viewer or editor access alone is insufficient:

```bash
oc get pods -n data-registry-example \
  -o custom-columns=NAME:.metadata.name,SA:.spec.serviceAccountName

# Replace WORKBENCH_SA with the SA shown for data-registry-api.
oc adm policy add-role-to-user feast-data-registry-admin \
  system:serviceaccount:data-registry-example:WORKBENCH_SA \
  -n data-registry-example

oc auth can-i --as=system:serviceaccount:data-registry-example:WORKBENCH_SA \
  create volumes.dataregistry.opendatahub.io -n data-registry-example

oc auth can-i --as=system:serviceaccount:data-registry-example:WORKBENCH_SA \
  use connections.dataregistry.opendatahub.io -n data-registry-example
```

Both checks should return `yes`. This is a **namespaced RoleBinding** to
an operator-provided role. It does not modify a ClusterRole or grant access to
other projects. Use the exact ServiceAccount reported by the new pod, not a
guessed name. See [Step 4](../04-share-registry-access/README.md) for the
existing user and group sharing examples.

## 4. Supply the public TLS certificate authority

The notebook calls the in-cluster TLS Service
`https://feast-data-registry-data-registry.rhoai-data-registry.svc:443`.
OpenShift signs that Service certificate with its service CA. Export the
**public CA certificate**, not a private key or bearer token, from the example
project:

```bash
oc get configmap openshift-service-ca.crt -n data-registry-example \
  -o jsonpath='{.data.service-ca\.crt}' > service-ca.crt

openssl x509 -in service-ca.crt -noout -subject
```

In JupyterLab, upload `service-ca.crt` into the same folder as the notebook.
The notebook verifies TLS against this file. If your administrator supplies a
different trusted CA bundle or service hostname, set `REGISTRY_CA_BUNDLE` and
`REGISTRY_URL` in the notebook configuration cell. Keep certificate validation
enabled. The service hostname must match a SAN in its serving certificate.

## 5. Upload and run the notebook

Download or clone this repository, then upload
[data-registry-api-walkthrough.ipynb](data-registry-api-walkthrough.ipynb) and
`service-ca.crt` to the workbench's persistent folder. In JupyterLab:

1. Open the notebook and read its first cell. Check the project, collection,
   asset, expected S3 prefix, and connection name in the configuration cell.
2. Select the workbench's Python 3 kernel. If imports fail, install
   [requirements.txt](requirements.txt) using the approved workbench package
   mirror, restart the kernel, and run from the top.
3. Run the cells **in order**. The notebook stops on a failed prerequisite,
   unexpected HTTP response, wrong connection, wrong object, or hash mismatch.
4. Confirm the final cell prints a success summary and that
   `downloads/customer-support-faq.md` exists in the workbench folder.

The notebook performs these checks:

| Notebook section | API or storage action | Expected result |
| --- | --- | --- |
| Runtime preflight | Check service CA, projected ServiceAccount token, and connection variable *presence* | No secret values displayed. |
| Authentication | GET `/v1/config` without a token, then `/v1/data-registry-example/config` with the workbench token | The proxy denies the anonymous request; project discovery succeeds for an authorized ServiceAccount. |
| Collections | GET `/v1/data-registry-example/namespaces` | `customer-support` is listed. |
| Asset list and detail | GET `/v1/data-registry-example/namespaces/customer-support/volumes` and `/volumes/customer-support-faq` | Exact asset, format, path, and connection reference match Step 2. |
| S3 list and download | `ListObjectsV2`, `GetObject` through the attached connection | The fixture is present and downloaded. |
| Verification | SHA-256 of the downloaded file | Matches the committed synthetic fixture. |
| API registration | POST a `customer-support-api` collection and `customer-support-faq-api` volume; GET both | A second catalog entry points at the same S3 prefix and connection. |

The registry API returns **metadata**. The S3 client uses the workbench's
attached connection to fetch the **document bytes**. Neither a registry read
nor a saved connection reference alone proves that a user may read physical
data. The final S3 call provides that separate check.

> **Screenshot to add:** Notebook after the collections and asset-detail cells,
> with only names and non-sensitive metadata visible.
>
> **Screenshot to add:** Final success cell and JupyterLab file browser showing
> the downloaded document.

## If a check fails

| Symptom | What to check |
| --- | --- |
| No Workbenches tab or create action | Ask the administrator to check the workbenchesV2 management state and component status. |
| Missing `AWS_*` variable | Attach `data-registry-storage` to this workbench and restart it; do not add credentials to the notebook. |
| Registry request returns 401 | The projected ServiceAccount token is missing, expired, or not sent to the API. Restart the workbench and rerun the preflight. |
| Registry request returns 403 | Check the workbench pod's actual ServiceAccount and its namespaced admin RoleBinding. |
| TLS certificate error | Check `service-ca.crt`, the service hostname, and the cluster's CA rotation. Do not disable verification. |
| Connection or path differs | Open the asset detail page and correct the metadata in Step 2. The notebook deliberately rejects a different resource. |
| S3 request returns 403 | Check connection attachment, the bucket policy, and that the connection uses the S3 API endpoint rather than the SeaweedFS Admin port. |
| S3 times out | Check workbench egress and storage ingress NetworkPolicies for the project and port 8333. |
| SHA-256 mismatch | Upload the committed fixture to the documented key again only after inspecting the current object and confirming this test key is yours. |

This exercise does not delete assets, connections, bucket objects, workbench
storage, or project resources. Continue to [Step 4](../04-share-registry-access/README.md)
for the current sharing guidance.
