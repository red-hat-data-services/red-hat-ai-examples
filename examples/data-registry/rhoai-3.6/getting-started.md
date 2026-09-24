# Getting started with the Data Registry in RHOAI 3.6

The Data Registry is a Technology Preview feature in Red Hat OpenShift AI 3.6. Use this guide to:

1. enable and deploy a Data Registry instance;
2. organize and register a data asset; and
3. grant access to registry metadata without granting access to unrelated resources in the OpenShift project.

> **Technology Preview:** Technology Preview features are not supported with Red Hat production service-level agreements (SLAs), might not be functionally complete, and are not recommended for production. See the Red Hat support scope for Technology Preview features before using this example.

<!--
Maintainer note: before publishing this guide, validate the DataScienceCluster
snippets, generated ClusterRole names, navigation labels, and screenshots against
the final RHOAI 3.6 build. RHOAIENG-95346 was not merged when this draft was
written. Remove this comment after that validation.
-->

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
- an RHOAI project in which to register assets.

Creating assets and managing registry access do not require cluster administrator access when your existing project role permits those actions.

## 1. Enable and deploy the Data Registry

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

Wait for RHOAI to create the service namespace:

```bash
oc wait --for=jsonpath='{.status.phase}'=Ready datasciencecluster/default-dsc --timeout=10m
oc get namespace rhoai-data-registry
```

### Configure the metadata database

The registry requires PostgreSQL for its own metadata. It can use the same PostgreSQL service as a Feast Feature Store, but use a dedicated database and database user when possible. This gives you clearer ownership, backup, lifecycle, and access boundaries even when both databases share a PostgreSQL server.

Copy [database-secret.example.yaml](database-secret.example.yaml), replace every `CHANGE_ME` value, and apply it:

```bash
oc apply -f database-secret.example.yaml
```

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

> **Screenshot placeholder — registry landing page:** Replace this callout with a neutral RHOAI 3.6 screenshot showing **AI hub > Data**, the project selector, and an empty or non-sensitive registry. Do not include cluster hostnames, usernames, or customer data.

If the page does not load, first inspect the `FeatureStore` status and workload events:

```bash
oc describe featurestore/data-registry -n rhoai-data-registry
oc get events -n rhoai-data-registry --sort-by='.lastTimestamp'
```

## 2. Create a collection and register an asset

Select the RHOAI project that should own the metadata. The project is the authorization boundary: anyone with registry view access in the project can see all of its collections and assets.

### Decide whether to create a collection

Every asset is assigned to a collection. The default collection is useful for a quick trial. For metadata that will be shared, create a collection whose name reflects a stable data product, business domain, or lifecycle, for example `customer-orders` or `fraud-training-data`.

In **AI hub > Data**, select **Manage collections**, create a collection, and provide:

- a lowercase name containing letters, numbers, and hyphens, up to 63 characters;
- a short description that states what belongs in the collection; and
- an owner who can answer questions about the collection.

The owner is descriptive metadata. It does not grant permissions.

> **Screenshot placeholder — create collection:** Replace this callout with a neutral RHOAI 3.6 screenshot of the collection form with example values and no personal data.

### Register a data asset

Select **Register data** and describe the data you want people to discover. Saving the form registers metadata only: it does not upload, copy, sample, or validate the underlying data.

Use the fields as follows:

| Field | How to use it |
| --- | --- |
| Name | Use a stable, readable identifier such as `customer-orders-daily`. Names use lowercase letters, numbers, and hyphens and are limited to 63 characters. |
| Description | State what the data represents, its scope, important exclusions, and its update cadence. Avoid repeating the name. |
| Owner | Identify the team or person responsible for quality and access questions. This is metadata, not an RBAC rule. |
| Type and format | Choose structured data for tabular or schema-based data, or unstructured data for documents, images, audio, video, binary data, and similar content. Then select the closest format. |
| Collection | Group the asset with related assets in the same project. Collections do not change access. |
| Labels | Apply a small, agreed vocabulary for search and filtering, for example `domain=fraud` or `quality=verified`. Prefer consistent labels over spelling variants. |
| Connection | Optionally reference an existing RHOAI connection that applications can use to locate connection configuration. The registry stores a reference, not credential values. |
| Path | Record the location within the connected system, such as an object-storage prefix, table name, or URI. Keep the path separate from secrets. |
| Purpose | Explain the intended business or ML use and any prohibited uses. |
| License | Select the terms that govern reuse. Confirm the choice with the data owner rather than guessing. |
| Maturity | Set the lifecycle state: experimental, staging, production, or deprecated. Treat it as a maintained signal, not a one-time label. |
| PII status | Record whether the asset contains PII, sensitive data, anonymized data, or neither. This classification is informative and does not enforce access controls. |
| Custom properties | Add organization-specific key-value metadata such as `retention=365d` or `source-system=crm`. Never put passwords, tokens, or personal data in these fields. |
| Schema | For structured data, document field names, types, descriptions, and nullability. The registry does not inspect the source to verify that the declared schema is accurate. |

For a first asset, you might use:

```text
Name: customer-orders-daily
Description: Daily order line items from the commerce platform, retained for model training and revenue analysis.
Owner: data-platform
Type / format: Structured / Parquet
Collection: customer-orders
Labels: domain=commerce, cadence=daily
Path: s3://example-data/curated/orders/daily/
Purpose: Training and evaluation of demand forecasting models
License: Internal use
Maturity: Staging
PII status: Contains PII
```

Select a connection only when the asset has a physical location that should be resolved through existing RHOAI connection configuration. Registering the reference neither reveals its Secret values in the registry nor grants a user permission to read the physical data. Storage authorization remains a separate responsibility.

> **Screenshot placeholder — register data:** Replace this callout with neutral RHOAI 3.6 screenshots showing the basic details and metadata sections of the registration form. Use fictional locations and owners.

After saving, verify that the asset appears in the selected project and collection, and open its details page to review the recorded metadata. A successful save proves that the metadata was registered; it does not prove that the underlying path exists, credentials work, or the schema matches the data.

## 3. Grant project-scoped registry access

The Data Registry uses OpenShift RBAC in the project where the assets are registered. Standard OpenShift project `view`, `edit`, and `admin` access is aggregated with the corresponding registry permissions. A user who already has one of those roles does not need an additional registry RoleBinding.

When a user or group needs access to registry metadata but must not receive broad access to other project resources, create a RoleBinding in that project to one of the Data Registry ClusterRoles:

| ClusterRole | Registry access |
| --- | --- |
| `data-registry-viewer` | List, view, and watch registry resources. |
| `data-registry-editor` | Create, update, and delete registry resources. |
| `data-registry-admin` | Editor access plus use of referenced RHOAI connections. |

These ClusterRoles are installed and maintained by the operator. Do not edit them or create a duplicate namespaced Role. A namespaced RoleBinding limits the ClusterRole grant to Data Registry resources in the selected project.

For reference, the generated viewer ClusterRole is equivalent to this abbreviated YAML. Inspect the installed role on your cluster for the authoritative rules; do not apply this snippet:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: data-registry-viewer
rules:
  - apiGroups:
      - dataregistry.opendatahub.io
    resources:
      - registries
      - namespaces
      - tables
      - volumes
      - generic-tables
    verbs:
      - get
      - list
      - watch
```

Replace the example values and grant viewer access to a user:

```bash
oc adm policy add-role-to-user data-registry-viewer \
  example-user -n example-project
```

Or grant it to a group:

```bash
oc adm policy add-role-to-group data-registry-viewer \
  example-group -n example-project
```

Equivalent declarative examples are provided for a [user](rbac/viewer-user-rolebinding.yaml) and a [group](rbac/viewer-group-rolebinding.yaml). Change the project, subject, and role to match the intended access before applying them.

Verify that the subject can view registry assets:

```bash
oc auth can-i --as=example-user get \
  generic-tables.dataregistry.opendatahub.io -n example-project
```

If the user is supposed to have registry-only access, also check a resource outside the registry:

```bash
oc auth can-i --as=example-user get secrets -n example-project
```

The second command should return `no` only when no other RoleBinding grants that permission. OpenShift permissions are additive, so the registry-only RoleBinding cannot remove access granted elsewhere.

Registry access controls metadata. It does not grant access to the underlying object store, database, or other physical data system. Configure and audit that access independently.

## Where to go next

After completing this guide, consider documenting or automating:

- an organization-wide labeling and ownership convention;
- API-based registration and metadata synchronization;
- asset lifecycle, deprecation, and deletion procedures;
- storage and connection access alongside registry RBAC; and
- database backup, restore, and disaster recovery for registry metadata.
