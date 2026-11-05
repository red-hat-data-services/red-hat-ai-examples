# Step 2: Create a project, collection, and data asset

[← Step 1: Configure the registry](../01-configure-data-registry/README.md) ·
[Step 3: Use the API →](../03-use-registry-api/README.md) ·
[Guide index](../README.md)

In this walkthrough, you create an RHOAI project, connect it to an S3-compatible
object store, upload one fictional support document, and register that document
in the Data Registry. The registry stores a description and a location. The
object stays in S3-compatible storage, and the connection holds the credentials.
Step 3 uses the same asset and connection from a workbench.

This example uses **SeaweedFS** as its S3-compatible store. It is one convenient
evaluation option, not a Data Registry dependency. If your organization already
provides S3-compatible storage, use its approved endpoint, bucket, and scoped
credentials in the connection, and adjust the example path.

## Before you start

- Complete [Step 1](../01-configure-data-registry/README.md), or ask an
  administrator to confirm that **AI hub → Data** loads.
- Follow the [S3-compatible storage guide](../supplementary/s3-compatible-storage.md)
  to deploy and verify SeaweedFS, or obtain an existing S3 service. The guide
  explains the internal endpoint, bucket, credential handling, and test upload.
- Have permission to create an RHOAI project, connection, collection, and asset.
- Keep credentials out of Git, screenshots, asset descriptions, and notebook
  outputs. This example's document contains only synthetic information.

The example names below are used throughout Steps 2 and 3:

| Item | Example value | Why it exists |
| --- | --- | --- |
| RHOAI project | `data-registry-example` | Project boundary for the connection and registry metadata. |
| S3 bucket | `data-registry-example` | Holds the example document; it happens to have the same name as the project. |
| Connection | `data-registry-storage` | Supplies S3 endpoint and credentials to the workbench. |
| Collection | `customer-support` | Groups related support knowledge assets. |
| Asset | `customer-support-faq` | Catalog entry for the document prefix. |
| Asset path | `s3://data-registry-example/examples/customer-support/` | Bucket and prefix containing the document. |

## 1. Create the RHOAI project

In the RHOAI dashboard, open **Projects**, select **Create project**, enter
`data-registry-example` as the project name, and create it. Select the new
project in the project selector. A project is the access boundary: people who
can view registry resources in it can see its collections and assets. The
SeaweedFS deployment is in a separate namespace, so its service and PVC are
not owned by this RHOAI project.

An OpenShift administrator can create the same project from the CLI:

```bash
oc new-project data-registry-example \
  --display-name='Data Registry example'
oc label namespace data-registry-example opendatahub.io/dashboard=true
```

If the project already exists, do not recreate it. Check that it appears under
**Projects** in the dashboard. The label makes a CLI-created namespace
available as an RHOAI project; it does not grant storage access.

> **Screenshot to add:** Projects page with `data-registry-example` selected.

## 2. Put an example document in S3-compatible storage

The [SeaweedFS guide's S3 verification](../supplementary/s3-compatible-storage.md#verify-the-s3-api)
creates a small `sample/hello.txt` object. Upload the more representative
[synthetic FAQ](sample-data/customer-support-faq.md) for this tutorial. It gives
the asset a real object that Step 3 can list and download. The content is safe
to inspect, but it is still only fictional demonstration material.

Keep the guide's `oc port-forward service/seaweedfs 18333:8333` running. In a
second terminal, load the S3 credentials from `Secret/seaweedfs-credentials`
as shown in that guide, then run these commands from this directory:

```bash
aws --endpoint-url http://127.0.0.1:18333 s3api put-object \
  --bucket data-registry-example \
  --key examples/customer-support/customer-support-faq.md \
  --body sample-data/customer-support-faq.md

aws --endpoint-url http://127.0.0.1:18333 s3api list-objects-v2 \
  --bucket data-registry-example \
  --prefix examples/customer-support/

unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
```

The list should show `examples/customer-support/customer-support-faq.md`.
Keep the `s3://` path in the table above: it describes the bucket and prefix,
while the connection's endpoint tells an S3 client where to reach the service.
The registry does not upload this file for you.

## 3. Create an S3 connection in the project

Open **Projects → data-registry-example → Connections → Create connection**.
Choose **S3 compatible object storage - v1**. This connection will be attached
to the workbench in Step 3 and selected on the asset form below. Enter:

| Connection field | Example value | What it means |
| --- | --- | --- |
| Name | `data-registry-storage` | The connection resource used by the asset and workbench. |
| Access key | From `Secret/seaweedfs-credentials` | Identifies the S3 client. Do not put it in the asset. |
| Secret key | From the same Secret | Authenticates the client. Do not include it in screenshots. |
| Endpoint | `http://seaweedfs.data-registry-storage.svc:8333` | Internal S3 API endpoint; port 12646 is the Admin UI and is not used here. |
| Region | `us-east-1` | Signing region for this example. |
| Bucket | `data-registry-example` | Bucket holding the document. |

The [storage guide's connection section](../supplementary/s3-compatible-storage.md#create-an-rhoai-data-connection)
has the credential transfer procedure and troubleshooting notes. The service
name contains the **storage namespace**. Replace it if your SeaweedFS instance
uses another namespace. The internal `.svc` address is for workloads in the
cluster; the workstation uses the port forward only to upload the fixture.

After saving, check that `data-registry-storage` appears on the project's
**Connections** tab. The connection contains configuration and credentials; it
does not itself create a Data Registry asset or grant every project member S3
access.

> **Screenshot to add:** Completed S3 connection form with the access and
> secret key fields obscured; then the connection listed in the project.

## 4. Create a collection

Open **AI hub → Data** and select `data-registry-example` in the project
selector. Select **Manage collections**, then **Create collection**. Enter:

| Collection field | Example value | Why |
| --- | --- | --- |
| Name | `customer-support` | Stable group for support knowledge assets. |
| Description | `Synthetic support knowledge used to demonstrate document discovery and API access.` | Tells future readers what belongs here. |

Save and confirm the collection appears in the list. The server records the
creator as owner; the current form does not ask you to type an owner. That owner
is descriptive metadata and does not grant permissions. Every asset belongs to
one collection. The `default` collection is fine for a quick test, but a named
collection makes this example easier to find. Collections do not create an
additional access boundary inside the project.

> **Screenshot to add:** Manage collections modal with the new collection row.

## 5. Register the document as an asset

Select **Register data** in **AI hub → Data**. Fill in the form using the values
below. The form has sections for identity, format, organization, location, and
additional properties. Select the connection you just created; this records a
reference to it on the asset so another user can identify the intended source.
The registry stores the connection name, not a copy of the S3 keys.

| Field | Enter | Why this value is useful |
| --- | --- | --- |
| Asset name | `customer-support-faq` | Stable lowercase identifier for API and search. |
| Description | `Fictional shipping, returns, and escalation FAQ for a support-assistant demonstration. No customer records; reviewed when the tutorial changes.` | Scope, exclusions, and update cadence in one place. |
| Asset type | **Unstructured** | The source is a document, not a table with columns. |
| Format | **Documents** | Matches the Markdown document in S3. |
| Collection | `customer-support` | Groups it with related support knowledge. |
| Labels | `customer-support`, `synthetic`, `faq` | Short, reusable discovery terms. |
| Connection | `data-registry-storage` | Points to the S3 configuration in this project. |
| Path | `s3://data-registry-example/examples/customer-support/` | Prefix containing the FAQ object. |
| Purpose | `Demonstrate document discovery and retrieval for a support assistant.` | States the intended use without claiming production suitability. |
| License | **Internal use** | The synthetic document is for this tutorial; confirm reuse terms for real data. |
| Maturity | **Experimental** | Signals that this is an evaluation asset. |
| Domain | `customer-support` | Business area that owns the content. |
| PII status | **No PII** | Matches the fictional fixture; this is metadata, not an access control. |
| Custom properties | `source=synthetic-tutorial`, `review-cadence=on-change` | Extra context useful to downstream readers. |

The owner shown after registration comes from the authenticated creator; it is
not a field to fill in. Names must use lowercase letters, digits, and hyphens
and be at most 63 characters. Description is limited to 500 characters and
purpose to 200. Labels should follow one agreed vocabulary. Never add a
password, token, or real personal information to labels, descriptions, paths,
or custom properties.

If your organization uses a different S3 provider, choose the project
connection for that provider and record its actual `s3://bucket/prefix/` path.
The path describes the location; it is not a credential or an upload command.

> **Screenshot to add:** Registration form showing identity and format values.
>
> **Screenshot to add:** Organization, location, and governance values with
> `data-registry-storage` selected; no credentials in view.

Select **Register**. Find `customer-support-faq` in `customer-support` and open
its details. Confirm the format, description, connection, path, labels, and
governance metadata. A successful save proves the metadata was registered. The
upload in section 2 proves the object exists. Step 3 proves an authorized
workbench can read both the registry metadata and the object.

> **Screenshot to add:** Asset detail page with the connection and path visible.

## What the fields mean for your own data

For another data product, replace the fictional values deliberately:

- **Name, description, owner:** use a stable identifier, describe scope and
  exclusions, and identify who can answer quality and access questions. The
  creator-derived owner does not grant permissions.
- **Type, format, schema:** choose structured for tabular data, and describe
  fields and nullability in its schema. Choose unstructured for documents,
  images, audio, video, binary files, and other file collections. The registry
  does not inspect a source to verify a declared schema.
- **Collection and labels:** organize discovery within the project. Neither
  changes who can view the asset.
- **Connection and path:** associate an existing project connection and locate
  the physical data. Registration does not test credentials or grant storage
  access. A path should not contain secrets.
- **Purpose, license, maturity, domain, PII, custom properties:** record
  intended use, reuse terms, lifecycle, business area, data classification,
  and local conventions. Confirm these with the data owner. PII status is an
  informative classification; it does not enforce storage or registry access.

Next, [use the API from a workbench](../03-use-registry-api/README.md) to
inspect this asset and download the document using the attached connection.
