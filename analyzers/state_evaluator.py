def evaluate_pod_state(status_data: dict) -> dict:
    parsed_status = status_data.get("parsed_status", "Unknown")
    pod_name = status_data.get("pod_name", "unknown-pod")
    namespace = status_data.get("namespace", "default")

    if parsed_status == "Running":
        return {
            "state_detected": "Running",
            "health_status": "healthy",
            "requires_remediation": False,
            "recommended_action": None,
            "recommended_params": {},
            "reason": f"Pod {pod_name} in namespace {namespace} is healthy and running normally.",
        }

    if parsed_status == "CrashLoopBackOff":
        return {
            "state_detected": "CrashLoopBackOff",
            "health_status": "unhealthy",
            "requires_remediation": True,
            "recommended_action": "delete_pod",
            "recommended_params": {
                "namespace": namespace,
                "pod_name": pod_name,
            },
            "reason": f"Pod {pod_name} in namespace {namespace} is in CrashLoopBackOff.",
        }

    if parsed_status == "Error":
        return {
            "state_detected": "Error",
            "health_status": "unhealthy",
            "requires_remediation": False,
            "recommended_action": None,
            "recommended_params": {},
            "reason": f"Pod {pod_name} in namespace {namespace} is in Error state. Auto-remediation policy is not defined for this state.",
        }

    if parsed_status == "ImagePullBackOff":
        return {
            "state_detected": "ImagePullBackOff",
            "health_status": "unhealthy",
            "requires_remediation": False,
            "recommended_action": None,
            "recommended_params": {},
            "reason": f"Pod {pod_name} in namespace {namespace} is in ImagePullBackOff. Manual investigation is recommended.",
        }

    if parsed_status == "Pending":
        return {
            "state_detected": "Pending",
            "health_status": "unhealthy",
            "requires_remediation": False,
            "recommended_action": None,
            "recommended_params": {},
            "reason": f"Pod {pod_name} in namespace {namespace} is Pending. Auto-remediation policy is not defined for this state.",
        }

    return {
        "state_detected": parsed_status,
        "health_status": "unknown",
        "requires_remediation": False,
        "recommended_action": None,
        "recommended_params": {},
        "reason": f"Pod {pod_name} in namespace {namespace} is in state {parsed_status}. No auto-remediation policy is defined for this state.",
    }