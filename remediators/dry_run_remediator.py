"""
DryRunRemediator — wrapper que simula ações destrutivas sem executar kubectl.
Chamadas de leitura são delegadas ao remediator real.
"""

DESTRUCTIVE_ACTIONS = {
    "delete_pod",
    "rollout_restart_deployment",
}

READ_ONLY_ACTIONS = {
    "get_pod_status",
    "get_pod_logs",
    "get_pod_previous_logs",
    "describe_pod",
    "describe_service",
    "list_pods",
    "list_pods_wide",
    "list_services",
    "list_deployments",
    "list_namespaces",
    "list_nodes",
    "list_all_pods",
    "get_pod_node",
    "get_pod_owner",
}


class DryRunRemediator:
    """
    Wrapper sobre KubectlRemediator para modo dry-run.
    Ações destrutivas são simuladas — nunca executam kubectl real.
    Ações de leitura são delegadas normalmente.
    """

    def __init__(self, real_remediator):
        self._real = real_remediator

    def delete_pod(self, namespace: str, pod_name: str):
        return (
            True,
            f"[DRY-RUN] delete pod '{pod_name}' in namespace '{namespace}' — simulado, não executado.",
        )

    def rollout_restart_deployment(self, namespace: str, deployment_name: str):
        return (
            True,
            f"[DRY-RUN] rollout restart deployment '{deployment_name}' in namespace '{namespace}' — simulado, não executado.",
        )

    def __getattr__(self, name):
        """
        Delega qualquer método não definido aqui para o remediator real.
        Isso cobre todos os métodos de leitura sem precisar redefinir cada um.
        """
        return getattr(self._real, name)
