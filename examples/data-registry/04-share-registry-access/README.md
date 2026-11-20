# Step 4 (optional): Share Data Registry assets

[← Step 3: Use the Data Registry API](../03-use-registry-api/README.md) ·
[Guide index](../README.md)

**Minimum persona:** An **RHOAI user** with project `admin` permissions in the
project containing the assets.

This optional step explores sharing after Steps 2 and 3. The collection and
assets belong to the `data-registry-example` project. You can share the assets
through a person's **project role**, or grant access to **Data Registry assets
only**. Choose based on whether that person also needs access to other resources
in the project. If you followed the optional
[sample users and roles guide](../supplementary/users-and-roles.md), use
`rhoai-user-data-curator` as the person granting access and
`rhoai-user-recipient` as the recipient. Otherwise, use your own RHOAI user
with project `admin` permissions as the grantor and another RHOAI user as the
recipient; replace `rhoai-user-recipient` in the commands below with that
user's username.

## Who applies the grants

Run the grant and revoke commands as an **OpenShift project administrator**
in `data-registry-example`. With the sample accounts, this is
`rhoai-user-data-curator`, which received project `admin` when it created the
project in Step 2. Use the recipient's own session only for verification.

For group examples, replace `example-group` with an existing OpenShift group
and verify as one of its members. Group provisioning is outside this step.

Use unused RoleBinding names for these tests; choose new names if an example
name is already occupied. Preserve existing bindings when resetting access.

| Step 4 action | Who can apply it |
| --- | --- |
| Grant project `view` or `admin` in Option 1 | A user with project `admin` in the target project. |
| Bind `feast-data-registry-viewer` or `feast-data-registry-admin` in Option 2 | A user with project `admin` in the target project, with the registry roles already installed. |
| Create and bind the project-discovery Role | A user with project `admin` in the target project. |
| Create, bind, or revoke the optional Secret-list Role | A user with project `admin` in the target project, after accepting the credential-read scope described below. |

A cluster administrator can also perform these actions, but cluster-admin
access is not required for the namespaced grants in this step. **RHOAI
administrator status alone is not sufficient**: that user also needs the
necessary OpenShift permissions in the target project. Similarly,
`feast-data-registry-admin` grants catalog management, not permission to
create Roles or RoleBindings or share access with another user.

The table describes the tested installation. A more narrowly delegated user
can also perform a particular action when explicitly authorized. Kubernetes
requires permission to manage the relevant Role or RoleBinding and prevents
granting permissions the grantor does not hold, unless explicitly delegated
through `bind` or `escalate`. See the
[Kubernetes RBAC delegation rules](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#privilege-escalation-prevention-and-bootstrapping).

The operator-provided registry ClusterRoles must already exist from the
registry setup. Installing or changing cluster-scoped roles belongs to
platform setup and is outside Step 4; the commands below create only
namespace-scoped Roles and RoleBindings.

## Option 1: Share the whole project

On the RHOAI 3.6 installation used for this guide, Data Registry permissions
are included in the standard OpenShift project roles:

| Project role | Data Registry access inherited | Scope of the grant |
| --- | --- | --- |
| `view` | View collections and assets. | Read access to other project resources allowed by the project role. |
| `admin` | View, create, update, and delete collections and assets. | Administration of other project resources as well. |

For example, if a teammate already has `view` in `data-registry-example`, they
can view its Data Registry assets without another RoleBinding. An RHOAI user
with project `admin` permissions can manage those assets and grant project
access to another RHOAI user by running **one** of these commands:

```bash
# Give the RHOAI user project-wide read access, including Data Registry assets.
oc adm policy add-role-to-user view rhoai-user-recipient -n data-registry-example \
  --rolebinding-name=data-registry-project-view-recipient

# Or give the RHOAI user project-wide administration, including Data Registry
# assets.
oc adm policy add-role-to-user admin rhoai-user-recipient -n data-registry-example \
  --rolebinding-name=data-registry-project-admin-recipient
```

For a group, use the matching command:

```bash
oc adm policy add-role-to-group view example-group -n data-registry-example \
  --rolebinding-name=data-registry-project-view-example-group

# Or, for project-wide administration:
oc adm policy add-role-to-group admin example-group -n data-registry-example \
  --rolebinding-name=data-registry-project-admin-example-group
```

Project roles affect more than Data Registry, so use this option when the
person needs the corresponding access to the project as a whole.

## Option 2: Share Data Registry access

Start with catalog access and project discovery. These grants allow the
recipient to select the project and use the catalog without granting access
to its workbenches, pods, or Secret contents. Then decide separately whether
to enable connection discovery and selection with the optional Secret-list
grant below.

The catalog and project-discovery behavior in this section was verified on
RHOAI 3.6 with OpenShift 4.22.23 on 20 November 2026. Check the recipient's
effective permissions and actual dashboard behavior on your installation.

### 1. Choose the catalog permissions

If a teammate needs the catalog but should not receive broad access to other
resources in `data-registry-example`, bind one of the operator-provided Data
Registry ClusterRoles **in that project**:

| Data Registry ClusterRole | Access within `data-registry-example` | Connection access from this role |
| --- | --- | --- |
| `feast-data-registry-viewer` | View collections and assets. | Read the connection reference stored on an asset. No Secret read or write grant. |
| `feast-data-registry-admin` | View, create, update, and delete collections and assets. | Also change or clear an asset's connection reference. No Secret read or write grant. |

A connection reference records the connection type and identifier. For this
walkthrough, it identifies the Secret named `data-registry-storage`. Reading
that reference does not return the connection's credentials. Changing an asset's
reference does not edit the connection's endpoint, bucket, or credentials.
Neither registry role grants permission to change the underlying connection
Secret. The admin role's `use` permission on the virtual registry
`connections` resource does not grant Kubernetes Secret access.

For an RHOAI user, select the level of access and run **one** command:

```bash
# Let the RHOAI user view Data Registry assets in this project.
oc adm policy add-role-to-user feast-data-registry-viewer \
  rhoai-user-recipient -n data-registry-example \
  --rolebinding-name=data-registry-viewer-recipient

# Or let the RHOAI user manage Data Registry assets in this project.
oc adm policy add-role-to-user feast-data-registry-admin \
  rhoai-user-recipient -n data-registry-example \
  --rolebinding-name=data-registry-admin-recipient
```

For a group, use the matching group command:

```bash
oc adm policy add-role-to-group feast-data-registry-viewer \
  example-group -n data-registry-example \
  --rolebinding-name=data-registry-viewer-example-group

# Or, for people who should manage the registry assets:
oc adm policy add-role-to-group feast-data-registry-admin \
  example-group -n data-registry-example \
  --rolebinding-name=data-registry-admin-example-group
```

Equivalent RoleBinding examples are provided for a [viewer user](rbac/viewer-user-rolebinding.yaml),
[viewer group](rbac/viewer-group-rolebinding.yaml),
[admin user](rbac/admin-user-rolebinding.yaml), and
[admin group](rbac/admin-group-rolebinding.yaml). Replace the example subject
and project before applying a manifest. The RoleBinding grants the selected
ClusterRole only within its namespace; it does not change the operator-managed
ClusterRole or grant project-wide administration.

These roles cover Data Registry resources **throughout the selected project**.
They do not select individual collections or assets. OpenShift permissions are
additive: a Data Registry RoleBinding cannot remove access that the RHOAI user
already has through a project role or another binding.

### 2. Allow the project to appear in the selector

On the tested installation, the registry role alone allowed direct catalog
requests but left the Data Registry project dropdown empty. Add the
[project-discovery Role](rbac/project-discovery-role.yaml), which grants only
`get` on the named namespace's metadata, and bind it to the recipient:

Run the manifest commands from this guide's `04-share-registry-access/`
directory in your checkout.

```bash
oc apply -f rbac/project-discovery-role.yaml

oc create rolebinding data-registry-project-discovery-recipient \
  --role=data-registry-project-discovery \
  --user=rhoai-user-recipient -n data-registry-example \
  --dry-run=client -o yaml | oc apply -f -
```

For a group, use a distinct binding name and replace
`--user=rhoai-user-recipient` with `--group=example-group`.

This namespace-scoped Role works with OpenShift's project-visibility check,
which evaluates `get namespaces` within the named namespace. It does not
grant cluster-wide namespace listing or access to resources inside the
project. If using another project, update both `metadata.namespace` and
`rules[].resourceNames` in the manifest, and the command's namespace.
See the [OpenShift project-visibility implementation](https://github.com/openshift/openshift-apiserver/blob/release-4.22/pkg/project/auth/reviewer.go).

### 3. Optional: view connections and select one for an asset

Use this additional grant only when the recipient should discover the
project's Secret-backed connections. A registry viewer can then see the
available connections; a registry admin can select a different connection
when registering or editing an asset. The additional Role grants no
permission to edit the underlying connection Secret.

Without this grant, catalog reads and the stored connection reference remain
available. On the tested installation, the connection-list API returned
`403`, the dashboard showed **Unable to load connections** and **Connection
unavailable**, and the connection selector was disabled. A registry admin
could still set a known connection reference through the catalog API.

> **Security decision — permission to read project Secret contents:** The
> current Secret-backed connection lookup lists Kubernetes Secrets using the
> caller's token. Granting `list secrets` allows the recipient to read the
> complete contents of **all Secrets in this project**, including credentials
> and Secrets unrelated to connections. It is not limited to names or
> dashboard-filtered connections. An individual `get secret` can remain
> forbidden while a list response still exposes the values. Grant this only
> if that credential-read access is acceptable for the recipient.

Kubernetes documents that Secret list responses include Secret contents in
[Authorization](https://kubernetes.io/docs/reference/access-authn-authz/authorization/).
Credentials read from a Secret may authorize access to the underlying data
source, independently of the user's catalog permissions.

If you accept that scope, apply the
[Secret-list Role](rbac/connection-secret-list-role.yaml) and bind it to the
recipient. These commands grant only `list`; they do not add `get`, `watch`,
`create`, `patch`, `update`, or `delete` on Secrets:

```bash
oc apply -f rbac/connection-secret-list-role.yaml

oc create rolebinding data-registry-connection-secret-list-recipient \
  --role=data-registry-connection-secret-list \
  --user=rhoai-user-recipient -n data-registry-example \
  --dry-run=client -o yaml | oc apply -f -
```

For a group, use a distinct binding name and replace the `--user` option with
`--group=example-group`. These are additional permissions alongside the chosen
registry role and project-discovery binding. With this optional grant, access
includes project credential reads as well as catalog access.

## Verify the result

Use a separate CLI session authenticated as the **recipient** to inspect its
own effective rules. Project `admin` does not itself grant permission to
impersonate another user with `--as`.

```bash
oc whoami
oc get projects
oc auth can-i --list -n data-registry-example
```

Confirm the expected username and project visibility, then look for the
`dataregistry.opendatahub.io` rules. In the recipient's dashboard session,
open **AI hub → Data**, select the project, and open a collection and asset.
Verify that a viewer's catalog writes return `403` and that a registry admin
can create, update, and remove a disposable catalog entry.

For Option 2, also check the boundaries without displaying Secret values:

```bash
oc auth can-i get pods -n data-registry-example
oc auth can-i get notebooks.kubeflow.org -n data-registry-example
oc auth can-i list secrets -n data-registry-example
oc auth can-i get secrets -n data-registry-example
oc auth can-i patch secrets -n data-registry-example
```

With no other grants, pod, workbench, individual Secret reads, and Secret
patch checks should return `no`. Secret listing should return `no` for the
catalog-only setup and `yes` only if you chose the optional credential-read
grant. A `no` result for `get secrets` does **not** establish confidentiality
when `list secrets` is allowed.

Some `oc` versions cannot check Data Registry's virtual resources directly
with `oc auth can-i`; the effective rule list and an actual Data Registry
request are more reliable checks. Authorization caches can delay the effect
of grants and revocations, so recheck actual requests after permissions have
propagated. A successful RoleBinding deletion alone does not prove that an
existing session has lost access. Check both reads and writes with the
recipient's existing session: a cached write decision can outlive a read
decision. Use disposable records for mutation checks, remove them, and confirm
denial before testing another role.

On the tested dashboard, viewers still saw write controls even though the
API rejected their writes. Changing a connection reference through the API
also accepted a nonexistent connection name: a successful catalog save does
not verify connection existence, credentials, or connectivity.

The registry roles control catalog access. Access to the underlying S3 objects or
other data sources depends on their own credentials and policies. The
optional Secret-list grant can expose those credentials; review that
additional access explicitly when sharing an asset or its project.

## Reset after verifying each option

To revoke only this example user's optional Secret-list grant:

```bash
oc delete rolebinding data-registry-connection-secret-list-recipient \
  -n data-registry-example
```

The registry and project-discovery bindings remain in place. Review other
bindings too: removing this binding does not remove permissions granted
elsewhere.

To reset a project or registry role test, delete the RoleBinding created for
that choice. The example commands use separate names:

| Grant tested | RoleBinding to remove |
| --- | --- |
| Project `view` | `data-registry-project-view-recipient` |
| Project `admin` | `data-registry-project-admin-recipient` |
| Registry viewer | `data-registry-viewer-recipient` |
| Registry admin | `data-registry-admin-recipient` |

```bash
# Set this to the binding from your completed test.
BINDING=data-registry-project-view-recipient
oc delete rolebinding "$BINDING" -n data-registry-example
```

For Option 2, also remove `data-registry-project-discovery-recipient` and
`data-registry-connection-secret-list-recipient` if you created them. For a
group or manifest example, use that example's binding names. Recheck the
recipient's project visibility, effective rules, and actual API access after
revocation propagates. They should match the state before the test; other
pre-existing grants still apply. Reset before granting the next role, because
permissions from multiple bindings add together.
