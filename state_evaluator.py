from typing import Dict, Optional, TypedDict


class PodContext(TypedDict, total=False):
    namespace: str
    pod_name: str
    container_name: str


class PodStateEvaluation(TypedDict):
    health_status: str
    requires_remediation: bool
    recommended_action: Optional[str]
    suggested_follow_up_action: Optional[str]
    suggested_follow_up_params: PodContext


def evaluate_pod_state(
    parsed_status: Optional[str],
    namespace: Optional[str] = None,
    pod_name: Optional[str] = None,
    container_name: Optional[str] = None,
) -> PodStateEvaluation:
    """
    Evaluate pod state and provide deterministic remediation guidance.
    """
    state = (parsed_status or "").strip()

    pod_context: PodContext = {}
    if namespace:
        pod_context["namespace"] = namespace
    if pod_name:
        pod_context["pod_name"] = pod_name
    if container_name:
        pod_context["container_name"] = container_name

    if not state:
        return {
            "health_status": "unknown",
            "requires_remediation": False,
            "recommended_action": None,
            "suggested_follow_up_action": None,
            "suggested_follow_up_params": {},
        }

    if state == "Running":
        return {
            "health_status": "healthy",
            "requires_remediation": False,
            "recommended_action": None,
            "suggested_follow_up_action": None,
            "suggested_follow_up_params": {},
        }

    if state == "CrashLoopBackOff":
        return {
            "health_status": "unhealthy",
            "requires_remediation": True,
            "recommended_action": "delete_pod",
            "suggested_follow_up_action": "get_pod_previous_logs",
            "suggested_follow_up_params": pod_context,
        }

    if state == "Error":
        return {
            "health_status": "unhealthy",
            "requires_remediation": False,
            "recommended_action": None,
            "suggested_follow_up_action": "get_pod_logs",
            "suggested_follow_up_params": pod_context,
        }

    if state == "ImagePullBackOff":
        follow_up_params: PodContext = {}
        if namespace:
            follow_up_params["namespace"] = namespace
        if pod_name:
            follow_up_params["pod_name"] = pod_name

        return {
            "health_status": "unhealthy",
            "requires_remediation": False,
            "recommended_action": None,
            "suggested_follow_up_action": "describe_pod",
            "suggested_follow_up_params": follow_up_params,
        }

    if state == "Pending":
        follow_up_params: PodContext = {}
        if namespace:
            follow_up_params["namespace"] = namespace
        if pod_name:
            follow_up_params["pod_name"] = pod_name

        return {
            "health_status": "unhealthy",
            "requires_remediation": False,
            "recommended_action": None,
            "suggested_follow_up_action": "describe_pod",
            "suggested_follow_up_params": follow_up_params,
        }

    return {
        "health_status": "unknown",
        "requires_remediation": False,
        "recommended_action": None,
        "suggested_follow_up_action": None,
        "suggested_follow_up_params": {},
    }
