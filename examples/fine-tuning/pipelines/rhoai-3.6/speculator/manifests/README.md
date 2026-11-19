# Access manifests for the speculator pipelines

Everything an administrator needs to apply so one user can run the four speculator pipelines in one project. The reasoning behind each grant — what it allows, what it deliberately does not, and the trust boundary that remains — is in the [main guide](../README.md#access-you-need-and-what-your-administrator-must-provide).

| File | Applied in | Grants |
| --- | --- | --- |
| [`engineer-role.yaml`](engineer-role.yaml) | the project namespace | The user: Trainer jobs, the shared PVC, serving resources, workbenches, run inspection |
| [`pipeline-runner-role.yaml`](pipeline-runner-role.yaml) | the project namespace | The `pipeline-runner` ServiceAccount: TrainJob submission, the KFP workspace PVC, the serve stage |
| [`cluster-access.yaml`](cluster-access.yaml) | cluster-scoped | Both identities: ClusterTrainingRuntime discovery, a named read of this project, storage class discovery |
| [`hardwareprofile-reader.yaml`](hardwareprofile-reader.yaml) | `redhat-ods-applications` | The runner: read the GPU HardwareProfile the serving stage needs (train-only / online / offline) |

Neither identity gets Secret access or ServiceAccount token minting. Credential setup is a separate administrator procedure — see [Kubernetes authentication secret](../README.md#kubernetes-authentication-secret).

## Before you apply

Configure the **pipeline server** for the project first. It creates the `pipeline-runner` ServiceAccount these manifests bind, and it stores object-storage credentials in a Secret, so it is an administrator task too — see [Configure the pipeline server](../README.md#configure-the-pipeline-server).

## Apply

Every file uses two placeholders: `<project-namespace>` and `<your-username>`. Substitute them on the way in rather than editing the files:

```bash
PROJECT=<project-namespace>
USERNAME=<your-username>

for f in engineer-role.yaml pipeline-runner-role.yaml cluster-access.yaml; do
  sed -e "s/<project-namespace>/$PROJECT/g" -e "s/<your-username>/$USERNAME/g" "$f" | oc apply -f -
done

# Serving modes only (train-only / online / offline):
sed -e "s/<project-namespace>/$PROJECT/g" hardwareprofile-reader.yaml | oc apply -f -
```

If the runner on your cluster is not called `pipeline-runner`, confirm the name with `oc get serviceaccounts -n <project-namespace>` and adjust the `subjects` entries before applying.

## Verify

Check the grants as the user, not as the administrator:

```bash
oc auth can-i create trainjobs -n <project-namespace> --as=<your-username>
oc auth can-i create inferenceservices.serving.kserve.io -n <project-namespace> --as=<your-username>
oc auth can-i list clustertrainingruntimes.trainer.kubeflow.org --as=<your-username>
```

The user runs the full self-check list in [Check your own access before you start](../README.md#check-your-own-access-before-you-start); every answer must be `yes` for the modes they plan to run.

## Applying for a second project

`cluster-access.yaml` names its ClusterRole and ClusterRoleBinding after the project, so applying it for another project creates a separate pair and leaves the first one intact. Do not rename them back to a shared fixed name — a second apply would replace the first project's `resourceNames` and subjects, silently removing that user's access. To maintain one shared binding instead, add subjects to the existing ClusterRoleBinding and append the new project to the ClusterRole's `resourceNames` lists.
