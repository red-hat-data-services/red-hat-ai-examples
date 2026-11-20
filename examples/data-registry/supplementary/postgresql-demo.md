# Demo PostgreSQL for Data Registry metadata

The Data Registry needs a reachable PostgreSQL database for its metadata. Use
an existing database if one is available. This supplementary setup provides a
small, single-instance PostgreSQL 16 database for trying the walkthrough on an
OpenShift cluster.

> **Demo use only:** This setup is not production ready. It has one database
> pod, no high availability, no backup or recovery process, no TLS
> configuration, and no production hardening. Use an organization-approved
> PostgreSQL service for production workloads.

The database is deployed in its own namespace and exposed only through an
internal ClusterIP Service. Its PVC keeps the demo database data across pod
restarts. The Data Registry connects to it from the `rhoai-data-registry`
namespace. If cluster NetworkPolicies isolate namespaces, allow the Data
Registry namespace to connect to TCP port 5432.

## Deploy the database

> **Who runs these steps:** Creating a namespace requires a cluster admin or
> user delegated project-creation permission. With the default OpenShift project
> request template, the requester receives project `admin`; that project admin
> (or a delegated user with the required permissions) creates the database
> Secret and deploys PostgreSQL.

You need `oc`, `openssl`, permission to create a namespace or use an existing
one, and a default dynamic StorageClass with at least 5 Gi available. The
manifest uses the OpenShift-oriented PostgreSQL 16 image from
[SCLorg](https://github.com/sclorg/postgresql-container); change the image to
an approved mirror if your cluster cannot pull from Quay.

These commands assume a new namespace. To reuse a namespace you control, set
`POSTGRES_NAMESPACE` to its name and skip the `oc new-project` command.

```bash
export POSTGRES_NAMESPACE=data-registry-postgres
oc new-project "$POSTGRES_NAMESPACE"
```

Generate a demo password and store the database settings in a Secret. The
password uses hexadecimal characters, which are safe in the registry's
PostgreSQL connection URI. The connection step below reloads it from this
Secret, so you can use a separate terminal. The commands do not print it.

```bash
set +x
POSTGRESQL_PASSWORD="$(openssl rand -hex 24)"
oc create -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: postgresql-demo-credentials
  namespace: ${POSTGRES_NAMESPACE}
type: Opaque
stringData:
  POSTGRESQL_USER: data_registry
  POSTGRESQL_PASSWORD: "${POSTGRESQL_PASSWORD}"
  POSTGRESQL_DATABASE: data_registry
EOF
unset POSTGRESQL_PASSWORD
```

From this `supplementary/` directory in the repository checkout, apply the
Deployment, PVC, and internal Service:

```bash
oc apply -n "$POSTGRES_NAMESPACE" -f postgresql-demo.yaml
oc rollout status deployment/postgresql-demo \
  -n "$POSTGRES_NAMESPACE" --timeout=5m
oc get deployment,pod,service,pvc -n "$POSTGRES_NAMESPACE" -o wide
```

Wait for the Deployment to become ready and the PVC to show `Bound`. The
internal service address is
`postgresql-demo.<namespace>.svc:5432`; for the default namespace above, use
`postgresql-demo.data-registry-postgres.svc` as the host.

## Configure the Data Registry connection

After enabling the Data Registry component in
[Step 1](../01-configure-data-registry/README.md), wait for the
`rhoai-data-registry` namespace to appear. This namespace is managed by RHOAI;
do not create it manually. A cluster admin or delegated user with permission
to read the database Secret and create `data-registry-database` in
`rhoai-data-registry` can perform this one-time handoff. RHOAI admin status or
`rhods-admins` membership alone does not grant those permissions.

The Secret stores the endpoint, database credentials, and Feast SQL
configuration. From a terminal logged in as the authorized user, reload the
original password from the database Secret. Use your database namespace if it
differs from the default below:

```bash
set -euo pipefail
set +x
export POSTGRES_NAMESPACE=data-registry-postgres
POSTGRESQL_PASSWORD="$(oc get secret postgresql-demo-credentials \
  -n "$POSTGRES_NAMESPACE" -o jsonpath='{.data.POSTGRESQL_PASSWORD}' \
  | openssl base64 -d -A)"

oc create -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: data-registry-database
  namespace: rhoai-data-registry
type: Opaque
stringData:
  POSTGRES_HOST: "postgresql-demo.${POSTGRES_NAMESPACE}.svc"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: data_registry
  POSTGRES_USER: data_registry
  POSTGRES_PASSWORD: "${POSTGRESQL_PASSWORD}"
  dsn: |
    path: postgresql+psycopg://\${POSTGRES_USER}:\${POSTGRES_PASSWORD}@\${POSTGRES_HOST}:\${POSTGRES_PORT}/\${POSTGRES_DB}
    cache_ttl_seconds: 60
EOF

unset POSTGRESQL_PASSWORD
```

The commands create Secrets and fail if either Secret already exists. Run
them once. If either Secret already exists, stop and use the matching database
credentials; generating a new password would leave the database and registry
with different credentials. Create the connection Secret only after Step 1
has created the `rhoai-data-registry` namespace, then return to Step 1 and
apply the FeatureStore manifest. The PostgreSQL service has no public Route;
the registry must be able to reach the service over the cluster network.

If the Deployment does not become ready, inspect its events and logs:

```bash
oc describe deployment/postgresql-demo -n "$POSTGRES_NAMESPACE"
oc logs deployment/postgresql-demo -n "$POSTGRES_NAMESPACE"
```

Keep the namespace and PVC while the Data Registry uses this database.
Deleting them may permanently delete this database and its Data Registry
metadata, depending on the storage reclaim policy.
