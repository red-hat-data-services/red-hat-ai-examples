# S3-compatible storage for the Data Registry examples

This supplementary guide helps you provide the object storage used by the
[Data Registry getting-started example](../rhoai-3.6/getting-started.md). It is
not part of the Data Registry deployment itself.

The core example works with any approved object store that provides the S3 API.
You can either:

- use an existing AWS S3 or other S3-compatible service; or
- ask a cluster administrator to provide a cluster-local NooBaa endpoint when
  OpenShift Data Foundation (ODF) is available.

The Data Registry uses an `s3://` location and an RHOAI S3-compatible Data
Connection regardless of which provider supplies the endpoint. It does not
copy the data into the registry.

## Which Red Hat storage option is this?

The names are related but are not interchangeable:

| Name | Meaning |
| --- | --- |
| NooBaa | The object-storage service and Kubernetes operator that provide an S3-compatible endpoint. |
| Multicloud Object Gateway (MCG) | The Red Hat OpenShift Data Foundation name for the NooBaa-based object gateway. |
| OpenShift Data Foundation (ODF) | The broader Red Hat storage product and operator. It can deploy MCG alone or deploy a full storage system. |

For this use case, choose standalone MCG in ODF when a Red Hat-supported
deployment is required. It reduces the resource footprint compared with
deploying the full ODF storage stack, while retaining the Red Hat-supported
installation path. It still requires cluster-admin or operator-installation
privileges, an ODF entitlement, and a StorageClass that meets the ODF
requirements.

See Red Hat's [standalone MCG deployment
documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_data_foundation/4.22/html/deploying_openshift_data_foundation_on_vmware_vsphere/deploy-standalone-multicloud-object-gateway)
and its [MCG application access
documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_data_foundation/4.22/html/deploying_and_managing_openshift_data_foundation_using_red_hat_openstack_platform/multicloud-object-gateway_osp).

> [!WARNING]
> Do not install an object-storage operator or create cluster-scoped storage
> resources from a project-level example. Ask the OpenShift administrator to
> confirm the approved provider, subscription, StorageClass, endpoint, bucket,
> and least-privilege credentials first.

## Option 1: Use existing AWS S3 or S3-compatible storage

This is the preferred path when your organization already operates object
storage. The provider can be AWS S3, Red Hat Ceph Object Gateway, IBM Cloud
Object Storage, an ODF MCG endpoint, or another administrator-approved
S3-compatible service.

Ask the storage administrator for:

- the endpoint URL;
- an access key and secret key scoped to this example;
- the region value expected by the provider; and
- a bucket and the prefix where the example data will live.

Continue with [Create an RHOAI Data Connection](#create-an-rhoai-data-connection).

## Option 2: Provide cluster-local storage with standalone NooBaa

This option is for a cluster administrator. It does not require AWS S3, but it
does require permission to install the upstream NooBaa operator and create its
custom resources.

Standalone NooBaa is the lightweight, upstream option for an evaluation
cluster. It provides an S3 endpoint, a management console, and credentials
after installation. It is not the same support boundary as Red Hat ODF/MCG:
customers who require a Red Hat-supported storage deployment should use
standalone MCG through ODF instead.

### Install NooBaa

Use the upstream NooBaa CLI and follow its current installation instructions:

1. Install the NooBaa CLI for your operating system.
2. Create a namespace such as `noobaa`.
3. Make that namespace current and run `noobaa install`, specifying the
   approved StorageClass if the cluster has more than one:

   ```bash
   oc new-project noobaa
   oc project noobaa
   noobaa install --db-storage-class <storage-class> \\
     --pv-pool-default-storage-class <storage-class>
   ```

   If the namespace already exists, use `oc project noobaa` instead of
   `oc new-project noobaa`.
4. Wait for `noobaa status` to report that the system is Ready.
5. Keep the S3 endpoint, management-console address, access key, and secret key
   from `noobaa status` in a secure location.

The upstream [NooBaa operator
README](https://github.com/noobaa/noobaa-operator#installation) documents the
CLI installation flow. The [NooBaa core
README](https://github.com/noobaa/noobaa-core#deploy-to-kubernetes) confirms
that installation supplies both an S3 endpoint and a web management-console
address.

The generated default backing store is intended for evaluation, not
production. Create a project-scoped account and bucket through the NooBaa
console or CLI, and do not use the administrator credentials for a customer
project connection.

### Find the NooBaa endpoints

```bash
noobaa status
oc get route -n noobaa
```

Use the S3 endpoint from the status output or the S3 Route. Use the management
endpoint only to administer NooBaa and create the project bucket.

## Create an RHOAI Data Connection

In the RHOAI dashboard, open the Data Science project used by the example and
select **Connections → Create connection**. Choose **S3 compatible object
storage - v1** and enter:

| Field | Value |
| --- | --- |
| Connection name | A descriptive name such as `data-registry-storage` |
| Endpoint | The AWS S3, external provider, or NooBaa endpoint |
| Access key | The scoped account's access key |
| Secret key | The scoped account's secret key |
| Region | The provider's required region value |
| Bucket | The bucket created or assigned for the example |

Keep credentials in the RHOAI Secret. Do not put access keys, secret keys, or
pull credentials in this repository.

## Use the storage with the Data Registry example

Return to the [Data Registry getting-started guide](../rhoai-3.6/getting-started.md)
and register an asset in the same RHOAI project. When the form asks for a
connection, choose the connection created above. Use an object path such as:

```text
s3://data-registry-example/sample/orders/
```

The Data Registry stores the asset metadata and connection reference. It does
not upload objects, copy data, or validate that the path exists. Upload or
generate the example data in the selected bucket before registering it.

## If you must avoid the S3 API

RHOAI also has URI-based connections for HTTP/HTTPS locations, but those are
not a replacement for a writable object store. They do not provide bucket
creation, prefix listing, scoped object credentials, or the upload semantics
used by the current Data Registry examples.

For a no-object-store demonstration, use structured data through an approved
database connection or adapt the example to read-only public files. That is a
different example shape and should not be mixed with the S3-backed asset
steps above.

## Cleanup

Project users should delete only their own Data Connection and bucket contents
according to the storage administrator's retention policy. The cluster
administrator owns NooBaa or ODF/MCG lifecycle operations; do not delete their
namespace or PVCs as part of cleaning up this example.
