import re
from typing import Dict, Any


def suggest_remediation(incident: str) -> Dict[str, Any]:
    text = incident.strip().lower()

    match = re.search(
        r"(?:list|show)\s+pods?(?:\s+wide)?(?:\s+running)?"
        r"\s+in\s+(?:namespace\s+)?([a-z0-9-]+)(?:\s+namespace)?",
        text,
    )
    if match:
        namespace = match.group(1)
        wide_flag = "wide" in text
        return {
            "action": "list_pods_wide" if wide_flag else "list_pods",
            "params": {"namespace": namespace},
            "reason": f"User requested pod listing for namespace {namespace} with wide={wide_flag}.",
        }

    match = re.search(r"(?:list|show)\s+deployments\s+in\s+namespace\s+([a-z0-9-]+)", text)
    if match:
        namespace = match.group(1)
        return {
            "action": "list_deployments",
            "params": {"namespace": namespace},
            "reason": f"User requested deployment listing for namespace {namespace}.",
        }

    match = re.search(r"(?:check|status of)\s+pod\s+([a-z0-9-]+)\s+in\s+namespace\s+([a-z0-9-]+)", text)
    if match:
        pod_name, namespace = match.group(1), match.group(2)
        return {
            "action": "get_pod_status",
            "params": {"namespace": namespace, "pod_name": pod_name},
            "reason": f"User requested status for pod {pod_name} in namespace {namespace}.",
        }

    match = re.search(r"(?:describe pod|show details for pod)\s+([a-z0-9-]+)\s+in\s+namespace\s+([a-z0-9-]+)", text)
    if match:
        pod_name, namespace = match.group(1), match.group(2)
        return {
            "action": "describe_pod",
            "params": {"namespace": namespace, "pod_name": pod_name},
            "reason": f"User requested detailed description for pod {pod_name} in namespace {namespace}.",
        }

    match = re.search(r"(?:describe service|show details for service)\s+([a-z0-9-]+)\s+in\s+namespace\s+([a-z0-9-]+)", text)
    if match:
        service_name, namespace = match.group(1), match.group(2)
        return {
            "action": "describe_service",
            "params": {"namespace": namespace, "service_name": service_name},
            "reason": f"User requested detailed description for service {service_name} in namespace {namespace}.",
        }

    match = re.search(
        r"pod\s+([a-z0-9-]+)\s+is\s+in\s+crashloopbackoff\s+in\s+namespace\s+([a-z0-9-]+).*(?:restart pod|please restart|restart)",
        text,
    )
    if match:
        pod_name, namespace = match.group(1), match.group(2)
        return {
            "action": "delete_pod",
            "params": {"namespace": namespace, "pod_name": pod_name},
            "reason": f"Pod {pod_name} is reported in CrashLoopBackOff in namespace {namespace}; restarting pod by deletion was requested.",
        }

    match = re.search(r"(?:restart|delete)\s+pod\s+([a-z0-9-]+)\s+in\s+namespace\s+([a-z0-9-]+)", text)
    if match:
        pod_name, namespace = match.group(1), match.group(2)
        return {
            "action": "delete_pod",
            "params": {"namespace": namespace, "pod_name": pod_name},
            "reason": f"User requested restart/delete for pod {pod_name} in namespace {namespace}.",
        }

    match = re.search(r"(?:list|show)\s+services\s+in\s+namespace\s+([a-z0-9-]+)", text)
    if match:
        namespace = match.group(1)
        return {
            "action": "list_services",
            "params": {"namespace": namespace},
            "reason": f"User requested service listing for namespace {namespace}.",
        }

    match = re.search(
        r"(?:which node is pod|what node is pod)\s+([a-z0-9-]+)\s+(?:running on|on)\s+in\s+namespace\s+([a-z0-9-]+)",
        text,
    )
    if match:
        pod_name, namespace = match.group(1), match.group(2)
        return {
            "action": "get_pod_node",
            "params": {"namespace": namespace, "pod_name": pod_name},
            "reason": f"User requested node information for pod {pod_name} in namespace {namespace}.",
        }

    match = re.search(r"(?:show|get)\s+logs\s+for\s+pod\s+([a-z0-9-]+)\s+in\s+namespace\s+([a-z0-9-]+)", text)
    if match:
        pod_name, namespace = match.group(1), match.group(2)
        return {
            "action": "get_pod_logs",
            "params": {"namespace": namespace, "pod_name": pod_name},
            "reason": f"User requested logs for pod {pod_name} in namespace {namespace}.",
        }

    match = re.search(r"(?:list|show)\s+(?:all\s+)?namespaces?", text)
    if match:
        return {
            "action": "list_namespaces",
            "params": {},
            "reason": "User requested namespace listing.",
        }

    match = re.search(r"(?:list|show)\s+(?:all\s+)?nodes?", text)
    if match:
        return {
            "action": "list_nodes",
            "params": {},
            "reason": "User requested node listing.",
        }

    match = re.search(
        r"(?:list|show)\s+all\s+pods?\s*(?:running)?(?:\s+in\s+(?:all\s+)?namespaces?)?",
        text,
    )
    if match:
        return {
            "action": "list_all_pods",
            "params": {},
            "reason": "User requested pod listing across all namespaces.",
        }

    match = re.search(r"(?:list|show)\s+pods?(?:\s+running)?$", text)
    if match:
        return {
            "action": "list_pods",
            "params": {},
            "reason": "User requested pod listing. Namespace will be inferred from session context.",
        }

    match = re.search(r"^(?:show\s+)?logs?$", text)
    if match:
        return {
            "action": "get_pod_logs",
            "params": {},
            "reason": "User requested logs. Pod and namespace will be inferred from session context.",
        }

    match = re.search(r"^show\s+previous\s+logs?$", text)
    if match:
        return {
            "action": "get_pod_previous_logs",
            "params": {},
            "reason": "User requested previous logs. Pod and namespace will be inferred from session context.",
        }

    match = re.search(r"^describe\s+pod\s+([a-z0-9-]+)$", text)
    if match:
        pod_name = match.group(1)
        return {
            "action": "describe_pod",
            "params": {"pod_name": pod_name},
            "reason": f"User requested describe for pod {pod_name}. Namespace will be inferred from session context.",
        }

    match = re.search(r"^(?:check|status of)\s+pod\s+([a-z0-9-]+)$", text)
    if match:
        pod_name = match.group(1)
        return {
            "action": "get_pod_status",
            "params": {"pod_name": pod_name},
            "reason": f"User requested status for pod {pod_name}. Namespace will be inferred from session context.",
        }

    match = re.search(r"^restart\s+pod\s+([a-z0-9-]+)$", text)
    if match:
        pod_name = match.group(1)
        return {
            "action": "delete_pod",
            "params": {"pod_name": pod_name},
            "reason": f"User requested restart for pod {pod_name}. Namespace will be inferred from session context.",
        }

    return {
        "action": None,
        "params": {},
        "reason": (
            "No remediation rule matched. Try examples like: "
            "'please list pods in namespace default', "
            "'please list pods wide in namespace default', "
            "'list deployments in namespace default', "
            "'describe pod nginx-test in namespace default', "
            "'describe service nginx-test in namespace default', "
            "'which node is pod nginx-test running on in namespace default', "
            "'please list services in namespace default', "
            "'show logs for pod nginx-test in namespace default', "
            "'check pod nginx-test in namespace default', or "
            "'pod nginx-test is in CrashLoopBackOff in namespace default, please restart pod'."
        ),
    }


# Ações que são simples requests de leitura — sem pipeline de remediação
_REQUEST_ACTIONS = {
    "list_pods",
    "list_pods_wide",
    "list_services",
    "list_deployments",
    "list_namespaces",
    "list_nodes",
    "list_all_pods",
    "describe_pod",
    "describe_service",
    "get_pod_logs",
    "get_pod_previous_logs",
    "get_pod_node",
}


def classify_input(action: str | None) -> str:
    """
    Retorna 'request' para operações simples de leitura,
    ou 'incident' para operações que requerem pipeline completo.
    """
    if action in _REQUEST_ACTIONS:
        return "request"
    return "incident"