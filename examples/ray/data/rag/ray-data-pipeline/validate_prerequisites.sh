#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${1:-rag-example}"
PASS=0
FAIL=0
TOTAL=0

check() {
    local description="$1"
    local fix_hint="$2"
    shift 2
    TOTAL=$((TOTAL + 1))
    if "$@" &>/dev/null; then
        echo "[PASS] $description"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $description — $fix_hint"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== RAG Pipeline Prerequisite Validation ==="
echo "Namespace: $NAMESPACE"
echo ""

# a. oc authenticated — show user on success
TOTAL=$((TOTAL + 1))
if auth_user=$(oc whoami 2>/dev/null); then
    echo "[PASS] oc authenticated as $auth_user"
    PASS=$((PASS + 1))
else
    echo "[FAIL] oc authenticated — Run: oc login <cluster-url>"
    FAIL=$((FAIL + 1))
fi

check "Namespace '$NAMESPACE' exists" \
    "Create it with: oc new-project $NAMESPACE" \
    oc get namespace "$NAMESPACE"

check "KubeRay CRDs installed" \
    "Install the KubeRay operator via OperatorHub or ensure RHOAI is configured" \
    oc get crd rayclusters.ray.io

RAYCLUSTER_CHECK() {
    oc get raycluster -n "$NAMESPACE" --no-headers 2>/dev/null | grep -q .
}
check "RayCluster exists in '$NAMESPACE'" \
    "Apply the RayCluster manifest: oc apply -f manifests/raycluster-rag-optimized.yaml" \
    RAYCLUSTER_CHECK

PVC_CHECK() {
    local access_modes
    access_modes=$(oc get pvc rag-data-pvc -n "$NAMESPACE" -o jsonpath='{.status.accessModes[*]}' 2>/dev/null)
    [[ "$access_modes" == *"ReadWriteMany"* ]]
}
check "PVC 'rag-data-pvc' exists with RWX access" \
    "Create a ReadWriteMany PVC named 'rag-data-pvc' in namespace '$NAMESPACE'" \
    PVC_CHECK

GPU_CHECK() {
    oc get nodes -l nvidia.com/gpu.present=true --no-headers 2>/dev/null | grep -q .
}
check "GPU nodes available" \
    "Ensure at least one node with NVIDIA GPU is available in the cluster" \
    GPU_CHECK

MILVUS_CHECK() {
    oc run "milvus-check-$$" --rm -i --restart=Never \
        --image=curlimages/curl -n "$NAMESPACE" \
        -- curl -sf --max-time 5 \
        "http://milvus-milvus.milvus.svc.cluster.local:19530/v1/vector/collections" &>/dev/null
}
check "Milvus reachable from namespace '$NAMESPACE'" \
    "Deploy Milvus or check NetworkPolicy. See: https://milvus.io/docs/install_cluster-milvusoperator.md" \
    MILVUS_CHECK

check "RBAC: can create RayJobs" \
    "Request RayJob create permissions for your service account in '$NAMESPACE'" \
    oc auth can-i create rayjobs.ray.io -n "$NAMESPACE"

check "RBAC: can view pod logs" \
    "Request pods/log get permissions for your service account in '$NAMESPACE'" \
    oc auth can-i get pods/log -n "$NAMESPACE"

echo ""
echo "=== Results: $PASS/$TOTAL checks passed ==="
if [ "$FAIL" -gt 0 ]; then
    echo "$FAIL check(s) failed. Fix the issues above before running the pipeline."
    exit 1
else
    echo "All prerequisites met. You're ready to run the RAG pipeline!"
    exit 0
fi
