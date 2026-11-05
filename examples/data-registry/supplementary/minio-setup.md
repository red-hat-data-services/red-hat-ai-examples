# Local MinIO-compatible storage for the Data Registry examples

This supplementary guide provides disposable S3-compatible object storage for
the [Data Registry getting-started example](../rhoai-3.6/getting-started.md).
It is not part of the Data Registry deployment itself. Use it when you need a
local bucket for registering and testing example assets.

> [!WARNING]
> Before deploying, find a MinIO-approved image for your organization or
> cluster. The `MINIO_IMAGE` value below uses a MinIO AIStor image only as the
> current example reference. Replace it with the image and tag or digest that
> your administrator approves, and supply any required pull Secret or license.
> Do not use this single-replica example for production data.

Red Hat's older examples use `quay.io/minio/minio`, but that community image is
no longer publicly pullable. MinIO AIStor is available through the certified
OpenShift catalog, but it is a licensed MinIO product. Without a valid AIStor
license, the server can start in offline mode while denying S3 operations. See
the [Red Hat MinIO image advisory](https://access.redhat.com/solutions/7148629)
and the [MinIO AIStor OpenShift installation guide](https://docs.min.io/aistor/installation/kubernetes/install/deploy-aistor-on-openshift/).

## What this creates

In an existing RHOAI project, the steps create:

- a 10 Gi persistent volume for object data;
- a generated credential Secret, whose values are never committed;
- one MinIO-compatible server and an internal Service; and
- an API Route and a console Route for OpenShift access.

The bucket and RHOAI Data Connection are created separately so that each
example can choose its own bucket name and connection scope.

## Prerequisites

You need:

- an OpenShift project visible in the RHOAI dashboard;
- `oc` logged in to the intended cluster;
- permission to create a PVC, Secret, Deployment, Service, and Routes in that
  project;
- a default StorageClass, or a local edit to
  [minio.yaml](minio.yaml) that sets `storageClassName`; and
- an administrator-approved MinIO or AIStor image, pull Secret, and license if
  required by the image.

Set the project in which you will register the Data Registry assets. Replace
the placeholder before running the checks below:

```bash
export PROJECT="<your-data-science-project>"
```

Confirm the cluster and project before applying anything:

```bash
oc whoami
oc config current-context
oc project "$PROJECT"
oc get storageclass
```

## 1. Choose the project and image

Set the project in which you will register the Data Registry assets. Replace
the image placeholder. The AIStor reference is included only to make the
example complete; use your approved image whenever it differs.

```bash
export MINIO_IMAGE="quay.io/minio/aistor/minio:RELEASE.2026-09-19T17-05-25Z"

oc project "$PROJECT"
```

If the approved image is private, create its image pull Secret in this project
and attach it to the `default` ServiceAccount before continuing. Follow your
cluster administrator's registry instructions; do not commit pull Secret data.

## 2. Create generated credentials

The following commands generate credentials locally and apply them to a Secret
without printing the values. Re-running the block reuses existing credentials.

```bash
if ! oc get secret minio-root-credentials -n "$PROJECT" >/dev/null 2>&1; then
  MINIO_ROOT_USER="minio-$(openssl rand -hex 6)"
  MINIO_ROOT_PASSWORD="$(openssl rand -hex 24)"
  oc create secret generic minio-root-credentials \
    -n "$PROJECT" \
    --from-literal=MINIO_ROOT_USER="$MINIO_ROOT_USER" \
    --from-literal=MINIO_ROOT_PASSWORD="$MINIO_ROOT_PASSWORD"
  unset MINIO_ROOT_USER MINIO_ROOT_PASSWORD
fi
```

## 3. Deploy the server

Apply the maintained supplementary manifest after replacing its image
placeholder:

```bash
sed "s|IMAGE_PLACEHOLDER|${MINIO_IMAGE}|g" \
  supplementary/minio.yaml | oc apply -n "$PROJECT" -f -

oc rollout status deployment/minio -n "$PROJECT" --timeout=5m
oc get pods,svc -n "$PROJECT" -l app.kubernetes.io/name=minio
oc get route minio-api minio-ui -n "$PROJECT"
```

The server uses the internal S3 endpoint:

```text
http://minio-service.<project>.svc.cluster.local:9000
```

The external routes are useful for the browser console and for clients that
cannot run inside the cluster:

```bash
oc get route minio-api minio-ui -n "$PROJECT" \
  -o custom-columns=NAME:.metadata.name,HOST:.spec.host
```

If the pod is not ready, inspect the events and logs before continuing:

```bash
oc describe pod -n "$PROJECT" -l app.kubernetes.io/name=minio
oc logs deployment/minio -n "$PROJECT"
```

For AIStor, a log message saying that the server is running in offline mode
means that a valid license is missing; S3 requests will be denied until the
approved license is installed.

## 4. Create a bucket

Open the `minio-ui` Route in a browser. Retrieve the generated credentials only
when you need them, using your approved local secret-handling process:

```bash
oc get secret minio-root-credentials -n "$PROJECT" \
  -o jsonpath='{.data.MINIO_ROOT_USER}' | base64 --decode; echo
oc get secret minio-root-credentials -n "$PROJECT" \
  -o jsonpath='{.data.MINIO_ROOT_PASSWORD}' | base64 --decode; echo
```

Sign in to the console, create a bucket such as `data-registry-example`, and
keep the bucket name for the Data Connection step. Do not use a bucket name
containing spaces or uppercase letters.

## 5. Create an RHOAI Data Connection

In the RHOAI dashboard, open the same project and select **Connections**,
then **Create connection**. Choose **S3 compatible object storage - v1** and
enter:

| Field | Value |
| --- | --- |
| Connection name | A descriptive name such as `minio-data-registry` |
| Endpoint | `http://minio-service.<project>.svc.cluster.local:9000` |
| Access key | The `MINIO_ROOT_USER` Secret value |
| Secret key | The `MINIO_ROOT_PASSWORD` Secret value |
| Region | `us-east-1` |
| Bucket | The bucket created in the previous step |

For a connection Secret created by automation, keep the credential values in
the Secret and use the RHOAI S3 connection labels and annotations. Never put
the access key or secret key in this repository.

## 6. Use the storage with the Data Registry example

Return to the [Data Registry getting-started guide](../rhoai-3.6/getting-started.md)
and register an asset in the same RHOAI project. When the form asks for a
connection, choose the connection created above. Use an object path such as:

```text
s3://data-registry-example/sample/orders/
```

The Data Registry stores the asset metadata and connection reference. It does
not upload objects, copy data, or validate that the path exists.

## Cleanup

Deleting the PVC permanently deletes the objects stored by this disposable
instance. Confirm that the bucket is no longer needed before running cleanup:

```bash
oc delete route minio-api minio-ui -n "$PROJECT"
oc delete service minio-service -n "$PROJECT"
oc delete deployment minio -n "$PROJECT"
oc delete secret minio-root-credentials -n "$PROJECT"
oc delete pvc minio-data -n "$PROJECT"
```

The RHOAI Data Connection is separate; delete it from the project's
**Connections** page when it is no longer needed.
