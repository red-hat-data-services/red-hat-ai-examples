# Getting started with the Data Registry in RHOAI 3.6

The Data Registry is a Technology Preview catalog for data assets in an RHOAI
project. It stores metadata and location/connection references; the data stays
in its source system. This walkthrough enables the registry and shows how to
discover and read an asset from a workbench.

You can run the guide as a cluster admin or use separate accounts: an **RHOAI
admin** for Step 1 and an **RHOAI user** with project `admin` for Steps 2–3 and
optional Step 4. Sample-user provisioning and some supporting resources may
need an identity-provider or cluster admin, or delegated OpenShift permissions.
RHOAI admin status alone does not grant project `admin`.

> **Optional prerequisite — sample users:** Follow the
> [Create sample users and roles](supplementary/users-and-roles.md) guide for
> separate accounts: `rhoai-admin` (Step 1),
> `rhoai-user-data-curator` (Steps 2–3), and `rhoai-user-recipient` (Step 4).
> Use your own RHOAI accounts if they have the required access.
>
> **Optional prerequisite — S3 storage:** Use the
> [SeaweedFS evaluation setup](supplementary/s3-compatible-storage.md) for the
> sample object, or use an existing approved S3-compatible service.
>
> **Optional prerequisite — demo PostgreSQL:** The Data Registry needs a
> reachable PostgreSQL database for its metadata. Reuse an existing approved
> database, or follow the [supplementary demo PostgreSQL
> setup](supplementary/postgresql-demo.md) to deploy one in a separate
> project. The demo database is optional; a metadata database is required to
> run the example.
>
> **Technology Preview:** Technology Preview features are not supported with
> Red Hat production service-level agreements (SLAs), might not be functionally
> complete, and are not recommended for production.

## Follow the four steps

| Step | Guide | Outcome | User |
| --- | --- | --- | --- |
| 1 | [Configure the Data Registry](01-configure-data-registry/README.md) | Enabled registry and dashboard | RHOAI admin |
| 2 | [Register a data asset](02-register-data-asset/README.md) | Project created or selected; S3 asset registered | RHOAI user (project `admin`) |
| 3 | [Use the Data Registry API](03-use-registry-api/README.md) | Read an asset; register another via API | RHOAI user (project `admin`) |
| 4&nbsp;(optional) | [Share Data Registry assets](04-share-registry-access/README.md) | Project-wide or registry-only access | RHOAI user (project `admin`) |
