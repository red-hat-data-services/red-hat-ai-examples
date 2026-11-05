# Getting started with the Data Registry in RHOAI 3.6

The Data Registry is a Technology Preview catalog for describing data assets
in an RHOAI project. It stores metadata and location/connection references;
the data itself remains in the source system. This customer walkthrough takes
you from an enabled registry to an asset you can discover and read from a
workbench.

> **Technology Preview:** Technology Preview features are not supported with
> Red Hat production service-level agreements (SLAs), might not be functionally
> complete, and are not recommended for production.

## Follow the four steps

| Step | Guide | You will finish with |
| --- | --- | --- |
| 1 | [Configure the Data Registry](01-configure-data-registry/README.md) | A running registry and dashboard entry. Cluster administrator access is required. |
| 2 | [Create a project, connection, collection, and asset](02-register-data-asset/README.md) | A synthetic document in S3-compatible storage and a discoverable catalog record. |
| 3 | [Use the API from a workbench](03-use-registry-api/README.md) | A notebook that reads metadata, downloads the document, and registers an API-created asset. |
| 4 | [Share Data Registry assets](04-share-registry-access/README.md) | Choose project-wide access or grant a user or group access to registry assets only. |

The example uses `data-registry-example` as the RHOAI project and an
S3-compatible [SeaweedFS evaluation setup](supplementary/s3-compatible-storage.md)
for its sample document. You can use an existing approved S3 service instead.
SeaweedFS is not required for the Data Registry service itself.

The guide is written for RHOAI 3.6. An administrator should verify component
settings and generated role names against the installed cluster before applying
them. The notebook needs an enabled Workbenches component, an attached S3
connection, and a namespaced registry role for its ServiceAccount.
