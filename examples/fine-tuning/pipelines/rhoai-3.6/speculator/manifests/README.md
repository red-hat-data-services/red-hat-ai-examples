# Access manifests for the speculator pipelines

Everything an administrator needs to apply so one user can run the four speculator pipelines in one project. The reasoning behind each grant — what it allows, what it deliberately does not, and the trust boundary that remains — is in the [main guide](../README.md#access-you-need-and-what-your-administrator-must-provide).

| File | Applied in | Grants |
| --- | --- | --- |
| [`engineer-role.yaml`](engineer-role.yaml) | the project namespace | The user: Trainer jobs, the shared PVC, serving resources, workbenches, run inspection |
| [`pipeline-runner-role.yaml`](pipeline-runner-role.yaml) | the project namespace | The `pipeline-runner` ServiceAccount: TrainJob submission, the KFP workspace PVC, the serve stage |
| [`cluster-access.yaml`](cluster-access.yaml) | cluster-scoped | Both identities: ClusterTrainingRuntime discovery, a named read of this project, storage class discovery |
| [`hardwareprofile-reader.yaml`](hardwareprofile-reader.yaml) | `redhat-ods-applications` | The runner: read the GPU HardwareProfile the serving stage needs (train-only / online / offline) |

Neither identity gets Secret access or ServiceAccount token minting. Credential setup is a separate administrator procedure — see [Kubernetes authentication secret](../README.md#kubernetes-authentication-secret).

## Why the grants look like this

**The user Role has no secret permissions.** This is not just minimalism: on clusters that populate manually created `kubernetes.io/service-account-token` Secrets, a role combining secret creation with secret read can mint a token for a more privileged ServiceAccount — create a Secret of that type pointing at the ServiceAccount, wait for the token controller to populate it, read it back. Keeping both capabilities away from the user and the runner closes that path, which is why credential setup is an administrator procedure instead.

**The runner Role is smaller still.** It deliberately does not get secret access, token minting, workbench (`notebooks`) management, pod exec/port-forward, or deployment scaling — none of those are pipeline operations, and granting them would let pipeline code borrow credentials or escalate through another ServiceAccount. It *does* get the ClusterTrainingRuntime read from `cluster-access.yaml`, because the TrainJobs it submits reference CTRs by name.

**What neither Role can fence off.** Any identity that can create TrainJobs in a namespace can read that namespace's Secrets and run arbitrary code in it, through the Trainer API's own fields. The project is therefore a single trust domain — see [the trust-boundary note](../README.md#what-this-access-deliberately-does-not-grant) in the main guide. Removing grants such as notebooks or `pods/exec` does not change that; admission policy (Kyverno, Gatekeeper) is the enforcement point.

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
