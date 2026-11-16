#!/usr/bin/env python3
"""Deploy the external vLLM server used by the speculator training examples.

Applies the Deployment + Service + NetworkPolicy from vllm-server.yaml, waits
for the rollout to complete, and prints the endpoint URL to set as
VLLM_ENDPOINT in the notebooks.

Intended to be run from a workbench terminal (or anywhere with `oc` and cluster
credentials) — the notebooks deliberately do not deploy the server themselves:

    python3 deploy_vllm_server.py --namespace <your-namespace> --token <token>

The token must belong to a user allowed to create Deployments and Services in
the namespace (e.g., the namespace owner).

Getting the token:
- NOTEBOOK_USER_TOKEN is only set inside the notebook kernel (the
  "Authenticate to your OpenShift Cluster" cell), NOT in workbench terminals —
  from a terminal, --token defaults to an empty $NOTEBOOK_USER_TOKEN.
- Copy the token from the notebook's auth cell, or from the OpenShift console
  (username dropdown -> "Copy login command" -> "Display token"), and pass it:
      python3 deploy_vllm_server.py --token <token>
- Alternatively, run `oc login` in the terminal first; the script then reuses
  that session and no token is needed.

--namespace is detected from the pod's service account when run inside an
OpenShift AI workbench, so it can usually be omitted.

For the DATA_ONLY Method 2 example, point the server's hidden states path at
that notebook's output directory with --hs-path (the manifest default matches
the OFFLINE notebook):

    python3 deploy_vllm_server.py --hs-path /mnt/speculator/run-01/hidden_states

Clean up again with --cleanup (hidden states and checkpoints on the PVC are
not removed).
"""

import argparse
import os
import subprocess
import sys
import urllib.error
import urllib.request

MANIFEST_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "vllm-server.yaml"
)
SERVICE_NAME = "vllm-svc"
SERVICE_PORT = 8000

# Must stay consistent with spec.progressDeadlineSeconds in vllm-server.yaml:
# the Deployment gives up progressing after this many seconds, so waiting any
# longer in the rollout check below cannot help. The notebooks' guidance quotes
# the same figure (15 minutes) for first starts that include the image pull.
ROLLOUT_TIMEOUT_SECONDS = 900

HEALTH_CHECK_TIMEOUT_SECONDS = 30

SERVICE_ACCOUNT_DIR = "/var/run/secrets/kubernetes.io/serviceaccount"


def run_oc(*args):
    """Run an oc command, stopping on failure — a failed login or apply must
    not be followed by rollout polling."""
    result = subprocess.run(["oc", *args], capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        raise RuntimeError(
            f"oc {' '.join(args[:1])} failed (exit code {result.returncode})"
        )
    if result.stdout.strip():
        print(result.stdout.strip())
    return result


def detect_namespace():
    """Read the namespace from the pod's service account, when running in one."""
    try:
        with open(os.path.join(SERVICE_ACCOUNT_DIR, "namespace")) as f:
            return f.read().strip()
    except OSError:
        return None


def login(token):
    # The in-cluster API endpoint is used so the certificate is verified by
    # the cluster CA mounted in the pod — the external API URL may present a
    # certificate that CA does not sign. The token is passed as a separate
    # argument, not interpolated into a shell command line.
    run_oc(
        "login",
        "--token",
        token,
        "--server",
        "https://kubernetes.default.svc",
        "--certificate-authority",
        os.path.join(SERVICE_ACCOUNT_DIR, "ca.crt"),
    )


def wait_for_rollout(namespace, timeout):
    # Wait for the CURRENT rollout to complete — not just for any ready
    # replica. If the manifest was re-applied (or its env changed) while an
    # older pod was still running, a readyReplicas poll would see the old pod
    # and proceed before the new configuration is serving. `oc rollout status`
    # blocks until the latest rollout finishes or the Deployment's
    # progressDeadlineSeconds expires.
    result = subprocess.run(
        [
            "oc",
            "rollout",
            "status",
            f"deployment/{SERVICE_NAME}",
            "-n",
            namespace,
            f"--timeout={timeout}s",
        ],
        capture_output=True,
        text=True,
    )
    print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        print("Inspect the deployment:")
        print(f"  oc get pods -l app={SERVICE_NAME} -n {namespace}")
        print(f"  oc logs deployment/{SERVICE_NAME} -n {namespace}")
        raise RuntimeError(
            f"vLLM server rollout not complete after {timeout // 60} minutes"
        )


def check_health(endpoint):
    # The notebooks configure VLLM_ENDPOINT with a trailing /v1 (the
    # OpenAI-compatible API path); the health endpoint lives at the server
    # root. Both a transport failure and a non-2xx response stop the script.
    health_url = endpoint.rstrip("/").removesuffix("/v1") + "/health"
    try:
        with urllib.request.urlopen(
            health_url, timeout=HEALTH_CHECK_TIMEOUT_SECONDS
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"health check returned HTTP {resp.status}")
            print(f"Health check OK: {health_url}")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"health check failed for {health_url}: {exc}") from exc


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-n",
        "--namespace",
        default=detect_namespace(),
        help="Namespace to deploy into. Defaults to this pod's namespace when "
        "run inside a workbench, otherwise it must be given.",
    )
    parser.add_argument(
        "-t",
        "--token",
        default=os.environ.get("NOTEBOOK_USER_TOKEN"),
        help="oc login token of a user allowed to create Deployments/Services "
        "in the namespace. Defaults to $NOTEBOOK_USER_TOKEN — note this "
        "variable is only set inside the notebook kernel, not in workbench "
        "terminals. When no token is given, the existing oc login (if any) "
        "is used.",
    )
    parser.add_argument(
        "--hs-path",
        help="Set SPECULATOR_HS_PATH on the live deployment (container path; "
        "the shared PVC root maps to /mnt). Must match the trainer's "
        "hidden_states_path. The manifest default matches the OFFLINE "
        "notebook; the DATA_ONLY Method 2 example needs "
        "/mnt/speculator/<RUN_NAME>/hidden_states.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=ROLLOUT_TIMEOUT_SECONDS,
        help=f"Rollout wait in seconds (default: {ROLLOUT_TIMEOUT_SECONDS}, matching "
        "the Deployment's progressDeadlineSeconds).",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete the Deployment/Service/NetworkPolicy instead of deploying.",
    )
    parser.add_argument(
        "--manifest",
        default=MANIFEST_PATH,
        help=f"Path to the manifest to apply (default: {MANIFEST_PATH}).",
    )
    args = parser.parse_args()

    if not args.namespace:
        parser.error(
            "--namespace is required when not running inside a workbench pod "
            "(auto-detection failed)"
        )

    if args.token:
        login(args.token)
    else:
        # Fail fast with a clear message instead of raw oc credential errors
        # at apply time: without a token we depend on an existing oc login,
        # which may be absent or expired (workbench terminals start with none,
        # and NOTEBOOK_USER_TOKEN is not exported there).
        print("No token given — checking the existing oc login.")
        check = subprocess.run(["oc", "whoami"], capture_output=True, text=True)
        if check.returncode != 0:
            raise RuntimeError(
                "No token given and the existing oc login is missing or "
                "expired. Either:\n"
                "  - pass --token <token> (copy it from the notebook's "
                "'Authenticate to your OpenShift Cluster' cell, or from the "
                "OpenShift console: username dropdown -> 'Copy login command' "
                "-> 'Display token'),\n"
                "  - export NOTEBOOK_USER_TOKEN=<token> first (it is only "
                "set inside the notebook kernel, not in terminals), or\n"
                "  - run 'oc login' in this terminal before the script."
            )
        print(f"Logged in as {check.stdout.strip()} — continuing with that session.")

    if args.cleanup:
        run_oc("delete", "-f", args.manifest, "-n", args.namespace)
        print(
            f"Removed the {SERVICE_NAME} deployment, service, and network policy "
            f"from namespace {args.namespace}."
        )
        print("Hidden states and checkpoints on the PVC were NOT removed.")
        return

    run_oc("apply", "-f", args.manifest, "-n", args.namespace)

    if args.hs_path:
        # Set on the live deployment only — the checked-in manifest is not
        # modified, so its shipped default stays intact. This triggers a new
        # rollout, which the wait below covers.
        run_oc(
            "set",
            "env",
            f"deployment/{SERVICE_NAME}",
            f"SPECULATOR_HS_PATH={args.hs_path}",
            "-n",
            args.namespace,
        )

    wait_for_rollout(args.namespace, args.timeout)

    endpoint = (
        f"http://{SERVICE_NAME}.{args.namespace}.svc.cluster.local:{SERVICE_PORT}/v1"
    )
    check_health(endpoint)

    print()
    print("vLLM server is ready.")
    print(f"Set VLLM_ENDPOINT in the notebook to: {endpoint}")


if __name__ == "__main__":
    main()
