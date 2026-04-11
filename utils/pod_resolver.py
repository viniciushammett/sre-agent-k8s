"""
PodResolver — resolve nomes parciais de pods para nomes reais.

Quando o usuário informa um prefixo ou nome base (ex: payment-worker),
resolve para o pod real (ex: payment-worker-698f78f485-rh7r6).
"""
import subprocess
from typing import Optional


def list_pods_in_namespace(namespace: str) -> list:
    """Retorna lista de nomes de pods no namespace. Retorna [] se erro."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace,
             "-o", "jsonpath={.items[*].metadata.name}"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        return result.stdout.strip().split()
    except Exception:
        return []


def resolve_pod_name(
    pod_name: str,
    namespace: str,
    last_pod: Optional[str] = None,
) -> dict:
    """
    Resolve nome parcial de pod para nome real.

    Retorna dict com:
        resolved: str | None — nome resolvido
        status: "exact" | "resolved" | "ambiguous" | "not_found" | "no_namespace"
        candidates: list[str] — candidatos se ambíguo
        message: str — mensagem para o usuário
    """
    if not namespace:
        return {
            "resolved": None,
            "status": "no_namespace",
            "candidates": [],
            "message": "Namespace não definido. Use: set namespace <nome>",
        }

    # tentar match exato primeiro
    pods = list_pods_in_namespace(namespace)
    if pod_name in pods:
        return {
            "resolved": pod_name,
            "status": "exact",
            "candidates": [],
            "message": "",
        }

    # tentar resolução por prefixo
    matches = [p for p in pods if p.startswith(pod_name)]

    if len(matches) == 1:
        return {
            "resolved": matches[0],
            "status": "resolved",
            "candidates": [],
            "message": f"Resolved pod: {matches[0]}",
        }

    if len(matches) > 1:
        return {
            "resolved": None,
            "status": "ambiguous",
            "candidates": matches,
            "message": (
                f"Múltiplos pods encontrados com prefixo '{pod_name}':\n"
                + "\n".join(f"  · {m}" for m in matches)
                + "\nUse o nome completo para especificar."
            ),
        }

    # não encontrado — sugerir last_pod se disponível
    if last_pod:
        return {
            "resolved": None,
            "status": "not_found",
            "candidates": [],
            "message": (
                f"Pod '{pod_name}' não encontrado em '{namespace}'.\n"
                f"Último pod usado: {last_pod}"
            ),
        }

    return {
        "resolved": None,
        "status": "not_found",
        "candidates": [],
        "message": f"Pod '{pod_name}' não encontrado no namespace '{namespace}'.",
    }
