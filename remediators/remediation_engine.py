from typing import Dict, Any

from remediators.kubectl_remediator import (
    delete_pod,
    get_pod_details,
    get_pods,
    pod_exists,
)


ALLOWED_NAMESPACES = {"default", "lab", "testing"}


def execute_remediation(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    namespace = params.get("namespace")

    if action == "list_pods":
        if not namespace:
            return {
                "success": False,
                "message": "Missing namespace for list_pods action.",
                "action": action,
                "params": params,
            }

        if namespace not in ALLOWED_NAMESPACES:
            return {
                "success": False,
                "message": f"Namespace '{namespace}' is not allowed for remediation.",
                "action": action,
                "params": params,
            }

        success, output = get_pods(namespace)
        return {
            "success": success,
            "message": output,
            "action": action,
            "params": params,
        }

    if action == "get_pod":
        pod_name = params.get("pod_name")

        if not namespace or not pod_name:
            return {
                "success": False,
                "message": "Missing namespace or pod_name for get_pod action.",
                "action": action,
                "params": params,
            }

        if namespace not in ALLOWED_NAMESPACES:
            return {
                "success": False,
                "message": f"Namespace '{namespace}' is not allowed for remediation.",
                "action": action,
                "params": params,
            }

        success, output = get_pod_details(namespace, pod_name)
        return {
            "success": success,
            "message": output,
            "action": action,
            "params": params,
        }

    if action == "delete_pod":
        pod_name = params.get("pod_name")

        if not namespace or not pod_name:
            return {
                "success": False,
                "message": "Missing namespace or pod_name for delete_pod action.",
                "action": action,
                "params": params,
            }

        if namespace not in ALLOWED_NAMESPACES:
            return {
                "success": False,
                "message": f"Namespace '{namespace}' is not allowed for remediation.",
                "action": action,
                "params": params,
            }

        pod_found, pod_check_message = pod_exists(namespace, pod_name)
        if not pod_found:
            return {
                "success": False,
                "message": f"Pre-check failed: {pod_check_message}",
                "action": action,
                "params": params,
            }

        success, output = delete_pod(namespace, pod_name)

        return {
            "success": success,
            "message": output,
            "action": action,
            "params": params,
        }

    return {
        "success": False,
        "message": f"Unsupported remediation action: {action}",
        "action": action,
        "params": params,
    }