# S3-compatible storage for the Data Registry examples

The [Data Registry getting-started guide](../README.md)
registers metadata and a reference to a data location. It does not deploy
object storage, upload files, or keep S3 credentials. Several S3-compatible
object stores can serve these examples; [SeaweedFS](https://github.com/seaweedfs/seaweedfs)
is one option, not a requirement of the Data Registry. This guide uses a small,
standalone SeaweedFS deployment so you can try the S3-backed example without
an AWS account. You can instead use an existing S3-compatible service supplied
by your organization.

SeaweedFS is Apache-2.0 licensed and does not require a product license key.
The example below runs its single-node `weed mini` mode with an authenticated
S3 endpoint, a web Admin UI, and a persistent volume. It is an evaluation
setup, not a highly available storage design. Keep it separate from the Data
Registry service and from any existing object store.

```text
Data Registry asset metadata -> RHOAI Data Connection -> S3 endpoint
                                                    -> SeaweedFS bucket -> PVC
```

A standalone SeaweedFS **4.52** deployment with this configuration was
verified on OpenShift using the `restricted-v2` security context and a
dynamically provisioned PVC. The
[upstream quick start](https://github.com/seaweedfs/seaweedfs#quick-start)
documents `weed mini`, its S3 endpoint, and the Admin UI. The
[Helm chart documentation](https://github.com/seaweedfs/seaweedfs/blob/master/k8s/charts/seaweedfs/README.md#openshift-support)
provides an OpenShift path for larger deployments.

## Choose a storage path

| Situation | Path |
| --- | --- |
| Your organization already provides S3-compatible storage | Obtain its endpoint, bucket, region, and scoped credentials. Skip to [Create an RHOAI Data Connection](#create-an-rhoai-data-connection). |
| You need a self-contained evaluation | Follow the SeaweedFS installation and verification below. |

An existing service might be AWS S3, Red Hat Ceph Object Gateway, IBM Cloud
Object Storage, or an OpenShift Data Foundation Object Bucket Claim. Use the
provider and access policy approved for your project. An
[Object Bucket Claim](https://docs.redhat.com/en/documentation/red_hat_openshift_data_foundation/4.22/html/managing_hybrid_and_multicloud_resources/object-bucket-claim)
can supply a bucket and credentials when OpenShift Data Foundation is already
installed; installing that product is outside this project-level example.

## Install SeaweedFS in a new namespace

### Prerequisites

Use a checkout of this repository and run the commands from
`examples/data-registry/supplementary/`. You need `oc`, Python 3, the AWS
CLI, `openssl`, and `curl` on your workstation. You also need
permission to create a namespace and a default dynamic `StorageClass` with at
least 10 Gi of capacity. Ask an administrator for a namespace or storage class
if your access does not include those operations. The cluster must be able to
pull `docker.io/chrislusf/seaweedfs:4.52` or an approved mirror of it.

Confirm the cluster before creating resources:

```bash
oc whoami
oc config current-context
oc get storageclass
oc get namespace data-registry-storage --ignore-not-found
```

Use a different new namespace name if `data-registry-storage` already belongs
to another workload. Set `STORAGE_NAMESPACE` to that name in the commands
below. This example uses one internal ClusterIP Service; it does **not** create
a public Route.

```bash
export STORAGE_NAMESPACE=data-registry-storage
oc create namespace "$STORAGE_NAMESPACE"
```

### Create credentials

The S3 access key, S3 secret key, and Admin UI password are independent.
Generate them into a Kubernetes Secret without writing their values to a file
or terminal output:

```bash
python3 - <<'PY' | oc apply -n "$STORAGE_NAMESPACE" -f -
import json
import secrets

print(json.dumps({
    "apiVersion": "v1",
    "kind": "Secret",
    "metadata": {"name": "seaweedfs-credentials"},
    "type": "Opaque",
    "stringData": {
        "AWS_ACCESS_KEY_ID": "swfs" + secrets.token_hex(10),
        "AWS_SECRET_ACCESS_KEY": secrets.token_hex(32),
        "WEED_ADMIN_PASSWORD": secrets.token_hex(24),
    },
}))
PY
```

Keep this Secret when reapplying the manifest or restarting the pod. Recreating
it changes the credentials and requires updating any Data Connection that uses
them. The Secret is for this evaluation store; do not commit its values.

### Deploy the store

Review [seaweedfs.yaml](seaweedfs.yaml), then apply it in the new namespace:

```bash
oc apply -n "$STORAGE_NAMESPACE" -f seaweedfs.yaml
oc rollout status deployment/seaweedfs -n "$STORAGE_NAMESPACE" --timeout=5m
oc get deployment,pod,service,pvc -n "$STORAGE_NAMESPACE" -o wide
```

Expect `deployment/seaweedfs` to show `1/1` Ready, `pvc/seaweedfs-data` to
show `Bound`, and `service/seaweedfs` to expose ports **8333** (S3) and
**12646** (Admin UI). The image runs with a non-root UID and the restricted
OpenShift security context. The PVC uses the cluster's default StorageClass;
set `storageClassName` in the manifest if you need a specific one. The bucket
`data-registry-example` is created at startup.

The manifest gives `weed mini` a fixed Admin port below the usual ephemeral
port range, mounts `/tmp` separately, and stores object data under `/data` on
the PVC. The Service is internal to the cluster. It does not require a storage
operator, cluster-wide RBAC, or changes to the Data Registry deployment.

## Verify the S3 API

In one terminal, forward the two Service ports. Keep this command running
while testing. If either local port is already in use, stop the older port
forward or choose unused local ports and update the URLs below. Confirm the
forward names `service/seaweedfs` in your new namespace before using the S3
keys from that namespace:

```bash
oc -n "$STORAGE_NAMESPACE" port-forward service/seaweedfs \
  18333:8333 12646:12646
```

In a second terminal, set the same namespace variable and load the S3 keys
from the Secret. Command substitution keeps their values out of terminal
output; avoid shell tracing while credentials are in use.

```bash
export STORAGE_NAMESPACE=data-registry-storage
set +x
export AWS_ACCESS_KEY_ID="$(oc -n "$STORAGE_NAMESPACE" get secret seaweedfs-credentials \
  -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | openssl base64 -d -A)"
export AWS_SECRET_ACCESS_KEY="$(oc -n "$STORAGE_NAMESPACE" get secret seaweedfs-credentials \
  -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | openssl base64 -d -A)"
export AWS_DEFAULT_REGION=us-east-1
export AWS_EC2_METADATA_DISABLED=true
```

Create, list, and download a small object through the S3 API:

```bash
test_dir="$(mktemp -d)"
printf 'SeaweedFS S3 test\n' > "$test_dir/hello.txt"

aws --endpoint-url http://127.0.0.1:18333 s3api head-bucket \
  --bucket data-registry-example
aws --endpoint-url http://127.0.0.1:18333 s3api put-object \
  --bucket data-registry-example --key sample/hello.txt \
  --body "$test_dir/hello.txt"
aws --endpoint-url http://127.0.0.1:18333 s3api list-objects-v2 \
  --bucket data-registry-example --prefix sample/
aws --endpoint-url http://127.0.0.1:18333 s3api get-object \
  --bucket data-registry-example --key sample/hello.txt \
  "$test_dir/downloaded.txt"
cmp "$test_dir/hello.txt" "$test_dir/downloaded.txt"
printf 'S3 round trip passed\n'

rm -r "$test_dir"
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
```

The list should contain `sample/hello.txt`, and `cmp` should succeed. An
unsigned request to the bucket should return `403 AccessDenied`:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  http://127.0.0.1:18333/data-registry-example
```

To test persistence, restart only this deployment:

```bash
oc rollout restart deployment/seaweedfs -n "$STORAGE_NAMESPACE"
oc rollout status deployment/seaweedfs -n "$STORAGE_NAMESPACE" --timeout=5m
oc get pvc seaweedfs-data -n "$STORAGE_NAMESPACE"
```

The existing port forward disconnects when its pod is replaced. Restart the
port-forward command in the first terminal. In the second terminal, reload
the two AWS key exports from the Secret as shown above, then read the object
again:

```bash
aws --endpoint-url http://127.0.0.1:18333 s3api get-object \
  --bucket data-registry-example --key sample/hello.txt \
  /tmp/seaweedfs-persisted-hello.txt
cat /tmp/seaweedfs-persisted-hello.txt
rm /tmp/seaweedfs-persisted-hello.txt
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
```

The response should contain `SeaweedFS S3 test`. The object remains because
the PVC stays Bound.

## Use the Admin UI

With the Admin port forwarded, open <http://127.0.0.1:12646/login>. Sign in
as `admin` with the `WEED_ADMIN_PASSWORD` stored in
`Secret/seaweedfs-credentials`. On macOS, copy it to the clipboard without
printing it:

```bash
oc -n "$STORAGE_NAMESPACE" get secret seaweedfs-credentials \
  -o jsonpath='{.data.WEED_ADMIN_PASSWORD}' | openssl base64 -d -A | pbcopy
```

Use your workstation's clipboard utility in place of `pbcopy` on other
systems. The **Object Store → Buckets** page should show
`data-registry-example`; open it to browse `sample/hello.txt`. The UI also
shows cluster status and volume information. Keep the Admin UI internal and
authenticated rather than adding a public Route for this example.

## Create an RHOAI Data Connection

This step connects an RHOAI project to the object store. It is independent of
the standalone S3 installation test above. In the RHOAI dashboard, open the
Data Science project that will own the example asset, select **Connections →
Create connection**, and choose **S3 compatible object storage - v1**.

| Field | SeaweedFS example value |
| --- | --- |
| Connection name | `data-registry-storage` |
| Endpoint | `http://seaweedfs.data-registry-storage.svc:8333` |
| Access key | `AWS_ACCESS_KEY_ID` from `Secret/seaweedfs-credentials` |
| Secret key | `AWS_SECRET_ACCESS_KEY` from the same Secret |
| Region | `us-east-1` |
| Bucket | `data-registry-example` |

If you chose another storage namespace, replace `data-registry-storage` in the
endpoint. The `.svc` address is available inside the cluster, not from a
workstation browser. Use your organization's approved process to transfer the
scoped key values into the RHOAI connection Secret. Do not put them into asset
metadata, Git, screenshots, or a public URL. A NetworkPolicy or service-mesh
rule may require an explicit path from the project to port 8333.

Return to [Step 2](../02-register-data-asset/README.md) to upload the synthetic
FAQ and register an unstructured example asset with the connection and path:

```text
s3://data-registry-example/examples/customer-support/
```

The Data Registry stores the path and connection reference. Registration does
not prove that the object exists or that a workbench can read it; the S3 test
above verifies the object independently. An RHOAI user needs storage access
through the connection as well as registry metadata access through project
RBAC.

## Troubleshoot and retain the data

| Symptom | Check |
| --- | --- |
| PVC stays `Pending` | Check the default StorageClass, quota, and PVC events with `oc describe pvc seaweedfs-data -n "$STORAGE_NAMESPACE"`. |
| Pod cannot pull the image | Check pod events and cluster egress or mirror policy. Do not substitute an unrelated image. |
| Pod restarts or cannot write `/data` | Check `oc describe pod` and `oc logs deployment/seaweedfs -n "$STORAGE_NAMESPACE"`; confirm PVC ownership and the assigned OpenShift security context. |
| S3 requests return `403` | Confirm the generated Secret and AWS CLI environment match; anonymous access is intentionally denied. |
| UI redirects to login | This is expected. Use the Admin password from the Secret and the forwarded port 12646. |
| S3 returns `403` with the new Secret, or port forwarding reports an address already in use | Check for an older port forward on 18333 or 12646. Stop it and forward `service/seaweedfs` in the intended namespace. Credentials from one SeaweedFS instance will not authenticate to another. |
| Forwarded ports stop after restart | Start `oc port-forward` again; it was attached to the replaced pod. |
| RHOAI workload cannot reach S3 | Verify the endpoint uses the correct namespace and port 8333, then check NetworkPolicy and DNS from the workload namespace. |

The `sample/hello.txt` object is harmless test data. Keep the namespace and
PVC if you plan to reuse the store. **Deleting the namespace or PVC deletes
the object data** when the StorageClass uses a delete reclaim policy; make an
intentional backup and removal decision before cleaning up. Nothing in this
guide deletes persistent storage or changes an existing object store.
