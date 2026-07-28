"""RAG Pipeline Setup Utilities.

Hides Kubernetes complexity behind simple Python functions.
All K8s resources are created programmatically -- no YAML files needed.

Authentication uses an explicit API server URL and OAuth token,
ensuring your user credentials are used instead of the notebook's
mounted service account.
"""

import time

import urllib3
from kubernetes import client
from kubernetes.client.rest import ApiException

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RAGSetup:
    """Manage Kubernetes resources for the RAG pipeline.

    Authenticates with an explicit API server URL and OAuth token
    (from ``oc whoami -t``), so operations run as **your user**
    rather than the notebook pod's service account.
    """

    def __init__(
        self,
        api_server: str,
        token: str,
        namespace: str,
        verify_ssl: bool = False,
    ):
        self.namespace = namespace
        self._token = token

        configuration = client.Configuration()
        configuration.host = api_server
        configuration.api_key = {"authorization": f"Bearer {token}"}
        configuration.verify_ssl = verify_ssl

        self._api_client = client.ApiClient(configuration)
        self.v1 = client.CoreV1Api(self._api_client)
        self.rbac_v1 = client.RbacAuthorizationV1Api(self._api_client)
        self.custom_api = client.CustomObjectsApi(self._api_client)

        self._verify_connection(api_server)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _verify_connection(self, api_server: str):
        try:
            ns = self.v1.read_namespace(self.namespace)
            print(f"Connected to {api_server}")
            print(f"  Namespace: {ns.metadata.name}")
        except ApiException as e:
            if e.status == 403:
                print(f"Connected to {api_server}")
                print(
                    f"  Namespace: {self.namespace} (no read permission, but token is valid)"
                )
            else:
                raise RuntimeError(f"Cannot connect to {api_server}: {e.reason}") from e

    # ------------------------------------------------------------------
    # Prerequisites
    # ------------------------------------------------------------------

    def create_secret(self, name: str, data: dict):
        """Create or update an Opaque Secret."""
        body = client.V1Secret(
            metadata=client.V1ObjectMeta(name=name, namespace=self.namespace),
            string_data=data,
            type="Opaque",
        )
        try:
            self.v1.create_namespaced_secret(namespace=self.namespace, body=body)
            print(f"  Secret '{name}' created")
        except ApiException as e:
            if e.status == 409:
                self.v1.patch_namespaced_secret(
                    name=name, namespace=self.namespace, body=body
                )
                print(f"  Secret '{name}' updated")
            else:
                raise

    def create_pvc(
        self,
        name: str,
        size: str = "30Gi",
        access_mode: str = "ReadWriteOnce",
    ):
        """Create a PVC if it does not already exist."""
        body = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(name=name, namespace=self.namespace),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=[access_mode],
                resources=client.V1VolumeResourceRequirements(
                    requests={"storage": size}
                ),
            ),
        )
        try:
            self.v1.create_namespaced_persistent_volume_claim(
                namespace=self.namespace, body=body
            )
            print(f"  PVC '{name}' created ({size})")
        except ApiException as e:
            if e.status == 409:
                print(f"  PVC '{name}' already exists")
            else:
                raise

    def setup_pipeline_rbac(
        self,
        service_accounts: list[str] | None = None,
    ):
        """Create Role, RoleBinding, ClusterRole and ClusterRoleBinding
        for pipeline service accounts.

        Args:
            service_accounts: SA names to bind. Defaults to the standard
                RHOAI pipeline SAs.
        """
        if service_accounts is None:
            service_accounts = ["pipeline-runner-dspa", "ds-pipeline-dspa"]

        # --- Namespaced Role ---
        role = client.V1Role(
            metadata=client.V1ObjectMeta(
                name="pipeline-rag-role", namespace=self.namespace
            ),
            rules=[
                client.V1PolicyRule(
                    api_groups=["ray.io"],
                    resources=["rayjobs", "rayclusters"],
                    verbs=[
                        "create",
                        "get",
                        "list",
                        "watch",
                        "patch",
                        "update",
                        "delete",
                    ],
                ),
                client.V1PolicyRule(
                    api_groups=["serving.kserve.io"],
                    resources=["inferenceservices", "servingruntimes"],
                    verbs=[
                        "create",
                        "get",
                        "list",
                        "watch",
                        "patch",
                        "update",
                        "delete",
                    ],
                ),
                client.V1PolicyRule(
                    api_groups=[""],
                    resources=["secrets"],
                    verbs=["create", "get", "patch", "delete"],
                ),
                client.V1PolicyRule(
                    api_groups=[""],
                    resources=["pods", "pods/log"],
                    verbs=["get", "list", "watch"],
                ),
                client.V1PolicyRule(
                    api_groups=[""],
                    resources=["events"],
                    verbs=["get", "list", "watch"],
                ),
            ],
        )
        self._create_or_update_role(role)

        # --- RoleBinding ---
        subjects = [
            client.RbacV1Subject(
                kind="ServiceAccount", name=sa, namespace=self.namespace
            )
            for sa in service_accounts
        ]
        binding = client.V1RoleBinding(
            metadata=client.V1ObjectMeta(
                name="pipeline-rag-rolebinding", namespace=self.namespace
            ),
            subjects=subjects,
            role_ref=client.V1RoleRef(
                api_group="rbac.authorization.k8s.io",
                kind="Role",
                name="pipeline-rag-role",
            ),
        )
        self._create_or_update_role_binding(binding)

        # --- ClusterRole for HardwareProfiles (best-effort) ---
        cr = client.V1ClusterRole(
            metadata=client.V1ObjectMeta(name="pipeline-hardwareprofile-reader"),
            rules=[
                client.V1PolicyRule(
                    api_groups=["infrastructure.opendatahub.io"],
                    resources=["hardwareprofiles"],
                    verbs=["get", "list"],
                ),
            ],
        )
        crb = client.V1ClusterRoleBinding(
            metadata=client.V1ObjectMeta(
                name="pipeline-hardwareprofile-reader-binding"
            ),
            subjects=subjects,
            role_ref=client.V1RoleRef(
                api_group="rbac.authorization.k8s.io",
                kind="ClusterRole",
                name="pipeline-hardwareprofile-reader",
            ),
        )
        try:
            self._create_or_update_cluster_role(cr)
            self._create_or_update_cluster_role_binding(crb)
        except ApiException as e:
            if e.status == 403:
                print(
                    "  ClusterRole for HardwareProfiles skipped (needs cluster-admin)"
                )
            else:
                raise

    def _create_or_update_role(self, role):
        name = role.metadata.name
        try:
            self.rbac_v1.create_namespaced_role(namespace=self.namespace, body=role)
            print(f"  Role '{name}' created")
        except ApiException as e:
            if e.status == 409:
                self.rbac_v1.patch_namespaced_role(
                    name=name, namespace=self.namespace, body=role
                )
                print(f"  Role '{name}' updated")
            else:
                raise

    def _create_or_update_role_binding(self, binding):
        name = binding.metadata.name
        try:
            self.rbac_v1.create_namespaced_role_binding(
                namespace=self.namespace, body=binding
            )
            print(f"  RoleBinding '{name}' created")
        except ApiException as e:
            if e.status == 409:
                self.rbac_v1.patch_namespaced_role_binding(
                    name=name, namespace=self.namespace, body=binding
                )
                print(f"  RoleBinding '{name}' updated")
            else:
                raise

    def _create_or_update_cluster_role(self, cr):
        name = cr.metadata.name
        try:
            self.rbac_v1.create_cluster_role(body=cr)
            print(f"  ClusterRole '{name}' created")
        except ApiException as e:
            if e.status == 409:
                self.rbac_v1.patch_cluster_role(name=name, body=cr)
                print(f"  ClusterRole '{name}' updated")
            else:
                raise

    def _create_or_update_cluster_role_binding(self, crb):
        name = crb.metadata.name
        try:
            self.rbac_v1.create_cluster_role_binding(body=crb)
            print(f"  ClusterRoleBinding '{name}' created")
        except ApiException as e:
            if e.status == 409:
                self.rbac_v1.patch_cluster_role_binding(name=name, body=crb)
                print(f"  ClusterRoleBinding '{name}' updated")
            else:
                raise

    def verify_prerequisites(
        self,
        secret_name: str,
        pvc_name: str,
        hf_secret_name: str | None = None,
    ):
        """Print a summary of prerequisite resources."""
        from tabulate import tabulate

        print("=== PVCs ===")
        pvcs = self.v1.list_namespaced_persistent_volume_claim(namespace=self.namespace)
        rows = [
            [p.metadata.name, p.status.phase, p.spec.resources.requests.get("storage")]
            for p in pvcs.items
        ]
        print(tabulate(rows, headers=["NAME", "STATUS", "SIZE"], tablefmt="simple"))

        print("\n=== Secrets ===")
        try:
            s = self.v1.read_namespaced_secret(
                name=secret_name, namespace=self.namespace
            )
            print(f"  {secret_name}: {len(s.data)} keys")
        except ApiException:
            print(f"  {secret_name}: NOT FOUND")

        if hf_secret_name:
            try:
                s = self.v1.read_namespaced_secret(
                    name=hf_secret_name, namespace=self.namespace
                )
                print(f"  {hf_secret_name}: {len(s.data)} keys")
            except ApiException:
                print(
                    f"  {hf_secret_name}: NOT FOUND "
                    "(required for gated models like Mistral/Llama)"
                )

        print("\n=== RBAC ===")
        try:
            r = self.rbac_v1.read_namespaced_role(
                name="pipeline-rag-role", namespace=self.namespace
            )
            print(f"  pipeline-rag-role: {len(r.rules)} rules")
        except ApiException:
            print("  pipeline-rag-role: NOT FOUND")

    # ------------------------------------------------------------------
    # Embedding Service
    # ------------------------------------------------------------------

    def deploy_embedding_service(
        self,
        model_name: str,
        service_name: str = "embedding-service",
        runtime_image: str = "registry.redhat.io/rhaiis/vllm-cuda-rhel9@sha256:094db84a1da5e8a575d0c9eade114fa30f4a2061064a338e3e032f3578f8082a",
        cpu_requests: str = "2",
        cpu_limits: str = "4",
        memory_requests: str = "4Gi",
        memory_limits: str = "8Gi",
        gpu_count: int = 1,
        max_model_len: int = 512,
    ):
        """Deploy a text embedding model as a KServe InferenceService.

        Uses vLLM with ``--task embedding`` on GPU to serve an
        OpenAI-compatible ``/v1/embeddings`` endpoint.
        """
        ns = self.namespace

        gpu_resources = {}
        if gpu_count > 0:
            gpu_resources = {"nvidia.com/gpu": str(gpu_count)}

        serving_runtime = {
            "apiVersion": "serving.kserve.io/v1alpha1",
            "kind": "ServingRuntime",
            "metadata": {"name": service_name, "namespace": ns},
            "spec": {
                "containers": [
                    {
                        "name": "kserve-container",
                        "image": runtime_image,
                        "args": [
                            "--model",
                            model_name,
                            "--task",
                            "embedding",
                            "--port",
                            "8080",
                            "--dtype",
                            "float16",
                            "--max-model-len",
                            str(max_model_len),
                        ],
                        "env": [
                            {"name": "HF_HOME", "value": "/tmp/hf_home"},
                            {"name": "HUGGINGFACE_HUB_CACHE", "value": "/tmp/hf_home"},
                            {"name": "HF_HUB_OFFLINE", "value": "0"},
                            {"name": "TRANSFORMERS_OFFLINE", "value": "0"},
                        ],
                        "ports": [{"containerPort": 8080, "protocol": "TCP"}],
                        "resources": {
                            "requests": {
                                "cpu": cpu_requests,
                                "memory": memory_requests,
                                **gpu_resources,
                            },
                            "limits": {
                                "cpu": cpu_limits,
                                "memory": memory_limits,
                                **gpu_resources,
                            },
                        },
                    }
                ],
                "supportedModelFormats": [{"name": "vLLM", "version": "1"}],
            },
        }

        isvc = {
            "apiVersion": "serving.kserve.io/v1beta1",
            "kind": "InferenceService",
            "metadata": {
                "name": service_name,
                "namespace": ns,
                "annotations": {"serving.kserve.io/deploymentMode": "RawDeployment"},
            },
            "spec": {
                "predictor": {
                    "model": {
                        "modelFormat": {"name": "vLLM"},
                        "runtime": service_name,
                        "resources": {
                            "requests": {
                                "cpu": cpu_requests,
                                "memory": memory_requests,
                                **gpu_resources,
                            },
                            "limits": {
                                "cpu": cpu_limits,
                                "memory": memory_limits,
                                **gpu_resources,
                            },
                        },
                    }
                }
            },
        }

        self._apply_custom_object(
            "serving.kserve.io",
            "v1alpha1",
            "servingruntimes",
            service_name,
            serving_runtime,
            "ServingRuntime",
        )
        self._apply_custom_object(
            "serving.kserve.io",
            "v1beta1",
            "inferenceservices",
            service_name,
            isvc,
            "InferenceService",
        )

        endpoint = f"http://{service_name}-predictor.{ns}.svc.cluster.local:8080"
        print(f"  Endpoint: {endpoint}")
        return endpoint

    def wait_for_service(self, name: str, timeout: int = 900, interval: int = 15):
        """Wait for an InferenceService to become Ready."""
        print(f"Waiting for InferenceService '{name}'...")
        deadline = time.time() + timeout
        while time.time() < deadline:
            obj = self.custom_api.get_namespaced_custom_object(
                group="serving.kserve.io",
                version="v1beta1",
                namespace=self.namespace,
                plural="inferenceservices",
                name=name,
            )
            conditions = obj.get("status", {}).get("conditions", [])
            ready = any(
                c.get("type") == "Ready" and c.get("status") == "True"
                for c in conditions
            )
            if ready:
                url = obj.get("status", {}).get("url", "")
                print(f"  Ready: {url}")
                return url
            time.sleep(interval)
        raise TimeoutError(f"InferenceService '{name}' not ready after {timeout}s")

    @staticmethod
    def test_embedding_endpoint(
        endpoint: str, model_name: str, retries: int = 30, interval: int = 5
    ):
        """Send a test request to the embedding service."""
        import requests

        print(f"Testing: {endpoint}")
        for i in range(retries):
            try:
                resp = requests.post(
                    f"{endpoint}/v1/embeddings",
                    json={"model": model_name, "input": ["test"]},
                    timeout=10,
                )
                resp.raise_for_status()
                dim = len(resp.json()["data"][0]["embedding"])
                print(f"  Ready (dim={dim})")
                return dim
            except requests.ConnectionError:
                if i < retries - 1:
                    print(f"  Retrying in {interval}s... ({i + 1}/{retries})")
                    time.sleep(interval)
                else:
                    print(f"  Not ready after {retries * interval}s")
            except Exception as e:
                print(f"  Error: {e}")
                break
        return None

    # ------------------------------------------------------------------
    # KFP Client
    # ------------------------------------------------------------------

    def get_kfp_client(self, route_name: str = "ds-pipeline-dspa"):
        """Create a KFP client from the DSPA OpenShift Route.

        Returns:
            A configured ``kfp.Client``.
        """
        import kfp

        route = self.custom_api.get_namespaced_custom_object(
            group="route.openshift.io",
            version="v1",
            namespace=self.namespace,
            plural="routes",
            name=route_name,
        )
        dspa_url = f"https://{route['spec']['host']}"
        print(f"DSPA: {dspa_url}")
        return kfp.Client(host=dspa_url, existing_token=self._token, verify_ssl=False)

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def show_rayjobs(self):
        """Display RayJob status and Ray pod status."""
        from tabulate import tabulate

        print("=== RayJobs ===")
        try:
            items = self.custom_api.list_namespaced_custom_object(
                group="ray.io",
                version="v1",
                namespace=self.namespace,
                plural="rayjobs",
            ).get("items", [])
            if items:
                rows = [
                    [
                        j["metadata"]["name"],
                        j.get("status", {}).get("jobStatus", "Unknown"),
                        j.get("status", {}).get("jobDeploymentStatus", "Unknown"),
                    ]
                    for j in items
                ]
                print(
                    tabulate(
                        rows,
                        headers=["NAME", "STATUS", "DEPLOYMENT"],
                        tablefmt="simple",
                    )
                )
            else:
                print("  No RayJobs found")
        except ApiException as e:
            print(f"  Error: {e.reason}")

        print("\n=== Ray Pods ===")
        pods = self.v1.list_namespaced_pod(
            namespace=self.namespace, label_selector="ray.io/node-type"
        )
        if pods.items:
            rows = [
                [
                    p.metadata.name,
                    p.status.phase,
                    p.metadata.labels.get("ray.io/node-type"),
                ]
                for p in pods.items
            ]
            print(tabulate(rows, headers=["NAME", "STATUS", "TYPE"], tablefmt="simple"))
        else:
            print("  No Ray pods found")

    def show_pipeline_pods(self):
        """Display KFP pipeline component pods."""
        from tabulate import tabulate

        pods = self.v1.list_namespaced_pod(
            namespace=self.namespace,
            label_selector="pipelines.kubeflow.org/v2_component=true",
        )
        if pods.items:
            sorted_pods = sorted(
                pods.items, key=lambda p: p.metadata.creation_timestamp
            )
            rows = [
                [
                    p.metadata.name,
                    p.status.phase,
                    p.metadata.creation_timestamp.strftime("%H:%M:%S"),
                ]
                for p in sorted_pods
            ]
            print(
                tabulate(rows, headers=["NAME", "STATUS", "STARTED"], tablefmt="simple")
            )
        else:
            print("No pipeline pods found")

    def show_inferenceservices(self, llm_isvc_name: str | None = None):
        """Display InferenceServices and optionally show LLM pods."""
        from tabulate import tabulate

        print("=== InferenceServices ===")
        try:
            items = self.custom_api.list_namespaced_custom_object(
                group="serving.kserve.io",
                version="v1beta1",
                namespace=self.namespace,
                plural="inferenceservices",
            ).get("items", [])
            if items:
                rows = []
                for i in items:
                    status = i.get("status", {})
                    conds = status.get("conditions", [])
                    ready = next(
                        (c["status"] for c in conds if c.get("type") == "Ready"),
                        "Unknown",
                    )
                    rows.append([i["metadata"]["name"], ready, status.get("url", "")])
                print(
                    tabulate(rows, headers=["NAME", "READY", "URL"], tablefmt="simple")
                )
            else:
                print("  None found")
        except ApiException as e:
            print(f"  Error: {e.reason}")

        if llm_isvc_name:
            print(f"\n=== Pods for '{llm_isvc_name}' ===")
            pods = self.v1.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=f"serving.kserve.io/inferenceservice={llm_isvc_name}",
            )
            if pods.items:
                rows = []
                for p in pods.items:
                    cs = p.status.container_statuses or []
                    ready = sum(1 for c in cs if c.ready)
                    rows.append([p.metadata.name, p.status.phase, f"{ready}/{len(cs)}"])
                print(
                    tabulate(
                        rows, headers=["NAME", "STATUS", "READY"], tablefmt="simple"
                    )
                )
            else:
                print("  No pods found")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def delete_inferenceservice(self, name: str):
        """Delete an InferenceService."""
        self._delete_custom_object(
            "serving.kserve.io", "v1beta1", "inferenceservices", name
        )

    def delete_servingruntime(self, name: str):
        """Delete a ServingRuntime."""
        self._delete_custom_object(
            "serving.kserve.io", "v1alpha1", "servingruntimes", name
        )

    def delete_pvc(self, name: str):
        """Delete a PVC."""
        try:
            self.v1.delete_namespaced_persistent_volume_claim(
                name=name, namespace=self.namespace
            )
            print(f"  Deleted PVC '{name}'")
        except ApiException as e:
            if e.status == 404:
                print(f"  PVC '{name}' not found")
            else:
                raise

    def delete_secret(self, name: str):
        """Delete a Secret."""
        try:
            self.v1.delete_namespaced_secret(name=name, namespace=self.namespace)
            print(f"  Deleted Secret '{name}'")
        except ApiException as e:
            if e.status == 404:
                print(f"  Secret '{name}' not found")
            else:
                raise

    def delete_rbac(self):
        """Delete the pipeline Role, RoleBinding, and ClusterRole/Binding."""
        for name in ["pipeline-rag-rolebinding"]:
            try:
                self.rbac_v1.delete_namespaced_role_binding(
                    name=name, namespace=self.namespace
                )
                print(f"  Deleted RoleBinding '{name}'")
            except ApiException as e:
                if e.status != 404:
                    raise

        for name in ["pipeline-rag-role"]:
            try:
                self.rbac_v1.delete_namespaced_role(name=name, namespace=self.namespace)
                print(f"  Deleted Role '{name}'")
            except ApiException as e:
                if e.status != 404:
                    raise

        for name in ["pipeline-hardwareprofile-reader-binding"]:
            try:
                self.rbac_v1.delete_cluster_role_binding(name=name)
                print(f"  Deleted ClusterRoleBinding '{name}'")
            except ApiException as e:
                if e.status not in (404, 403):
                    raise

        for name in ["pipeline-hardwareprofile-reader"]:
            try:
                self.rbac_v1.delete_cluster_role(name=name)
                print(f"  Deleted ClusterRole '{name}'")
            except ApiException as e:
                if e.status not in (404, 403):
                    raise

    def cleanup_all(
        self,
        llm_isvc_name: str | None = None,
        embedding_service_name: str | None = None,
        pvc_name: str | None = None,
        secret_name: str | None = None,
    ):
        """Delete all RAG resources in one call."""
        if llm_isvc_name:
            self.delete_inferenceservice(llm_isvc_name)
            self.delete_servingruntime(llm_isvc_name)
        if embedding_service_name:
            self.delete_inferenceservice(embedding_service_name)
            self.delete_servingruntime(embedding_service_name)
        if pvc_name:
            self.delete_pvc(pvc_name)
        if secret_name:
            self.delete_secret(secret_name)
        self.delete_rbac()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _apply_custom_object(self, group, version, plural, name, body, kind):
        """Create-or-update pattern for custom resources."""
        try:
            self.custom_api.get_namespaced_custom_object(
                group=group,
                version=version,
                namespace=self.namespace,
                plural=plural,
                name=name,
            )
            self.custom_api.patch_namespaced_custom_object(
                group=group,
                version=version,
                namespace=self.namespace,
                plural=plural,
                name=name,
                body=body,
            )
            print(f"  {kind} '{name}' updated")
        except ApiException as e:
            if e.status == 404:
                self.custom_api.create_namespaced_custom_object(
                    group=group,
                    version=version,
                    namespace=self.namespace,
                    plural=plural,
                    body=body,
                )
                print(f"  {kind} '{name}' created")
            else:
                raise

    def _delete_custom_object(self, group, version, plural, name):
        kind = plural.rstrip("s").capitalize()
        try:
            self.custom_api.delete_namespaced_custom_object(
                group=group,
                version=version,
                namespace=self.namespace,
                plural=plural,
                name=name,
            )
            print(f"  Deleted {kind} '{name}'")
        except ApiException as e:
            if e.status == 404:
                print(f"  {kind} '{name}' not found")
            else:
                raise
