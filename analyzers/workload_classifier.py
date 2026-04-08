"""
WorkloadClassifier — resolve owner completo de um pod e classifica
o tipo de workload Kubernetes para orientar ações no nível correto.
"""
from dataclasses import dataclass, field
from typing import Optional


# Tipos de workload suportados
WORKLOAD_DEPLOYMENT = "Deployment"
WORKLOAD_STATEFULSET = "StatefulSet"
WORKLOAD_DAEMONSET = "DaemonSet"
WORKLOAD_JOB = "Job"
WORKLOAD_CRONJOB = "CronJob"
WORKLOAD_STANDALONE = "standalone"
WORKLOAD_UNKNOWN = "unknown"

# Workloads onde restart automático é seguro
SAFE_TO_RESTART = {WORKLOAD_DEPLOYMENT}

# Workloads onde restart requer aviso mas é permitido
RESTART_WITH_WARNING = {WORKLOAD_STATEFULSET, WORKLOAD_DAEMONSET}

# Workloads onde restart NÃO faz sentido
NO_RESTART = {WORKLOAD_JOB, WORKLOAD_CRONJOB}


@dataclass
class WorkloadInfo:
    """Resultado da classificação de workload para um pod."""
    pod_name: str
    namespace: str
    owner_kind: Optional[str] = None        # kind direto do pod (ex: ReplicaSet, StatefulSet)
    owner_name: Optional[str] = None        # nome direto do pod
    workload_kind: Optional[str] = None     # kind resolvido (ex: Deployment)
    workload_name: Optional[str] = None     # nome resolvido (ex: demo-nginx)
    workload_type: str = WORKLOAD_STANDALONE
    safe_to_restart: bool = False
    restart_warning: Optional[str] = None
    recommended_action: Optional[str] = None
    action_target: Optional[str] = None     # "deployment/demo-nginx" etc
    error: Optional[str] = None


class WorkloadClassifier:
    """
    Resolve a hierarquia completa de owner de um pod e classifica
    o tipo de workload para orientar ações de remediação.
    """

    def __init__(self, remediator):
        """remediator: instância com acesso ao kubectl."""
        self.remediator = remediator

    def classify(self, pod_name: str, namespace: str) -> WorkloadInfo:
        """
        Ponto de entrada único. Resolve owner e classifica workload.
        Sempre retorna WorkloadInfo — nunca lança exceção.
        """
        info = WorkloadInfo(pod_name=pod_name, namespace=namespace)
        try:
            return self._resolve(info)
        except Exception as e:
            info.error = str(e)
            info.workload_type = WORKLOAD_UNKNOWN
            return info

    def _get_owner_ref(self, resource_type: str, name: str, namespace: str) -> tuple:
        """
        Retorna (kind, name) do primeiro ownerReference do recurso.
        Retorna (None, None) se não encontrado ou erro.
        """
        import subprocess
        try:
            result = subprocess.run(
                [
                    "kubectl", "get", resource_type, name, "-n", namespace,
                    "-o", "jsonpath={.metadata.ownerReferences[0].kind}|{.metadata.ownerReferences[0].name}",
                ],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None, None
            parts = result.stdout.strip().split("|")
            if len(parts) != 2 or not parts[0] or not parts[1]:
                return None, None
            return parts[0].strip(), parts[1].strip()
        except Exception:
            return None, None

    def _resolve(self, info: WorkloadInfo) -> WorkloadInfo:
        """
        Resolve a cadeia de ownership do pod até o workload raiz.
        Cadeia: Pod → ReplicaSet → Deployment
                    → StatefulSet
                    → DaemonSet
                    → Job → CronJob
        """
        # Step 1: owner direto do pod
        kind, name = self._get_owner_ref("pod", info.pod_name, info.namespace)
        if not kind:
            info.workload_type = WORKLOAD_STANDALONE
            return self._apply_workload_rules(info)

        info.owner_kind = kind
        info.owner_name = name

        # Step 2: resolver cadeia por tipo
        if kind == "ReplicaSet":
            # ReplicaSet → Deployment?
            parent_kind, parent_name = self._get_owner_ref("replicaset", name, info.namespace)
            if parent_kind == "Deployment":
                info.workload_kind = WORKLOAD_DEPLOYMENT
                info.workload_name = parent_name
            else:
                info.workload_kind = "ReplicaSet"
                info.workload_name = name

        elif kind == "StatefulSet":
            info.workload_kind = WORKLOAD_STATEFULSET
            info.workload_name = name

        elif kind == "DaemonSet":
            info.workload_kind = WORKLOAD_DAEMONSET
            info.workload_name = name

        elif kind == "Job":
            info.workload_kind = WORKLOAD_JOB
            info.workload_name = name
            # Job → CronJob?
            parent_kind, parent_name = self._get_owner_ref("job", name, info.namespace)
            if parent_kind == "CronJob":
                info.workload_kind = WORKLOAD_CRONJOB
                info.workload_name = parent_name

        else:
            info.workload_kind = kind
            info.workload_name = name

        info.workload_type = info.workload_kind or WORKLOAD_UNKNOWN
        return self._apply_workload_rules(info)

    def _apply_workload_rules(self, info: WorkloadInfo) -> WorkloadInfo:
        """
        Aplica regras de remediação por tipo de workload.
        Define safe_to_restart, restart_warning, recommended_action e action_target.
        """
        wt = info.workload_type

        if wt == WORKLOAD_DEPLOYMENT:
            info.safe_to_restart = True
            info.restart_warning = None
            info.recommended_action = "rollout_restart_deployment"
            info.action_target = f"deployment/{info.workload_name}"

        elif wt == WORKLOAD_STATEFULSET:
            info.safe_to_restart = True
            info.restart_warning = (
                f"StatefulSet '{info.workload_name}' tem estado persistente. "
                "Rollout restart pode causar indisponibilidade temporária de pods com PVC."
            )
            info.recommended_action = "rollout_restart_statefulset"
            info.action_target = f"statefulset/{info.workload_name}"

        elif wt == WORKLOAD_DAEMONSET:
            info.safe_to_restart = True
            info.restart_warning = (
                f"DaemonSet '{info.workload_name}' roda em todos os nodes. "
                "Rollout restart afetará todos os nodes do cluster sequencialmente."
            )
            info.recommended_action = "rollout_restart_daemonset"
            info.action_target = f"daemonset/{info.workload_name}"

        elif wt == WORKLOAD_JOB:
            info.safe_to_restart = False
            info.restart_warning = None
            info.action_target = f"job/{info.workload_name}"
            info.recommended_action = "inspect_job"

        elif wt == WORKLOAD_CRONJOB:
            info.safe_to_restart = False
            info.restart_warning = None
            info.action_target = f"cronjob/{info.workload_name}"
            info.recommended_action = "inspect_cronjob"

        elif wt == WORKLOAD_STANDALONE:
            info.safe_to_restart = True
            info.restart_warning = None
            info.recommended_action = "delete_pod"
            info.action_target = f"pod/{info.pod_name}"

        else:
            info.safe_to_restart = False
            info.restart_warning = f"Tipo de workload '{wt}' não reconhecido — ação manual recomendada."
            info.recommended_action = None

        return info
