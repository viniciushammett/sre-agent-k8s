import json
import subprocess
from typing import Optional, Tuple


def delete_pod(namespace: str, pod_name: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["kubectl", "delete", "pod", pod_name, "-n", namespace],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)


def list_pods(namespace: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)


def list_pods_wide(namespace: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-o", "wide", "-n", namespace],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)


def list_services(namespace: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["kubectl", "get", "svc", "-n", namespace],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)


def list_deployments(namespace: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["kubectl", "get", "deployments", "-n", namespace],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)


def describe_pod(namespace: str, pod_name: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["kubectl", "describe", "pod", pod_name, "-n", namespace],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)


def describe_service(namespace: str, service_name: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["kubectl", "describe", "svc", service_name, "-n", namespace],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)


def get_pod_logs(namespace: str, pod_name: str, container_name: Optional[str] = None) -> Tuple[bool, str]:
    try:
        cmd = ["kubectl", "logs", pod_name, "-n", namespace]
        if container_name:
            cmd.extend(["-c", container_name])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)


def get_pod_previous_logs(namespace: str, pod_name: str, container_name: Optional[str] = None) -> Tuple[bool, str]:
    try:
        cmd = ["kubectl", "logs", pod_name, "-n", namespace, "--previous"]
        if container_name:
            cmd.extend(["-c", container_name])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)


def get_pod_node(namespace: str, pod_name: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            [
                "kubectl", "get", "pod", pod_name,
                "-n", namespace,
                "-o", "jsonpath={.spec.nodeName}"
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)


def get_pod_status(namespace: str, pod_name: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["kubectl", "get", "pod", pod_name, "-n", namespace, "-o", "json"],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )

        pod_data = json.loads(result.stdout)
        phase = pod_data.get("status", {}).get("phase", "Unknown")

        container_statuses = pod_data.get("status", {}).get("containerStatuses", [])
        container_name = None
        container_state_reason = None
        restart_count = 0

        if container_statuses:
            first_container = container_statuses[0]
            container_name = first_container.get("name")
            restart_count = first_container.get("restartCount", 0)

            state = first_container.get("state", {})
            waiting = state.get("waiting")
            terminated = state.get("terminated")

            if waiting and waiting.get("reason"):
                container_state_reason = waiting["reason"]
            elif terminated and terminated.get("reason"):
                container_state_reason = terminated["reason"]

        parsed_status = container_state_reason or phase

        output = {
            "pod_name": pod_name,
            "namespace": namespace,
            "phase": phase,
            "container_name": container_name,
            "container_state_reason": container_state_reason,
            "restart_count": restart_count,
            "parsed_status": parsed_status,
        }

        return True, json.dumps(output, indent=2)
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)


def list_namespaces() -> Tuple[bool, str]:
    """Lista todos os namespaces do cluster."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "namespaces"],
            capture_output=True, text=True, timeout=15, check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)


def list_nodes() -> Tuple[bool, str]:
    """Lista todos os nodes do cluster."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "nodes"],
            capture_output=True, text=True, timeout=15, check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)


def list_all_pods() -> Tuple[bool, str]:
    """Lista todos os pods de todos os namespaces."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "--all-namespaces"],
            capture_output=True, text=True, timeout=15, check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.strip() or str(exc)
    except Exception as exc:
        return False, str(exc)