"""
Simulation / Chaos Mode — gerador de estado falso para teste do pipeline.

Fabrica dicts de status_data compatíveis com o que o pipeline consome
após get_pod_status, sem executar nenhum kubectl real.

Uso:
    from simulation.simulator import build_simulated_incident
    data = build_simulated_incident("crashloop")
"""

SUPPORTED_STATES = {"crashloop", "imagepull", "pending", "oomkilled"}

_STATE_MAP = {
    "crashloop": {
        "pod_name":      "simulated-pod-crashloop",
        "namespace":     "simulation",
        "parsed_status": "CrashLoopBackOff",
        "container_name": "app",
        "restart_count": 5,
    },
    "imagepull": {
        "pod_name":      "simulated-pod-imagepull",
        "namespace":     "simulation",
        "parsed_status": "ImagePullBackOff",
        "container_name": "app",
        "restart_count": 0,
    },
    "pending": {
        "pod_name":      "simulated-pod-pending",
        "namespace":     "simulation",
        "parsed_status": "Pending",
        "container_name": None,
        "restart_count": 0,
    },
    "oomkilled": {
        "pod_name":      "simulated-pod-oomkilled",
        "namespace":     "simulation",
        "parsed_status": "OOMKilled",
        "container_name": "app",
        "restart_count": 3,
    },
}


def build_simulated_incident(state: str) -> dict:
    """
    Retorna um dict de status_data compatível com o pipeline para o estado simulado.

    O dict retornado tem a mesma estrutura que parse_status_output(get_pod_status(...))
    retornaria para um pod real, e pode ser injetado diretamente no pipeline
    sem executar nenhum kubectl.

    Campos retornados:
        pod_name      — nome sintético do pod (simulated-pod-<state>)
        namespace     — namespace de simulação ("simulation")
        parsed_status — estado Kubernetes correspondente (ex: "CrashLoopBackOff")
        container_name — nome do container principal, ou None se não aplicável
        restart_count — número de reinicializações representativo do estado

    Args:
        state: um dos estados suportados: crashloop, imagepull, pending, oomkilled

    Returns:
        dict com os campos acima (cópia — mutações não afetam o mapa interno)

    Raises:
        ValueError: se state não for um dos SUPPORTED_STATES
    """
    normalized = state.strip().lower()
    if normalized not in SUPPORTED_STATES:
        raise ValueError(
            f"Estado '{state}' não suportado. "
            f"Estados válidos: {sorted(SUPPORTED_STATES)}"
        )
    return dict(_STATE_MAP[normalized])
