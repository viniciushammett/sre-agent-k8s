"""
Diagnosis Engine — investigação guiada determinística por estado de workload.

Fornece DiagnosisEngine com handlers específicos para cada estado:
    CrashLoopBackOff        — previous logs + describe + restart count
    OOMKilled               — previous logs + memory limits
    ImagePullBackOff        — describe + image/registry info
    ErrImagePull            — describe + image/registry info
    Pending                 — describe + scheduling constraints
    CreateContainerConfigError — describe + secret/configmap/volume
    CreateContainerError    — describe + secret/configmap/volume
    Running (unhealthy)     — logs + liveness/readiness probe info

Categorias de causa padronizadas:
    application_error, dependency_unavailable, configuration_error,
    image_runtime_problem, scheduling_resource_problem, permission_security_problem
"""
from dataclasses import dataclass, field
from typing import Optional


CAUSE_APPLICATION_ERROR = "application_error"
CAUSE_DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
CAUSE_CONFIGURATION_ERROR = "configuration_error"
CAUSE_IMAGE_RUNTIME_PROBLEM = "image_runtime_problem"
CAUSE_SCHEDULING_RESOURCE = "scheduling_resource_problem"
CAUSE_PERMISSION_SECURITY = "permission_security_problem"
CAUSE_UNKNOWN = "unknown"


@dataclass
class DiagnosisReport:
    """Resultado da investigação guiada por estado."""
    state: str
    cause_category: Optional[str] = None
    hypothesis: Optional[str] = None
    evidence: list = field(default_factory=list)
    recommended_actions: list = field(default_factory=list)
    safe_to_automate: bool = False
    requires_human_review: bool = False
    confidence: str = "low"  # low | medium | high


class DiagnosisEngine:
    """
    Investigação guiada determinística por estado de workload.
    Recebe estado detectado e executa coleta encadeada de evidências.
    """

    KNOWN_STATES = {
        "CrashLoopBackOff",
        "OOMKilled",
        "ImagePullBackOff",
        "ErrImagePull",
        "Pending",
        "CreateContainerConfigError",
        "CreateContainerError",
        "Running",
    }

    def __init__(self, remediator):
        """
        remediator: instância de KubectlRemediator para executar coletas.
        """
        self.remediator = remediator

    def investigate(self, state: str, pod_name: str, namespace: str, container_name: str = None) -> DiagnosisReport:
        """
        Ponto de entrada único. Despacha para o handler correto por estado.
        Retorna DiagnosisReport sempre — nunca lança exceção.
        """
        report = DiagnosisReport(state=state)

        try:
            if state == "CrashLoopBackOff":
                return self._investigate_crashloop(pod_name, namespace, container_name)
            elif state == "OOMKilled":
                return self._investigate_oomkilled(pod_name, namespace, container_name)
            elif state in ("ImagePullBackOff", "ErrImagePull"):
                return self._investigate_imagepull(pod_name, namespace, state)
            elif state == "Pending":
                return self._investigate_pending(pod_name, namespace)
            elif state in ("CreateContainerConfigError", "CreateContainerError"):
                return self._investigate_container_config(pod_name, namespace)
            elif state == "Running":
                return self._investigate_running_unhealthy(pod_name, namespace, container_name)
            else:
                report.hypothesis = f"Estado '{state}' não possui handler de diagnóstico."
                return report
        except Exception as e:
            report.hypothesis = f"Erro durante diagnóstico: {str(e)}"
            return report

    def _investigate_crashloop(self, pod_name, namespace, container_name):
        report = DiagnosisReport(state="CrashLoopBackOff")
        report.cause_category = CAUSE_APPLICATION_ERROR
        evidence = []

        # Coleta 1: previous logs
        prev_logs = self.remediator.get_pod_previous_logs(pod_name, namespace)
        if prev_logs and "error" not in prev_logs.lower()[:20]:
            evidence.append(f"previous_logs: {prev_logs[:300]}")
            report.confidence = "medium"
        else:
            evidence.append("previous_logs: não disponíveis ou vazios")

        # Coleta 2: describe pod (last state + restart count)
        describe = self.remediator.describe_pod(pod_name, namespace)
        if describe:
            evidence.append(f"describe: coletado ({len(describe)} chars)")
            for line in describe.splitlines():
                if "restart count" in line.lower():
                    evidence.append(f"restart_info: {line.strip()}")
                    report.confidence = "high"
                    break

        report.evidence = evidence
        report.hypothesis = (
            "Pod está reiniciando repetidamente. Causa mais provável: "
            "erro na aplicação, dependência indisponível ou configuração incorreta."
        )
        report.recommended_actions = [
            "Analisar previous logs para identificar exceção ou erro fatal",
            "Verificar variáveis de ambiente e secrets referenciados",
            "Verificar se dependências externas (DB, APIs) estão acessíveis",
            "Considerar rollout restart do deployment se reinicializações > 5",
        ]
        report.safe_to_automate = False
        report.requires_human_review = True
        return report

    def _investigate_oomkilled(self, pod_name, namespace, container_name):
        report = DiagnosisReport(state="OOMKilled")
        report.cause_category = CAUSE_SCHEDULING_RESOURCE
        evidence = []

        # Coleta 1: previous logs (para ver estado antes do kill)
        prev_logs = self.remediator.get_pod_previous_logs(pod_name, namespace)
        if prev_logs and "error" not in prev_logs.lower()[:20]:
            evidence.append(f"previous_logs: {prev_logs[:200]}")
        else:
            evidence.append("previous_logs: não disponíveis")

        # Coleta 2: describe para extrair limits/requests
        describe = self.remediator.describe_pod(pod_name, namespace)
        if describe:
            evidence.append(f"describe: coletado ({len(describe)} chars)")
            for line in describe.splitlines():
                if any(k in line.lower() for k in ["limits", "requests", "memory"]):
                    evidence.append(f"resource_info: {line.strip()}")
            report.confidence = "high"

        report.evidence = evidence
        report.hypothesis = (
            "Container foi encerrado pelo kernel por exceder o limite de memória (OOMKilled). "
            "Memory limit provavelmente está abaixo do consumo real da aplicação."
        )
        report.recommended_actions = [
            "Verificar memory limits no describe do pod",
            "Aumentar memory limit no deployment spec",
            "Analisar previous logs para padrão de consumo antes do kill",
            "Considerar adicionar métricas de memória se não houver",
        ]
        report.safe_to_automate = False
        report.requires_human_review = True
        return report

    def _investigate_imagepull(self, pod_name, namespace, state):
        report = DiagnosisReport(state=state)
        report.cause_category = CAUSE_IMAGE_RUNTIME_PROBLEM
        evidence = []

        # Coleta: describe pod para extrair image name e events
        describe = self.remediator.describe_pod(pod_name, namespace)
        if describe:
            evidence.append(f"describe: coletado ({len(describe)} chars)")
            for line in describe.splitlines():
                if any(k in line.lower() for k in ["image:", "image id", "failed to pull", "back-off", "errimagepull", "not found", "unauthorized"]):
                    evidence.append(f"image_info: {line.strip()}")
            report.confidence = "high"
        else:
            evidence.append("describe: não disponível")
            report.confidence = "low"

        report.evidence = evidence
        report.hypothesis = (
            "Kubernetes não conseguiu baixar a imagem do container. "
            "Causas comuns: tag inexistente, registry inacessível, credenciais ausentes ou inválidas."
        )
        report.recommended_actions = [
            "Verificar se a tag da imagem existe no registry",
            "Confirmar se o registry é acessível do cluster",
            "Verificar se existe imagePullSecret configurado para registries privados",
            "Checar eventos do pod para mensagem de erro exata",
        ]
        report.safe_to_automate = False
        report.requires_human_review = True
        return report

    def _investigate_pending(self, pod_name, namespace):
        report = DiagnosisReport(state="Pending")
        report.cause_category = CAUSE_SCHEDULING_RESOURCE
        evidence = []

        # Coleta: describe pod para extrair events e constraints
        describe = self.remediator.describe_pod(pod_name, namespace)
        if describe:
            evidence.append(f"describe: coletado ({len(describe)} chars)")
            for line in describe.splitlines():
                if any(k in line.lower() for k in [
                    "insufficient", "unschedulable", "taint", "toleration",
                    "node selector", "affinity", "persistentvolumeclaim",
                    "pending", "did not match", "warning", "0/"
                ]):
                    evidence.append(f"scheduling_info: {line.strip()}")
            report.confidence = "medium"

            # se encontrou evidência de PVC
            if any("persistentvolumeclaim" in e.lower() for e in evidence):
                report.cause_category = CAUSE_CONFIGURATION_ERROR
                report.hypothesis = (
                    "Pod está Pending aguardando PersistentVolumeClaim. "
                    "PVC pode estar unbound ou StorageClass indisponível."
                )
                report.recommended_actions = [
                    "Verificar status do PVC: kubectl get pvc -n <namespace>",
                    "Verificar se StorageClass existe e está disponível",
                    "Checar eventos do PVC para erro de provisionamento",
                ]
            # se encontrou taint/affinity
            elif any(k in e.lower() for e in evidence for k in ["taint", "toleration", "affinity", "node selector"]):
                report.hypothesis = (
                    "Pod não consegue ser agendado por restrições de node: "
                    "taints sem tolerations correspondentes, nodeSelector ou affinity incompatível."
                )
                report.recommended_actions = [
                    "Verificar taints nos nodes: kubectl describe nodes",
                    "Confirmar se o pod tem tolerations corretas",
                    "Revisar nodeSelector e affinity rules no deployment spec",
                ]
            # se encontrou insufficient resources
            elif any("insufficient" in e.lower() for e in evidence):
                report.hypothesis = (
                    "Pod não consegue ser agendado por falta de recursos. "
                    "Nenhum node tem CPU ou memória suficiente para os requests definidos."
                )
                report.recommended_actions = [
                    "Verificar recursos disponíveis: kubectl describe nodes",
                    "Reduzir resource requests no deployment spec",
                    "Considerar adicionar nodes ao cluster",
                ]
                report.confidence = "high"
            else:
                report.hypothesis = (
                    "Pod está Pending. Causa exata requer análise dos eventos do describe."
                )
                report.recommended_actions = [
                    "Analisar eventos: kubectl describe pod <pod> -n <namespace>",
                    "Verificar disponibilidade de nodes: kubectl get nodes",
                ]
        else:
            evidence.append("describe: não disponível")
            report.confidence = "low"
            report.hypothesis = "Pod está Pending. Não foi possível coletar describe para diagnóstico."
            report.recommended_actions = [
                "Executar: kubectl describe pod <pod> -n <namespace>",
            ]

        report.evidence = evidence
        report.safe_to_automate = False
        report.requires_human_review = True
        return report

    def _investigate_container_config(self, pod_name, namespace):
        report = DiagnosisReport(state="CreateContainerConfigError")
        report.cause_category = CAUSE_CONFIGURATION_ERROR
        evidence = []

        # Coleta: describe pod para extrair env, secrets, configmaps, mounts
        describe = self.remediator.describe_pod(pod_name, namespace)
        if describe:
            evidence.append(f"describe: coletado ({len(describe)} chars)")
            for line in describe.splitlines():
                if any(k in line.lower() for k in [
                    "error", "secret", "configmap", "env", "mount",
                    "volume", "not found", "forbidden", "invalid",
                    "warning", "failed"
                ]):
                    evidence.append(f"config_info: {line.strip()}")
            report.confidence = "high"

            if any("secret" in e.lower() for e in evidence):
                report.hypothesis = (
                    "Erro ao criar container por Secret ausente ou inválido. "
                    "O pod referencia um Secret que não existe no namespace."
                )
                report.recommended_actions = [
                    "Verificar secrets no namespace: kubectl get secrets -n <namespace>",
                    "Confirmar nome exato do secret referenciado no deployment spec",
                    "Criar o secret ausente ou corrigir a referência",
                ]
            elif any("configmap" in e.lower() for e in evidence):
                report.hypothesis = (
                    "Erro ao criar container por ConfigMap ausente ou inválido. "
                    "O pod referencia um ConfigMap que não existe no namespace."
                )
                report.recommended_actions = [
                    "Verificar configmaps no namespace: kubectl get configmaps -n <namespace>",
                    "Confirmar nome exato do configmap referenciado no deployment spec",
                    "Criar o configmap ausente ou corrigir a referência",
                ]
            elif any("mount" in e.lower() or "volume" in e.lower() for e in evidence):
                report.hypothesis = (
                    "Erro ao criar container por volume ou mount inválido. "
                    "PVC ou volume referenciado pode não existir."
                )
                report.recommended_actions = [
                    "Verificar volumes no pod spec",
                    "Confirmar que PVCs referenciados existem e estão bound",
                    "Checar permissões de mount no node",
                ]
            else:
                report.hypothesis = (
                    "Erro ao criar container por configuração inválida. "
                    "Analisar eventos do describe para causa exata."
                )
                report.recommended_actions = [
                    "Analisar eventos: kubectl describe pod <pod> -n <namespace>",
                    "Verificar env vars, secrets e configmaps referenciados",
                ]
        else:
            evidence.append("describe: não disponível")
            report.confidence = "low"
            report.hypothesis = "CreateContainerConfigError detectado. Describe não disponível para diagnóstico."
            report.recommended_actions = [
                "Executar: kubectl describe pod <pod> -n <namespace>",
            ]

        report.evidence = evidence
        report.safe_to_automate = False
        report.requires_human_review = True
        return report

    def _investigate_running_unhealthy(self, pod_name, namespace, container_name):
        report = DiagnosisReport(state="Running")
        report.cause_category = CAUSE_APPLICATION_ERROR
        evidence = []

        # Coleta 1: logs recentes
        logs = self.remediator.get_pod_logs(pod_name, namespace)
        if logs and "error" not in logs.lower()[:20]:
            evidence.append(f"logs: {logs[:300]}")
            report.confidence = "medium"
        else:
            evidence.append("logs: não disponíveis ou vazios")

        # Coleta 2: describe para extrair probe config e events
        describe = self.remediator.describe_pod(pod_name, namespace)
        if describe:
            evidence.append(f"describe: coletado ({len(describe)} chars)")
            for line in describe.splitlines():
                if any(k in line.lower() for k in [
                    "liveness", "readiness", "startup", "probe",
                    "unhealthy", "warning", "failed", "error", "restart"
                ]):
                    evidence.append(f"probe_info: {line.strip()}")
            report.confidence = "high"

        report.evidence = evidence

        if any("liveness" in e.lower() for e in evidence):
            report.hypothesis = (
                "Container está Running mas liveness probe está falhando. "
                "A aplicação pode estar em deadlock, travada ou demorando mais que o timeout configurado."
            )
            report.recommended_actions = [
                "Analisar logs recentes para erros ou travamento da aplicação",
                "Verificar configuração de liveness probe (timeout, threshold, path)",
                "Confirmar se endpoint de health check está respondendo corretamente",
                "Considerar aumentar initialDelaySeconds se aplicação demora para iniciar",
            ]
        elif any("readiness" in e.lower() for e in evidence):
            report.hypothesis = (
                "Container está Running mas readiness probe está falhando. "
                "A aplicação pode estar inicializando, sem conexão com dependências ou sobrecarregada."
            )
            report.recommended_actions = [
                "Verificar se dependências (DB, cache, APIs) estão acessíveis",
                "Analisar logs para erros de conexão ou inicialização",
                "Verificar configuração de readiness probe",
                "Pod não receberá tráfego enquanto readiness falhar",
            ]
        else:
            report.hypothesis = (
                "Container está Running mas avaliado como unhealthy. "
                "Verificar logs e eventos para causa específica."
            )
            report.recommended_actions = [
                "Analisar logs recentes: kubectl logs <pod> -n <namespace>",
                "Verificar eventos: kubectl describe pod <pod> -n <namespace>",
                "Confirmar endpoints de health check da aplicação",
            ]

        report.safe_to_automate = False
        report.requires_human_review = False
        return report
