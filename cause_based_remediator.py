from typing import Dict, List, Optional, TypedDict


class RemediationPlan(TypedDict):
    matched_pattern: Optional[str]
    recommended_checks: List[str]
    safe_remediation: Optional[str]
    requires_human_review: bool
    explanation: Optional[str]


# Matriz de regras: matched_pattern -> plano de ação determinístico
_RULES: List[Dict] = [
    {
        "matched_pattern": "connection refused",
        "recommended_checks": [
            "kubectl get pods -n <namespace>",
            "kubectl get endpoints -n <namespace>",
            "kubectl get networkpolicy -n <namespace>",
            "kubectl logs <pod> -n <namespace>",
        ],
        "safe_remediation": "kubectl get endpoints -n <namespace>",
        "requires_human_review": False,
        "explanation": "Dependent service may be unavailable or refusing connections. Check if downstream services are running and reachable.",
    },
    {
        "matched_pattern": "permission denied",
        "recommended_checks": [
            "kubectl get pod <pod> -n <namespace> -o jsonpath='{.spec.securityContext}'",
            "kubectl get pod <pod> -n <namespace> -o jsonpath='{.spec.containers[*].securityContext}'",
            "kubectl auth can-i --list --as=system:serviceaccount:<namespace>:<sa>",
        ],
        "safe_remediation": None,
        "requires_human_review": True,
        "explanation": "Permission denied in container. Security context, file permissions, or RBAC must be reviewed and corrected in the workload spec.",
    },
    {
        "matched_pattern": "exec format error",
        "recommended_checks": [
            "kubectl get nodes -o wide",
            "kubectl get pod <pod> -n <namespace> -o jsonpath='{.spec.containers[*].image}'",
        ],
        "safe_remediation": None,
        "requires_human_review": True,
        "explanation": "Binary or image architecture mismatch. Image was built for a different CPU architecture than the node. Must be rebuilt for the correct platform.",
    },
    {
        "matched_pattern": "memory issue",
        "recommended_checks": [
            "kubectl get pod <pod> -n <namespace> -o jsonpath='{.spec.containers[*].resources}'",
            "kubectl top pod <pod> -n <namespace>",
            "kubectl describe pod <pod> -n <namespace>",
        ],
        "safe_remediation": "kubectl describe pod <pod> -n <namespace>",
        "requires_human_review": True,
        "explanation": "Container was OOMKilled or exhausted available memory. Review memory limits and application memory usage pattern.",
    },
    {
        "matched_pattern": "image pull error",
        "recommended_checks": [
            "kubectl get pod <pod> -n <namespace> -o jsonpath='{.spec.containers[*].image}'",
            "kubectl get secret -n <namespace>",
            "kubectl describe pod <pod> -n <namespace>",
        ],
        "safe_remediation": "kubectl describe pod <pod> -n <namespace>",
        "requires_human_review": True,
        "explanation": "Container image could not be pulled. Check image name, tag, registry access, or imagePullSecrets.",
    },
]


def plan_next_steps(matched_pattern: Optional[str]) -> RemediationPlan:
    """
    Returns a deterministic remediation plan based on the matched_pattern
    produced by log_analyzer.infer_probable_cause().

    No external calls, no LLM, no heuristics beyond direct key lookup.
    """
    if matched_pattern:
        for rule in _RULES:
            if rule["matched_pattern"] == matched_pattern:
                return {
                    "matched_pattern": matched_pattern,
                    "recommended_checks": rule["recommended_checks"],
                    "safe_remediation": rule["safe_remediation"],
                    "requires_human_review": rule["requires_human_review"],
                    "explanation": rule["explanation"],
                }

    return {
        "matched_pattern": matched_pattern,
        "recommended_checks": [
            "kubectl logs <pod> -n <namespace>",
            "kubectl describe pod <pod> -n <namespace>",
        ],
        "safe_remediation": None,
        "requires_human_review": True,
        "explanation": "No specific rule matched. Manual investigation required.",
    }
