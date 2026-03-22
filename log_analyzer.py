from typing import Dict, Optional


def infer_probable_cause(log_text: Optional[str]) -> Dict[str, Optional[str]]:
    """
    Deterministic heuristic-based inference from pod logs.
    No external LLMs. Pure pattern matching.
    """
    text = (log_text or "").lower().strip()

    if not text:
        return {
            "probable_cause": None,
            "confidence": "low",
            "matched_pattern": None,
        }

    rules = [
        {
            "patterns": ["connection refused", "dial tcp", "connect: connection refused"],
            "probable_cause": "Dependent service may be unavailable or refusing connections.",
            "confidence": "medium",
            "matched_pattern": "connection refused",
        },
        {
            "patterns": ["permission denied", "operation not permitted"],
            "probable_cause": "Permission issue detected. Check container user, file permissions, or security context.",
            "confidence": "high",
            "matched_pattern": "permission denied",
        },
        {
            "patterns": ["no such file or directory", "file not found"],
            "probable_cause": "Missing file or invalid startup path. Check image contents, entrypoint, or mounted files.",
            "confidence": "high",
            "matched_pattern": "no such file or directory",
        },
        {
            "patterns": ["errimagepull", "imagepullbackoff", "pull access denied", "not found"],
            "probable_cause": "Container image could not be pulled. Check image name, tag, registry access, or imagePullSecrets.",
            "confidence": "medium",
            "matched_pattern": "image pull error",
        },
        {
            "patterns": ["exec format error"],
            "probable_cause": "Binary or image architecture mismatch.",
            "confidence": "high",
            "matched_pattern": "exec format error",
        },
        {
            "patterns": ["oomkilled", "out of memory", "cannot allocate memory"],
            "probable_cause": "Container may be hitting memory limits or exhausting available memory.",
            "confidence": "medium",
            "matched_pattern": "memory issue",
        },
    ]

    for rule in rules:
        for pattern in rule["patterns"]:
            if pattern in text:
                return {
                    "probable_cause": rule["probable_cause"],
                    "confidence": rule["confidence"],
                    "matched_pattern": rule["matched_pattern"],
                }

    return {
        "probable_cause": "Crash detected, but no known log pattern was matched.",
        "confidence": "low",
        "matched_pattern": None,
    }