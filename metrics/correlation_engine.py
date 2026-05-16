"""
Correlaciona sinais de estado, logs, métricas e eventos para diagnóstico consolidado.
"""
import logging

logger = logging.getLogger(__name__)

_RELEVANT_EVENT_REASONS = {
    "BackOff", "OOMKilling", "Failed", "FailedScheduling",
    "Unhealthy", "FailedMount",
}


def correlate_signals(
    state: dict,
    log_analysis: dict,
    metrics: dict,
    events: list,
) -> dict:
    """Consolida sinais de estado, logs, métricas e eventos em diagnóstico único."""
    try:
        root_cause = _resolve_root_cause(state, log_analysis, metrics)
        contributing_factors = _collect_factors(log_analysis, metrics, events)
        confidence = _resolve_confidence(log_analysis, state, metrics, contributing_factors)
        recommended_action = _resolve_action(root_cause)

        return {
            "confidence": confidence,
            "root_cause": root_cause,
            "contributing_factors": contributing_factors,
            "recommended_action": recommended_action,
        }
    except Exception as exc:
        logger.warning("correlate_signals failed: %s", exc)
        return {
            "confidence": "low",
            "root_cause": "Correlation failed — internal error",
            "contributing_factors": [],
            "recommended_action": "Investigate manually — no automated action recommended",
        }


def _resolve_root_cause(state: dict, log_analysis: dict, metrics: dict) -> str:
    log_confidence = log_analysis.get("confidence", "none")
    log_cause = log_analysis.get("cause")
    status = state.get("status", "")

    if log_confidence in ("high", "medium") and log_cause:
        return log_cause

    if status == "OOMKilled" and metrics.get("memory_pressure"):
        return "OOMKilled confirmed by memory metrics"

    if status == "CrashLoopBackOff":
        return "CrashLoopBackOff — check logs and config"

    if status == "Pending":
        return "Pod pending — check resources or scheduling"

    if status == "ImagePullBackOff":
        return "Image pull failure — check image name and registry"

    return "Undetermined — insufficient signal"


def _collect_factors(log_analysis: dict, metrics: dict, events: list) -> list:
    factors = []

    if metrics.get("available"):
        if metrics.get("cpu_pressure"):
            val = metrics.get("cpu_millicores")
            factors.append(f"High CPU usage ({val}m)")
        if metrics.get("memory_pressure"):
            val = metrics.get("memory_mib")
            factors.append(f"High memory usage ({val}MiB)")
    else:
        factors.append("Prometheus unavailable — metrics not considered")

    log_confidence = log_analysis.get("confidence", "none")
    if log_confidence == "low":
        factors.append("Low confidence log analysis")
    elif log_confidence == "none":
        factors.append("No log signal detected")

    for event in events:
        reason = event.get("reason", "")
        if reason in _RELEVANT_EVENT_REASONS:
            message = event.get("message", "")[:80]
            factors.append(f"Event: {reason} — {message}")

    return factors


def _resolve_confidence(
    log_analysis: dict, state: dict, metrics: dict, contributing_factors: list
) -> str:
    log_confidence = log_analysis.get("confidence", "none")

    if log_confidence == "high":
        return "high"

    if log_confidence == "medium":
        return "medium"

    status = state.get("status", "")
    if status == "OOMKilled" and metrics.get("memory_pressure"):
        return "medium"

    useful = [f for f in contributing_factors if "Prometheus unavailable" not in f]
    if useful:
        return "low"

    return "low"


def _resolve_action(root_cause: str) -> str:
    rc = root_cause.lower()
    if "oomkilled" in rc:
        return "Increase memory limits or investigate memory leak"
    if "crashloopbackoff" in rc:
        return "Inspect pod logs and check application configuration"
    if "pending" in rc:
        return "Check node resources, taints, and PVC availability"
    if "image pull" in rc:
        return "Verify image name, tag, and registry credentials"
    return "Investigate manually — no automated action recommended"
