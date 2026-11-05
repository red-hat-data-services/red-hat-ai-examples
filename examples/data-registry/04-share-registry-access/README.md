# Step 4: Share project-scoped registry access

[← Step 3: Use the API](../03-use-registry-api/README.md) · [Guide index](../README.md)

This step preserves the existing project-scoped access guidance. A fuller sharing workflow will follow.

## Grant project-scoped registry access

The Data Registry uses OpenShift RBAC in the project where the assets are registered. Standard OpenShift project `view`, `edit`, and `admin` access is aggregated with the corresponding registry permissions. A user who already has one of those roles does not need an additional registry RoleBinding.

When a user or group needs access to registry metadata but must not receive broad access to other project resources, create a RoleBinding in that project to one of the Data Registry ClusterRoles:

| ClusterRole | Registry access |
| --- | --- |
| `feast-data-registry-viewer` | List, view, and watch registry resources. |
| `feast-data-registry-editor` | Create, update, and delete registry resources. |
| `feast-data-registry-admin` | Editor access plus use of referenced RHOAI connections. |

These ClusterRoles are installed and maintained by the operator. Do not edit them or create a duplicate namespaced Role. A namespaced RoleBinding limits the ClusterRole grant to Data Registry resources in the selected project.

The `feast-data-registry-*` names were verified on an RHOAI 3.6 cluster. Check
`oc get clusterrole | grep feast-data-registry` on your installed build before
creating a RoleBinding; the installed role is authoritative.

For reference, the generated viewer ClusterRole is equivalent to this abbreviated YAML. Inspect the installed role on your cluster for the authoritative rules; do not apply this snippet:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: feast-data-registry-viewer
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
oc adm policy add-role-to-user feast-data-registry-viewer \
  example-user -n example-project
```

Or grant it to a group:

```bash
oc adm policy add-role-to-group feast-data-registry-viewer \
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
