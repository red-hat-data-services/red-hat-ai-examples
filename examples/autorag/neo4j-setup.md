# Neo4j on Red Hat OpenShift AI — Installation and Configuration Runbook

**Status**: Validated on OpenShift 4.21 / RHOAI 3.5.0 (ROSA, us-east-1)  
**Scope**: Customer/admin-provisioned Neo4j as a prerequisite for AutoRAG GraphRAG workloads

---

## Overview

Neo4j is the graph database used by AutoRAG's GraphRAG capability (`BaseGraphStore` + Neo4j adapter). RHOAI does **not** auto-install or lifecycle-manage Neo4j — it is a customer- or platform-admin-provisioned prerequisite. This runbook documents the validated install path, connectivity validation, sizing guidance, and known constraints.

**Recommended path**: Neo4j **Community Edition** via the official **Neo4j Helm chart** (`helm.neo4j.com/neo4j`), deployed into a dedicated namespace.

---

## Edition and Operator Decision

| Criterion | Community Edition (CE) | Enterprise Edition (EE) |
|---|---|---|
| License | Apache 2.0 / free | Commercial — requires Neo4j contract |
| Clustering | No (single-instance only) | Yes (causal cluster) |
| RBAC / fine-grained security | No | Yes |
| AutoRAG GraphRAG suitability | Sufficient for PoC and small-scale prod | Required for multi-replica HA |
| Helm chart support | `neo4j-community` chart | `neo4j` chart (same repo, `edition: enterprise`) |
| Disconnected | Requires mirroring `neo4j:<version>` from Docker Hub | Same image requirement |

**Recommendation**: Use **Community Edition** for development, evaluation, and single-node GraphRAG workloads. Switch to Enterprise only when HA clustering, fine-grained auth, or contract SLA is required. Note that Enterprise requires `acceptLicenseAgreement: "yes"` in values and a valid license.

The **Neo4j Operator** (OperatorHub) is an alternative to Helm but is less commonly used for single-instance deployments and adds CRD lifecycle complexity. The Helm chart is the validated and recommended path.

---

## Prerequisites

### 1. OpenShift permissions
- Cluster-admin or namespace-admin with ability to grant SCCs
- Ability to create `ServiceAccount` with `anyuid` SCC (Neo4j pod runs as UID/GID 7474)

### 2. Storage
- A `StorageClass` supporting `ReadWriteOnce` (RWO) dynamic provisioning  
  Validated: **`gp3-csi`** on ROSA/AWS  
  Minimum: 100 Gi for the data PVC (see [Sizing](#sizing-guidance))

### 3. Image pull access
Neo4j images are hosted on **Docker Hub** (`neo4j:<version>`). On clusters with Docker Hub rate limits or in disconnected environments, a pull secret is required.

```bash
# Create a Docker Hub pull secret (replace credentials)
oc create secret docker-registry dockerhub-pull-secret \
  --docker-server=docker.io \
  --docker-username=<your-dockerhub-user> \
  --docker-password=<your-dockerhub-token> \
  -n neo4j
```

For **disconnected/air-gapped** clusters, mirror the image to your internal registry first — see [Disconnected Constraints](#disconnectedair-gapped-constraints).

### 4. Helm
```bash
helm repo add neo4j https://helm.neo4j.com/neo4j
helm repo update
```

---

## Installation

### Step 1 — Create the namespace

```bash
oc new-project neo4j
```

### Step 2 — Grant `anyuid` SCC

Neo4j runs as UID 7474 (non-root but specific UID). The `restricted-v2` SCC blocks specific UIDs; `anyuid` is required.

```bash
oc adm policy add-scc-to-user anyuid \
  -z default \
  -n neo4j
```

Verify after deployment:
```bash
oc get pod autorag-neo4j-0 -n neo4j \
  -o jsonpath='{.metadata.annotations.openshift\.io/scc}'
# Expected: anyuid
```

### Step 3 — Create values file

Save as `neo4j.values.yaml`:

```yaml
neo4j:
  name: my-standalone
  # Uncomment to set a specific initial password (otherwise auto-generated)
  # password: "ChangeMe-8c^4&1-383F4f8"

image:
  # Note: must be plain strings, not name: key objects
  imagePullSecrets:
    - "dockerhub-pull-secret"

  resources:
    cpu: 4
    memory: 16Gi

  # Uncomment for Enterprise edition (requires Neo4j license)
  # edition: "enterprise"
  # acceptLicenseAgreement: "yes"

env:
  NEO4J_PLUGINS: '["apoc"]'

config:
  dbms.security.procedures.unrestricted: "apoc.*"

apoc_config:
  apoc.trigger.enabled: "true"
  apoc.import.file.enabled: "true"

volumes:
  data:
    mode: "dynamic"
    dynamic:
      storageClassName: gp3-csi   # Adjust to your cluster's RWO StorageClass
```

### Step 4 — Install via Helm

```bash
helm install autorag-neo4j neo4j/neo4j \
  --namespace neo4j \
  --values neo4j.values.yaml \
  --wait --timeout 5m
```

Expected result: `STATUS: deployed` and pod `autorag-neo4j-0` in `Running` state.

### Step 5 — Verify deployment

```bash
# Pod running
oc get pod autorag-neo4j-0 -n neo4j

# PVC bound (100Gi gp3-csi)
oc get pvc -n neo4j

# Services created
oc get svc -n neo4j
```

Expected services:

| Service | Type | Ports | Purpose |
|---|---|---|---|
| `autorag-neo4j` | ClusterIP | 7687, 7474 | Primary app access (Bolt + HTTP) |
| `autorag-neo4j-admin` | ClusterIP | 7687, 7474 | Admin/monitoring access |
| `my-standalone-lb-neo4j` | LoadBalancer | 7474, 7473, 7687 | External access (optional; requires cloud LB) |

### Step 6 — Verify APOC

APOC Core is bundled in the Neo4j image at `/var/lib/neo4j/labs/`. Setting `NEO4J_PLUGINS: '["apoc"]'` in the values causes the entrypoint to copy it into `/var/lib/neo4j/plugins/` at startup — no internet access required.

```bash
# Jar was copied into place
oc exec autorag-neo4j-0 -n neo4j -- ls /var/lib/neo4j/plugins/
# Expected: apoc.jar

NEO4J_PASSWORD=$(oc get secret my-standalone-auth -n neo4j \
  -o jsonpath='{.data.NEO4J_AUTH}' | base64 -d | cut -d/ -f2)

# APOC version is callable
oc exec autorag-neo4j-0 -n neo4j -- \
  cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" \
  "RETURN apoc.version() AS version;"
# Expected: "2026.06.0"

# Procedures are accessible (confirms unrestricted config is applied)
oc exec autorag-neo4j-0 -n neo4j -- \
  cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" \
  "CALL apoc.help('apoc') YIELD name RETURN count(name) AS total_procedures;"
# Expected: 436
```

> **Note — APOC Extended**: `apoc-extended` (the superset with additional procedures) is a separate artifact that the entrypoint downloads at runtime from GitHub. It requires outbound internet access and will fail in disconnected/air-gapped clusters. APOC Core covers the procedures needed for GraphRAG workloads.

> **Note — Extensions tab**: Plugin management via a UI Extensions tab is a Neo4j Desktop feature and is not available in the browser-based deployment. Use the Cypher queries above to inspect installed procedures.

---

## Authentication and Secrets

The Helm chart auto-generates credentials and stores them in a Kubernetes Secret:

```bash
# Secret name: <neo4j.name>-auth (default: my-standalone-auth)
oc get secret my-standalone-auth -n neo4j \
  -o jsonpath='{.data.NEO4J_AUTH}' | base64 -d
# Output format: neo4j/<password>
```

### Exposing credentials to AutoRAG workloads

Create a dedicated secret in the AutoRAG namespace that references the Bolt URI and credentials:

```bash
NEO4J_PASSWORD=$(oc get secret my-standalone-auth -n neo4j \
  -o jsonpath='{.data.NEO4J_AUTH}' | base64 -d | cut -d/ -f2)

oc create secret generic neo4j-bolt-credentials \
  --from-literal=NEO4J_URI="bolt://autorag-neo4j.neo4j.svc.cluster.local:7687" \
  --from-literal=NEO4J_USERNAME="neo4j" \
  --from-literal=NEO4J_PASSWORD="${NEO4J_PASSWORD}" \
  -n <autorag-namespace>
```

Reference in a KFP pipeline task or Pod spec:

```yaml
env:
  - name: NEO4J_URI
    valueFrom:
      secretKeyRef:
        name: neo4j-bolt-credentials
        key: NEO4J_URI
  - name: NEO4J_USERNAME
    valueFrom:
      secretKeyRef:
        name: neo4j-bolt-credentials
        key: NEO4J_USERNAME
  - name: NEO4J_PASSWORD
    valueFrom:
      secretKeyRef:
        name: neo4j-bolt-credentials
        key: NEO4J_PASSWORD
```

---

## Connectivity Validation

### From within the neo4j pod (cypher-shell)

```bash
NEO4J_PASSWORD=$(oc get secret my-standalone-auth -n neo4j \
  -o jsonpath='{.data.NEO4J_AUTH}' | base64 -d | cut -d/ -f2)

oc exec autorag-neo4j-0 -n neo4j -- \
  cypher-shell -u neo4j -p "${NEO4J_PASSWORD}" "RETURN 1 AS test;"
# Expected output:
# test
# 1
```

### From an AutoRAG pipeline task pod (KFP workload)

Run a one-off test pod in the AutoRAG namespace:

```bash
NEO4J_PASSWORD=$(oc get secret my-standalone-auth -n neo4j \
  -o jsonpath='{.data.NEO4J_AUTH}' | base64 -d | cut -d/ -f2)

oc run neo4j-bolt-test \
  --rm -it \
  --image=neo4j:2026.06.0 \
  --restart=Never \
  -n <autorag-namespace> \
  -- cypher-shell \
    -a bolt://autorag-neo4j.neo4j.svc.cluster.local:7687 \
    -u neo4j \
    -p "${NEO4J_PASSWORD}" \
    "RETURN 1 AS bolt_ok;"
```

Expected output: `bolt_ok / 1`

### From Python (AutoRAG / LlamaIndex neo4j driver)

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://autorag-neo4j.neo4j.svc.cluster.local:7687",
    auth=("neo4j", "<NEO4J_PASSWORD>")
)
with driver.session() as session:
    result = session.run("RETURN 1 AS test")
    print(result.single()["test"])  # 1
driver.close()
```

---

## Networking

### In-cluster Bolt URI

```
bolt://autorag-neo4j.neo4j.svc.cluster.local:7687
```

Format: `bolt://<service-name>.<namespace>.svc.cluster.local:7687`

### HTTP browser UI

```
http://autorag-neo4j.neo4j.svc.cluster.local:7474
```

To expose the UI externally, create an OpenShift Route:

```bash
oc expose svc/autorag-neo4j -n neo4j --port=7474 --name=neo4j-browser
oc get route neo4j-browser -n neo4j
```

### Network policies

No network policies were applied in the validated deployment. For production, restrict ingress to the Bolt port from the AutoRAG namespace only:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-autorag-bolt
  namespace: neo4j
spec:
  podSelector:
    matchLabels:
      app: my-standalone
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: <autorag-namespace>
      ports:
        - port: 7687
          protocol: TCP
```

### TLS / Bolt+s

The validated deployment uses **unencrypted Bolt** (`bolt://`). For production or compliance-sensitive deployments, Neo4j CE supports TLS via self-signed or CA-signed certs mounted as a Secret. See the [Neo4j Helm TLS docs](https://neo4j.com/docs/operations-manual/current/kubernetes/quickstart-standalone/) for the `ssl:` stanza in values.yaml. Use `bolt+ssc://` for self-signed or `bolt+s://` for properly signed certificates.

---

## Sizing Guidance (GraphRAG-Oriented Workload)

The following is validated for a single-node GraphRAG development/PoC workload:

| Resource | Minimum | Validated (this deployment) | Notes |
|---|---|---|---|
| CPU | 2 cores | 4 cores (request = limit) | Neo4j is CPU-intensive during entity resolution and graph traversal |
| Memory | 8 Gi | 16 Gi | Set heap and pagecache explicitly for larger graphs (see below) |
| Storage (data PVC) | 50 Gi | 100 Gi RWO (`gp3-csi`) | Depends heavily on corpus size; allow 3–5× raw text size |
| Storage (logs) | 10 Gi | included in data PVC | Separate logs PVC optional for production |

**JVM heap and pagecache tuning** (add to values.yaml for large corpora):

```yaml
config:
  NEO4J_server_memory_heap_initial__size: "4G"
  NEO4J_server_memory_heap_max__size: "8G"
  NEO4J_server_memory_pagecache_size: "4G"
```

Rule of thumb: heap + pagecache ≤ 80% of pod memory limit.

---

## Prerequisites Summary for AutoRAG Users

The following must be in place **before** configuring an AutoRAG pipeline with `graphstore_type: neo4j`:

1. A running Neo4j instance reachable from the AutoRAG pipeline namespace via Bolt (TCP 7687)
2. A Kubernetes Secret in the AutoRAG namespace containing `NEO4J_URI`, `NEO4J_USERNAME`, and `NEO4J_PASSWORD`
3. Optionally: a NetworkPolicy allowing ingress to Neo4j from the pipeline namespace

AutoRAG will surface a clear error (e.g. `ServiceUnavailable: Failed to establish connection to...`) if Neo4j is unreachable or credentials are wrong — no silent failure.

---

## Known Constraints and Unsupported Scenarios

### FIPS
Neo4j CE 2026.x does **not** publish FIPS-validated builds. Running on a FIPS-enabled RHEL 9 node may fail at JVM startup due to unsupported cipher suites. **Status: Unsupported on FIPS clusters.** Investigation with Neo4j EE FIPS support is a potential follow-on.

### Disconnected / Air-gapped
Neo4j CE images are published to **Docker Hub** (`docker.io/library/neo4j:<version>`). For disconnected clusters:
1. Mirror `neo4j:2026.06.0` to your internal registry (Quay, OpenShift internal registry, etc.)
2. Update `image.customImage` in values.yaml to point to the mirrored image
3. Ensure `imagePullSecrets` references a secret for the internal registry

No disconnected-specific image is provided by Neo4j; mirroring is the customer's responsibility.

### Licensing (Community vs Enterprise)
- CE: Apache 2.0 — no contract, no support SLA
- EE: Requires a commercial license from Neo4j, Inc. The Helm chart enforces `acceptLicenseAgreement: "yes"`. Using EE without a valid license violates the Neo4j EE EULA.

### Security Context Constraints
Neo4j **requires** the `anyuid` SCC (runs as UID 7474). It cannot run under `restricted-v2`. This is a fixed upstream constraint — adjusting the pod's UID is not supported by the Helm chart. Platform teams must explicitly grant `anyuid` to the neo4j service account.

### Auto-install / Lifecycle management by RHOAI
RHOAI (per platform policy overlay 0008) will **not** auto-install, upgrade, backup, or monitor Neo4j. All lifecycle operations are the customer's or platform admin's responsibility.

### Clustering / HA
Neo4j Community Edition is **single-node only**. Causal clustering (HA) requires Enterprise Edition and a commercial license.

### Apache AGE
AGE (PostgreSQL graph extension) is out of scope for this investigation. This runbook covers Neo4j only.

---

## Helm Chart Reference

| Parameter | Value used | Notes |
|---|---|---|
| `neo4j.name` | `my-standalone` | Sets the K8s resource name prefix |
| `neo4j.resources.cpu` | `4` | Request = limit (guaranteed QoS) |
| `neo4j.resources.memory` | `16Gi` | Request = limit |
| `image.imagePullSecrets` | `["dockerhub-pull-secret"]` | Plain strings — `name:` object format causes a template error |
| `env.NEO4J_PLUGINS` | `'["apoc"]'` | Triggers entrypoint to copy APOC Core jar from `/labs/` to `/plugins/` |
| `config.dbms.security.procedures.unrestricted` | `apoc.*` | Required for APOC procedures to be callable |
| `apoc_config` | see values file | APOC feature flags (triggers, file import, etc.) |
| `volumes.data.mode` | `dynamic` | Dynamic PVC provisioning |
| `volumes.data.dynamic.storageClassName` | `gp3-csi` | Replace with your cluster's RWO StorageClass |
| `neo4j.edition` | *(unset = community)* | Set to `enterprise` + `acceptLicenseAgreement: "yes"` for EE |

Full chart reference: `helm show values neo4j/neo4j`

---

## Validated Environment

| Component | Version |
|---|---|
| OpenShift | 4.21.18 |
| RHOAI | 3.5.0 (Self-Managed) |
| Neo4j Helm chart | neo4j-2026.6.0 |
| Neo4j image | neo4j:2026.06.0 (Community) |
| Cloud | ROSA (AWS), us-east-1 |
| StorageClass | gp3-csi |
| SCC | anyuid |
| Bolt connectivity | Confirmed (cypher-shell + Python driver) |
| APOC | Core 2026.06.0 (436 procedures) |

---

## Open Gaps and Recommendations

1. **TLS end-to-end**: Current validation uses plaintext Bolt. Production guidance should document the TLS values.yaml configuration and update the AutoRAG secret to use `bolt+s://`.
2. **FIPS**: Neo4j CE on FIPS nodes is untested and likely broken. If FIPS is a customer requirement, Neo4j EE with a FIPS-compatible JVM build must be evaluated.
3. **Disconnected**: Mirroring instructions for the Neo4j image should be included in the AutoRAG disconnected install guide.
4. **Backup/restore**: No PVC snapshot or `neo4j-admin` backup procedure is documented here. This is needed before production use.
5. **AutoRAG error messaging**: Confirm that the AutoRAG pipeline (`odh-autorag` runtime image) surfaces a clear user-facing error when Neo4j is unreachable. The Python `neo4j` driver raises `ServiceUnavailable` — AutoRAG should catch and report it without a cryptic stack trace.
6. **NetworkPolicy**: The validated deployment has no NetworkPolicy. A least-privilege policy should be part of the reference architecture for production.
