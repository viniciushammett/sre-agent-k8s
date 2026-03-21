import subprocess
from datetime import datetime
from typing import Tuple


def log_info(message: str) -> None:
    print(f"[{datetime.now().isoformat()}] [INFO] {message}")


def log_error(message: str) -> None:
    print(f"[{datetime.now().isoformat()}] [ERROR] {message}")


def list_pods(namespace: str, wide: bool = False) -> Tuple[bool, str]:
    log_info(f"Listing pods in namespace={namespace} wide={wide}")
    try:
        command = ["kubectl", "get", "pods", "-n", namespace]
        if wide:
            command.extend(["-o", "wide"])

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        log_info(f"Pods listed successfully in namespace={namespace} wide={wide}")
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        error = exc.stderr.strip() or str(exc)
        log_error(f"Failed to list pods in namespace={namespace} wide={wide}: {error}")
        return False, error
    except Exception as exc:
        log_error(f"Unexpected error while listing pods in namespace={namespace} wide={wide}: {exc}")
        return False, str(exc)


def list_deployments(namespace: str) -> Tuple[bool, str]:
    log_info(f"Listing deployments in namespace={namespace}")
    try:
        result = subprocess.run(
            ["kubectl", "get", "deployments", "-n", namespace],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        log_info(f"Deployments listed successfully in namespace={namespace}")
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        error = exc.stderr.strip() or str(exc)
        log_error(f"Failed to list deployments in namespace={namespace}: {error}")
        return False, error
    except Exception as exc:
        log_error(f"Unexpected error while listing deployments in namespace={namespace}: {exc}")
        return False, str(exc)


def get_pod_status(namespace: str, pod_name: str) -> Tuple[bool, str]:
    log_info(f"Getting status for pod={pod_name} namespace={namespace}")
    try:
        result = subprocess.run(
            ["kubectl", "get", "pod", pod_name, "-n", namespace, "-o", "wide"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        log_info(f"Status retrieved successfully for pod={pod_name} namespace={namespace}")
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        error = exc.stderr.strip() or str(exc)
        log_error(f"Failed to get status for pod={pod_name} namespace={namespace}: {error}")
        return False, error
    except Exception as exc:
        log_error(f"Unexpected error while getting status for pod={pod_name} namespace={namespace}: {exc}")
        return False, str(exc)


def describe_pod(namespace: str, pod_name: str) -> Tuple[bool, str]:
    log_info(f"Describing pod={pod_name} namespace={namespace}")
    try:
        result = subprocess.run(
            ["kubectl", "describe", "pod", pod_name, "-n", namespace],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        log_info(f"Describe retrieved successfully for pod={pod_name} namespace={namespace}")
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        error = exc.stderr.strip() or str(exc)
        log_error(f"Failed to describe pod={pod_name} namespace={namespace}: {error}")
        return False, error
    except Exception as exc:
        log_error(f"Unexpected error while describing pod={pod_name} namespace={namespace}: {exc}")
        return False, str(exc)


def describe_service(namespace: str, service_name: str) -> Tuple[bool, str]:
    log_info(f"Describing service={service_name} namespace={namespace}")
    try:
        result = subprocess.run(
            ["kubectl", "describe", "svc", service_name, "-n", namespace],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        log_info(f"Describe retrieved successfully for service={service_name} namespace={namespace}")
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        error = exc.stderr.strip() or str(exc)
        log_error(f"Failed to describe service={service_name} namespace={namespace}: {error}")
        return False, error
    except Exception as exc:
        log_error(f"Unexpected error while describing service={service_name} namespace={namespace}: {exc}")
        return False, str(exc)


def delete_pod(namespace: str, pod_name: str) -> Tuple[bool, str]:
    log_info(f"Deleting pod={pod_name} namespace={namespace}")
    try:
        result = subprocess.run(
            ["kubectl", "delete", "pod", pod_name, "-n", namespace],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        log_info(f"Pod deleted successfully pod={pod_name} namespace={namespace}")
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        error = exc.stderr.strip() or str(exc)
        log_error(f"Failed to delete pod={pod_name} namespace={namespace}: {error}")
        return False, error
    except Exception as exc:
        log_error(f"Unexpected error while deleting pod={pod_name} namespace={namespace}: {exc}")
        return False, str(exc)


def list_services(namespace: str) -> Tuple[bool, str]:
    log_info(f"Listing services in namespace={namespace}")
    try:
        result = subprocess.run(
            ["kubectl", "get", "svc", "-n", namespace],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        log_info(f"Services listed successfully in namespace={namespace}")
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        error = exc.stderr.strip() or str(exc)
        log_error(f"Failed to list services in namespace={namespace}: {error}")
        return False, error
    except Exception as exc:
        log_error(f"Unexpected error while listing services in namespace={namespace}: {exc}")
        return False, str(exc)


def get_pod_node(namespace: str, pod_name: str) -> Tuple[bool, str]:
    log_info(f"Getting node for pod={pod_name} namespace={namespace}")
    try:
        result = subprocess.run(
            ["kubectl", "get", "pod", pod_name, "-n", namespace, "-o", "wide"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        lines = result.stdout.strip().splitlines()
        if len(lines) < 2:
            log_error(f"Unexpected kubectl output for pod={pod_name} namespace={namespace}")
            return False, "Unexpected kubectl output"

        header = lines[0].split()
        values = lines[1].split()

        if "NODE" not in header:
            log_error(f"NODE column not found in kubectl output for pod={pod_name} namespace={namespace}")
            return False, "NODE column not found in kubectl output"

        node_index = header.index("NODE")
        if len(values) <= node_index:
            log_error(f"Could not extract node from kubectl output for pod={pod_name} namespace={namespace}")
            return False, "Could not extract node from kubectl output"

        node_name = values[node_index]
        log_info(f"Node retrieved successfully for pod={pod_name} namespace={namespace}: node={node_name}")
        return True, node_name
    except subprocess.CalledProcessError as exc:
        error = exc.stderr.strip() or str(exc)
        log_error(f"Failed to get node for pod={pod_name} namespace={namespace}: {error}")
        return False, error
    except Exception as exc:
        log_error(f"Unexpected error while getting node for pod={pod_name} namespace={namespace}: {exc}")
        return False, str(exc)


def get_pod_logs(namespace: str, pod_name: str) -> Tuple[bool, str]:
    log_info(f"Getting logs for pod={pod_name} namespace={namespace}")
    try:
        result = subprocess.run(
            ["kubectl", "logs", pod_name, "-n", namespace, "--tail", "50"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        log_info(f"Logs retrieved successfully for pod={pod_name} namespace={namespace}")
        return True, result.stdout.strip() or "(no logs returned)"
    except subprocess.CalledProcessError as exc:
        error = exc.stderr.strip() or str(exc)
        log_error(f"Failed to get logs for pod={pod_name} namespace={namespace}: {error}")
        return False, error
    except Exception as exc:
        log_error(f"Unexpected error while getting logs for pod={pod_name} namespace={namespace}: {exc}")
        return False, str(exc)