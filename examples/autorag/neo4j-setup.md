# Neo4j on Red Hat OpenShift AI — Installation and Configuration Runbook

**Status**: Validated against the `neo4j` namespace deployment on OpenShift 4.21 / RHOAI 3.5.0 (ROSA, us-east-1), including encrypted Bolt and HTTPS.
**Scope**: Customer/admin-provisioned Neo4j as a prerequisite for AutoRAG GraphRAG workloads

---

## Overview

Neo4j is the graph database used by AutoRAG's GraphRAG capability (`BaseVectorStore` + Neo4j adapter). RHOAI does **not** auto-install or lifecycle-manage Neo4j — it is a customer- or platform-admin-provisioned prerequisite. This runbook documents the install path, TLS-enabled connectivity validation, sizing guidance, and known constraints.

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
- cert-manager installed on the cluster; a cluster administrator is required when creating or selecting a `ClusterIssuer`

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

### 5. TLS certificate source

This runbook uses cert-manager to maintain the `neo4j-server-tls` Secret. It contains `tls.crt`, `tls.key`, and, when provided by the issuer, `ca.crt`. Neo4j mounts the certificate for both Bolt and HTTPS. Clients use the CA certificate to verify the server certificate.

cert-manager and a `ClusterIssuer` or namespaced `Issuer` are required. The steps below use `ClusterIssuer/selfsigned-issuer` for an internal evaluation deployment. For production, replace it with an organization or public CA issuer and configure clients to trust its CA. Do not use `bolt+ssc://`: it accepts a self-signed certificate without verifying its trust chain.

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

### Step 3 — Verify or create the cert-manager issuer

Check that cert-manager is installed and that the evaluation issuer exists:

```bash
oc get crd certificates.cert-manager.io
oc get clusterissuer selfsigned-issuer
```

If `selfsigned-issuer` does not exist, a cluster administrator can create it:

```bash
oc apply -f - <<'EOF'
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned-issuer
spec:
  selfSigned: {}
EOF
```

> For production, do not create this self-signed issuer. Obtain the name and kind of the organization-approved issuer from the platform team, then substitute it in Step 4.

### Step 4 — Create the cert-manager Certificate

Apply this before installing the Helm release so the keypair Secret exists when the Neo4j pod starts.

```bash
oc apply -f - <<'EOF'
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: neo4j-server-tls
  namespace: neo4j
spec:
  secretName: neo4j-server-tls
  commonName: autorag-neo4j.neo4j.svc.cluster.local
  dnsNames:
    - autorag-neo4j.neo4j.svc
    - autorag-neo4j.neo4j.svc.cluster.local
  duration: 2160h
  renewBefore: 360h
  privateKey:
    algorithm: RSA
    size: 2048
  usages:
    - server auth
    - client auth
  issuerRef:
    kind: ClusterIssuer
    name: selfsigned-issuer
EOF

# Confirm cert-manager issued the TLS Secret.
oc wait --for=condition=Ready certificate/neo4j-server-tls -n neo4j --timeout=2m
oc describe secret neo4j-server-tls -n neo4j
# Expected keys: ca.crt, tls.crt, tls.key
```

### Step 5 — Create values file

Save as `neo4j.values.yaml`:

```yaml
neo4j:
  name: my-standalone
  resources:
    cpu: "4"
    memory: 16Gi
  # Uncomment to set a specific initial password (otherwise auto-generated)
  # password: "ChangeMe-8c^4&1-383F4f8"

image:
  # Note: must be plain strings, not name: key objects
  imagePullSecrets:
    - "dockerhub-pull-secret"

  # Uncomment for Enterprise edition (requires Neo4j license)
  # edition: "enterprise"
  # acceptLicenseAgreement: "yes"

env:
  NEO4J_PLUGINS: '["apoc"]'

apoc_config:
  apoc.trigger.enabled: "true"
  apoc.import.file.enabled: "true"

volumes:
  data:
    mode: "dynamic"
    dynamic:
      storageClassName: gp3-csi   # Adjust to your cluster's RWO StorageClass

# Mount the cert-manager Secret for Bolt and HTTPS.
additionalVolumes:
  - name: neo4j-bolt-certs
    secret:
      secretName: neo4j-server-tls
      items:
        - key: tls.crt
          path: public.crt
        - key: tls.key
          path: private.key
  - name: neo4j-https-certs
    secret:
      secretName: neo4j-server-tls
      items:
        - key: tls.crt
          path: public.crt
        - key: tls.key
          path: private.key

additionalVolumeMounts:
  - name: neo4j-bolt-certs
    mountPath: /var/lib/neo4j/certificates/bolt
    readOnly: true
  - name: neo4j-https-certs
    mountPath: /var/lib/neo4j/certificates/https
    readOnly: true

config:
  dbms.security.procedures.unrestricted: "apoc.*"
  dbms.ssl.policy.bolt.base_directory: certificates/bolt
  dbms.ssl.policy.bolt.enabled: "true"
  dbms.ssl.policy.bolt.private_key: private.key
  dbms.ssl.policy.bolt.public_certificate: public.crt
  dbms.ssl.policy.https.base_directory: certificates/https
  dbms.ssl.policy.https.enabled: "true"
  dbms.ssl.policy.https.private_key: private.key
  dbms.ssl.policy.https.public_certificate: public.crt
  server.bolt.tls_level: OPTIONAL
  server.https.enabled: "true"
```

> After cert-manager renews or reissues `neo4j-server-tls`, restart Neo4j so it loads the new certificate:
>
> ```bash
> oc rollout restart statefulset/autorag-neo4j -n neo4j
> oc rollout status statefulset/autorag-neo4j -n neo4j --timeout=5m
> ```

### Step 6 — Install via Helm

```bash
helm install autorag-neo4j neo4j/neo4j \
  --namespace neo4j \
  --values neo4j.values.yaml \
  --wait --timeout 5m
```

Expected result: `STATUS: deployed` and pod `autorag-neo4j-0` in `Running` state.

### Step 7 — Verify deployment and TLS

```bash
# Pod running
oc get pod autorag-neo4j-0 -n neo4j

# PVC bound (100Gi gp3-csi)
oc get pvc -n neo4j

# Services created
oc get svc -n neo4j

# The chart mounts each Neo4j setting as a file in this projected directory.
# Confirm Bolt and HTTPS TLS are enabled.
oc exec autorag-neo4j-0 -n neo4j -- sh -c '\
  for setting in \
    server.bolt.tls_level \
    dbms.ssl.policy.bolt.enabled \
    dbms.ssl.policy.https.enabled \
    server.https.enabled; do
      printf "%s=" "$setting"
      cat "/config/neo4j.conf/$setting"
      printf "\n"
  done'
# Expected:
# server.bolt.tls_level=OPTIONAL
# dbms.ssl.policy.bolt.enabled=true
# dbms.ssl.policy.https.enabled=true
# server.https.enabled=true
```

Expected services:

| Service | Type | Ports | Purpose |
|---|---|---|---|
| `autorag-neo4j` | ClusterIP | 7687, 7474 | Primary app access (Bolt + HTTP) |
| `autorag-neo4j-admin` | ClusterIP | 7687, 7474 | Admin/monitoring access |
| `my-standalone-lb-neo4j` | LoadBalancer | 7474, 7473, 7687 | External client access |

### Step 8 — Add the LoadBalancer hostname to the certificate (optional)

The certificate initially covers only the in-cluster Service DNS names. Complete this step only when clients connect through the external LoadBalancer. Add its hostname as a certificate SAN, wait for certificate reissuance, then restart Neo4j so it reads the renewed Secret.

```bash
NEO4J_LB_HOST=$(oc get svc my-standalone-lb-neo4j -n neo4j \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
test -n "${NEO4J_LB_HOST}"

oc patch certificate neo4j-server-tls -n neo4j --type=json \
  -p="[{\"op\":\"add\",\"path\":\"/spec/dnsNames/-\",\"value\":\"${NEO4J_LB_HOST}\"}]"
oc wait --for=condition=Ready certificate/neo4j-server-tls -n neo4j --timeout=2m
oc rollout restart statefulset/autorag-neo4j -n neo4j
oc rollout status statefulset/autorag-neo4j -n neo4j --timeout=5m
```

Run this once after the LoadBalancer receives its hostname. If the Certificate already contains the hostname, do not patch it again. For a production issuer, ensure its certificate policy permits the LoadBalancer DNS name.

### Step 9 — Verify APOC

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

# Use ca.crt when cert-manager provides it; a self-signed leaf is its own
# trust certificate, so tls.crt is the safe fallback.
NEO4J_CA_DATA=$(oc get secret neo4j-server-tls -n neo4j \
  -o jsonpath='{.data.ca\.crt}')
if [ -z "${NEO4J_CA_DATA}" ]; then
  NEO4J_CA_DATA=$(oc get secret neo4j-server-tls -n neo4j \
    -o jsonpath='{.data.tls\.crt}')
fi
printf '%s' "${NEO4J_CA_DATA}" | base64 -d > neo4j-ca.crt

oc create secret generic neo4j-bolt-credentials \
  --from-literal=NEO4J_URI="bolt://autorag-neo4j.neo4j.svc.cluster.local:7687" \
  --from-literal=NEO4J_USERNAME="neo4j" \
  --from-literal=NEO4J_PASSWORD="${NEO4J_PASSWORD}" \
  --from-file=NEO4J_CA_CERT=neo4j-ca.crt \
  -n <autorag-namespace>
rm neo4j-ca.crt
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
volumeMounts:
  - name: neo4j-ca
    mountPath: /var/run/secrets/neo4j
    readOnly: true
volumes:
  - name: neo4j-ca
    secret:
      secretName: neo4j-bolt-credentials
      items:
        - key: NEO4J_CA_CERT
          path: ca.crt
```

---

## Connectivity Validation

### From an AutoRAG pipeline task pod (KFP workload)

After mounting `neo4j-bolt-credentials` as shown above, run this from a pipeline task image that includes the `neo4j` Python package. The live deployment uses a self-signed certificate. The Neo4j Python driver only permits a custom CA with the base `bolt://` or `neo4j://` scheme; set `encrypted=True` and provide `TrustCustomCAs`. This encrypts traffic and verifies the certificate chain and service hostname.

```python
import os

from neo4j import GraphDatabase, TrustCustomCAs

driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    encrypted=True,
    trusted_certificates=TrustCustomCAs("/var/run/secrets/neo4j/ca.crt"),
)
with driver.session() as session:
    assert session.run("RETURN 1 AS test").single()["test"] == 1
driver.close()
```

This validates the actual consumer namespace and task image. If the CA is already installed in the workload's system trust store, `bolt+s://` may be used without `encrypted` or `trusted_certificates`. AutoRAG must mount and configure `NEO4J_CA_CERT` (or otherwise trust the issuer) before it can use this self-signed certificate securely.

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

Verify the certificate chain and service hostname (this command returned `Verification: OK` and `Verify return code: 0 (ok)` on the live deployment):

```bash
oc exec autorag-neo4j-0 -n neo4j -- sh -c '\
  openssl s_client \
    -connect autorag-neo4j.neo4j.svc.cluster.local:7687 \
    -servername autorag-neo4j.neo4j.svc.cluster.local \
    -verify_hostname autorag-neo4j.neo4j.svc.cluster.local \
    -CAfile /var/lib/neo4j/certificates/bolt/public.crt \
    </dev/null 2>&1 | grep -E "Verification: OK|Verify return code: 0 \(ok\)"'
```

The Python-driver check above is the recommended end-to-end validation from the consumer namespace because it verifies TLS negotiation, authentication, and a Cypher query.

---

## Networking

### In-cluster Bolt connection

```
bolt://autorag-neo4j.neo4j.svc.cluster.local:7687
```

Use `bolt://<service-name>.<namespace>.svc.cluster.local:7687` only together with `encrypted=True` and `TrustCustomCAs(NEO4J_CA_CERT)`, as shown above. The bare URI does **not** enable encryption itself. The certificate contains this service DNS name as a SAN.

### External Bolt connection

After completing [Step 8](#step-8--add-the-loadbalancer-hostname-to-the-certificate), use the LoadBalancer hostname with the same Python driver settings:

```text
bolt://<load-balancer-hostname>:7687
```

Keep `encrypted=True` and `TrustCustomCAs` configured with the issued CA. The LoadBalancer hostname must be present in the certificate SANs or hostname verification will fail.

### HTTP Browser UI

After completing [Step 8](#step-8--add-the-loadbalancer-hostname-to-the-certificate), open:

```text
https://<load-balancer-hostname>:7473
```

The Browser UI uses the same certificate as Bolt. Import the issuing CA into the browser or operating-system trust store before opening it; otherwise the browser will correctly report the self-signed certificate as untrusted. Do not use the plaintext HTTP port (`7474`) outside the cluster.

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

### TLS / Bolt

The live installation mounts `neo4j-server-tls` at `/var/lib/neo4j/certificates/bolt` and `/var/lib/neo4j/certificates/https`. It enables both TLS policies and HTTPS. `server.bolt.tls_level: OPTIONAL` permits both encrypted and plaintext Bolt; AutoRAG must set `encrypted=True` and trust the supplied certificate to use verified encryption.

To enforce encrypted Bolt after migrating all clients, set `server.bolt.tls_level: REQUIRED` and upgrade the release. Distribute the issuing CA to every client.

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

1. A running Neo4j instance reachable from the AutoRAG pipeline namespace via TLS-enabled Bolt (TCP 7687)
2. A Kubernetes Secret in the AutoRAG namespace containing `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, and `NEO4J_CA_CERT`; the client must set `encrypted=True` and `TrustCustomCAs` as shown above
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
| `neo4j.resources.cpu` | `4` | Matches the live request and limit |
| `neo4j.resources.memory` | `16Gi` | Matches the live request and limit |
| `image.imagePullSecrets` | `["dockerhub-pull-secret"]` | Plain strings — `name:` object format causes a template error |
| `env.NEO4J_PLUGINS` | `'["apoc"]'` | Triggers entrypoint to copy APOC Core jar from `/labs/` to `/plugins/` |
| `config.dbms.security.procedures.unrestricted` | `apoc.*` | Required for APOC procedures to be callable |
| `apoc_config` | see values file | APOC feature flags (triggers, file import, etc.) |
| `volumes.data.mode` | `dynamic` | Dynamic PVC provisioning |
| `volumes.data.dynamic.storageClassName` | `gp3-csi` | Replace with your cluster's RWO StorageClass |
| `additionalVolumes` | `neo4j-server-tls` Secret | Mounts `tls.crt` and `tls.key` for Bolt and HTTPS |
| `config.dbms.ssl.policy.*.enabled` | `true` | Enables both Bolt and HTTPS TLS policies |
| `config.server.bolt.tls_level` | `OPTIONAL` | Matches the live deployment; set `REQUIRED` to reject plaintext Bolt |
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
| TLS / Bolt connectivity | Confirmed: TLS chain and service-hostname verification succeeded |
| APOC | Core 2026.06.0 (436 procedures) |

---

## Open Gaps and Recommendations

1. **Enforce TLS**: The current deployment accepts plaintext Bolt (`OPTIONAL`) for compatibility. Move to `REQUIRED` once all clients use TLS.
2. **FIPS**: Neo4j CE on FIPS nodes is untested and likely broken. If FIPS is a customer requirement, Neo4j EE with a FIPS-compatible JVM build must be evaluated.
3. **Disconnected**: Mirroring instructions for the Neo4j image should be included in the AutoRAG disconnected install guide.
4. **Backup/restore**: No PVC snapshot or `neo4j-admin` backup procedure is documented here. This is needed before production use.
5. **AutoRAG error messaging**: Confirm that the AutoRAG pipeline (`odh-autorag` runtime image) surfaces a clear user-facing error when Neo4j is unreachable. The Python `neo4j` driver raises `ServiceUnavailable` — AutoRAG should catch and report it without a cryptic stack trace.
6. **NetworkPolicy**: The validated deployment has no NetworkPolicy. A least-privilege policy should be part of the reference architecture for production.
