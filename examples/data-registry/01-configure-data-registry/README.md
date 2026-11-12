# Step 1: Configure the Data Registry in RHOAI 3.6

This step is for a cluster administrator. Enable the Data Registry component,
configure its metadata database, deploy an instance, and confirm the dashboard
is available. Then continue with [Step 2](../02-register-data-asset/README.md)
to register a data asset.

> **Technology Preview:** Technology Preview features are not supported with Red Hat production service-level agreements (SLAs), might not be functionally complete, and are not recommended for production. See the Red Hat support scope for Technology Preview features before using this example.

## How the registry is organized

The Data Registry stores metadata that helps people discover and understand data. It does not copy the data itself or store connection credentials.

```text
RHOAI project (authorization boundary)
└── Collection (optional organizational grouping)
    └── Asset (metadata about structured or unstructured data)
        ├── Location or path
        └── Optional reference to a RHOAI connection
```

An asset belongs to one RHOAI project and one collection. A user who can view registry resources in the project can view every asset and collection in that project. Collections organize metadata; they are not separate authorization boundaries.

## Prerequisites

You need:

- Red Hat OpenShift AI 3.6 installed on OpenShift;
- the `oc` command-line interface logged in to the cluster;
- cluster administrator access for enabling the Technology Preview component;
- a reachable PostgreSQL database for registry metadata; and
- permission to edit the RHOAI `DataScienceCluster` and dashboard configuration.

Project owners can follow Steps 2 and 3 after the administrator completes this step.

## Enable and deploy the Data Registry

### Enable the component

Find the `DataScienceCluster` resource used by your RHOAI installation:

```bash
oc get datasciencecluster
```

Edit that resource. The following example assumes its name is `default-dsc`:

```bash
oc edit datasciencecluster default-dsc
```

In the RHOAI 3.6 `DataScienceCluster` API, set the Data Registry management state to `Managed`:

```yaml
spec:
  components:
    data:
      dataRegistry:
        managementState: Managed
```

The Feature Store and Data Registry management states are independent. Do not change the Feature Store state unless you also intend to enable or disable that component.

Clusters upgraded from an earlier RHOAI release might expose the compatibility form below instead:

```yaml
spec:
  components:
    feastoperator:
      managementState: Managed
      dataRegistry:
        managementState: Managed
```

`managementState` is an enum such as `Managed` or `Removed`; it is not a `true` or `false` field. Check the custom resource definition installed on your cluster if neither form is accepted:

```bash
oc explain datasciencecluster.spec.components --recursive
```

### Enable the dashboard UI

The Data Registry backend and its dashboard UI are enabled separately. After
enabling the component, set `spec.dashboardConfig.dataRegistry` to `true` in
the Dashboard configuration custom resource. In the standard RHOAI 3.6
installation, the resource is named `odh-dashboard-config` in the
`redhat-ods-applications` namespace:

```bash
oc get odhdashboardconfig -n redhat-ods-applications

oc patch odhdashboardconfig odh-dashboard-config \
  -n redhat-ods-applications \
  --type=merge \
  -p '{"spec":{"dashboardConfig":{"dataRegistry":true}}}'
```

Verify that the setting is enabled before testing the dashboard:

```bash
oc get odhdashboardconfig odh-dashboard-config \
  -n redhat-ods-applications \
  -o jsonpath='{.spec.dashboardConfig.dataRegistry}{"\n"}'
```

The command should print `true`. If your installation uses a different
`OdhDashboardConfig` resource name, use the name returned by the `oc get`
command above. Changing the `DataScienceCluster` management state alone does
not make the Data Registry appear in the dashboard.

Wait for RHOAI to create the service namespace:

```bash
oc wait --for=jsonpath='{.status.phase}'=Ready datasciencecluster/default-dsc --timeout=10m
oc get namespace rhoai-data-registry
```

### Configure the metadata database

The registry requires PostgreSQL for its own metadata. Use an existing
reachable PostgreSQL service, or follow the
[supplementary demo PostgreSQL setup](../supplementary/postgresql-demo.md) to
create a single-instance database for evaluation. The demo setup is not
production ready. The registry can use the same PostgreSQL service as a Feast
Feature Store, but use a dedicated database and database user when possible.
This gives you clearer ownership, backup, lifecycle, and access boundaries
even when both databases share a PostgreSQL server.

For an existing PostgreSQL service, copy
[database-secret.example.yaml](database-secret.example.yaml), replace every
`CHANGE_ME` value, then apply it:

```bash
oc apply -f database-secret.example.yaml
```

If you use the supplementary demo database, its guide creates this same
Secret for you; skip the command above.

The Secret must be in the `rhoai-data-registry` namespace because the Data Registry workload reads it there. If the password contains reserved URI characters, URL-encode it before using it in the DSN. Never commit a Secret containing real credentials.

### Create the registry instance

Review [feature-store.yaml](feature-store.yaml), then create the instance:

```bash
oc apply -f feature-store.yaml
```

The fields that are specific to this setup are:

| Field | Purpose |
| --- | --- |
| `metadata.annotations[dataregistry.opendatahub.io/enabled]` | Marks this `FeatureStore` as the Data Registry instance. |
| `metadata.namespace` | Deploys the service in the RHOAI-managed Data Registry namespace. It is not the project in which assets are cataloged. |
| `services.registry.local.persistence` | Selects SQL persistence and the Secret key containing the registry DSN. |
| `services.registry.local.server.envFrom` | Makes the PostgreSQL values referenced by the DSN available to the server. |
| `services.onlineStore.disabled` | Avoids deploying a Feast online store, which the Data Registry does not use. |
| `authz.kubernetes` | Uses OpenShift authorization for project-scoped registry access. |

The remaining fields are standard `FeatureStore` configuration used by the Feast Operator.

### Verify the deployment

Wait for the `FeatureStore` to report `Ready`:

```bash
oc wait --for=jsonpath='{.status.phase}'=Ready \
  featurestore/data-registry -n rhoai-data-registry --timeout=10m

oc get featurestore/data-registry -n rhoai-data-registry
oc get deployments,pods,services,routes -n rhoai-data-registry
```

In the RHOAI dashboard, open **AI hub** and then **Data**. Confirm that you can select an RHOAI project and that the Data Registry page loads.

> **Screenshot to add:** RHOAI 3.6 **AI hub → Data** with the project selector and an empty registry. Capture a neutral project without hostnames, usernames, or customer data.

If the page does not load, first inspect the `FeatureStore` status and workload events:

```bash
oc describe featurestore/data-registry -n rhoai-data-registry
oc get events -n rhoai-data-registry --sort-by='.lastTimestamp'
```
