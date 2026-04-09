import json
import re
import sys
import uuid

from analyzers.incident_analyzer import classify_input, suggest_remediation
from incident_logger import write_incident_summary
from remediators.kubectl_remediator import (
    delete_pod,
    describe_pod,
    describe_service,
    get_pod_logs,
    get_pod_node,
    get_pod_owner,
    get_pod_previous_logs,
    get_pod_status,
    list_all_pods,
    list_deployments,
    list_namespaces,
    list_nodes,
    list_pods,
    list_pods_wide,
    list_services,
    rollout_restart_deployment,
)
from remediators.dry_run_remediator import DryRunRemediator
from state_evaluator import evaluate_pod_state, PodStateEvaluation
from remediation_guard import can_auto_remediate, register_remediation_attempt
from log_analyzer import infer_probable_cause
from cause_based_remediator import plan_next_steps
from analyzers.diagnosis_engine import DiagnosisEngine
from analyzers.workload_classifier import WorkloadClassifier, NO_RESTART
from reporters.incident_reporter import IncidentReporter, IncidentReport

AUTO_REMEDIATE = True
AUTO_FOLLOW_UP = True


class _KubectlFunctionsAdapter:
    """Wraps module-level kubectl functions as methods for DryRunRemediator composition."""

    def delete_pod(self, namespace: str, pod_name: str):
        return delete_pod(namespace, pod_name)

    def rollout_restart_deployment(self, namespace: str, deployment_name: str):
        return rollout_restart_deployment(namespace, deployment_name)

    def rollout_restart_statefulset(self, namespace: str, statefulset_name: str):
        from remediators.kubectl_remediator import rollout_restart_statefulset
        return rollout_restart_statefulset(namespace, statefulset_name)

    def rollout_restart_daemonset(self, namespace: str, daemonset_name: str):
        from remediators.kubectl_remediator import rollout_restart_daemonset
        return rollout_restart_daemonset(namespace, daemonset_name)


class _RemediatorAdapter:
    """Adapts module-level kubectl functions for DiagnosisEngine.
    Swaps arg order (pod_name, namespace) → (namespace, pod_name) and unwraps Tuple[bool, str].
    """

    def get_pod_previous_logs(self, pod_name, namespace):
        success, output = get_pod_previous_logs(namespace, pod_name)
        return output if success else None

    def describe_pod(self, pod_name, namespace):
        success, output = describe_pod(namespace, pod_name)
        return output if success else None

    def get_pod_logs(self, pod_name, namespace):
        success, output = get_pod_logs(namespace, pod_name)
        return output if success else None


_diagnosis_engine = DiagnosisEngine(_RemediatorAdapter())

_REQUIRED_NAMESPACE_ACTIONS = {
    "list_pods", "list_pods_wide", "list_services", "list_deployments",
    "get_pod_logs", "get_pod_previous_logs", "describe_pod",
    "get_pod_status", "delete_pod", "get_pod_node", "rollout_restart_deployment",
}

_REQUIRED_POD_ACTIONS = {
    "get_pod_logs", "get_pod_previous_logs", "describe_pod",
    "get_pod_status", "delete_pod", "get_pod_node",
}


class SessionContext:
    """Mantém o contexto da sessão REPL entre comandos."""

    def __init__(self):
        self.active_namespace: str | None = None
        self.active_pod: str | None = None

    def update(self, params: dict) -> None:
        """Atualiza o contexto com os params da última ação executada."""
        if params.get("namespace"):
            self.active_namespace = params["namespace"]
        if params.get("pod_name"):
            self.active_pod = params["pod_name"]

    def fill(self, params: dict) -> dict:
        """
        Preenche params faltantes com valores do contexto ativo.
        Retorna um novo dict sem modificar o original.
        """
        filled = dict(params)
        if not filled.get("namespace") and self.active_namespace:
            filled["namespace"] = self.active_namespace
        if not filled.get("pod_name") and self.active_pod:
            filled["pod_name"] = self.active_pod
        return filled

    def clear(self) -> None:
        """Limpa o contexto da sessão."""
        self.active_namespace = None
        self.active_pod = None

    def prompt(self) -> str:
        """Retorna o texto do prompt com namespace ativo se disponível."""
        if self.active_namespace:
            return f"sre-agent [{self.active_namespace}]> "
        return "sre-agent> "


def execute_action(action: str, params: dict):
    if action == "delete_pod":
        return delete_pod(params["namespace"], params["pod_name"])

    if action == "list_pods":
        return list_pods(params["namespace"])

    if action == "list_pods_wide":
        return list_pods_wide(params["namespace"])

    if action == "list_namespaces":
        return list_namespaces()

    if action == "list_nodes":
        return list_nodes()

    if action == "list_all_pods":
        return list_all_pods()

    if action == "list_services":
        return list_services(params["namespace"])

    if action == "list_deployments":
        return list_deployments(params["namespace"])

    if action == "describe_pod":
        return describe_pod(params["namespace"], params["pod_name"])

    if action == "describe_service":
        return describe_service(params["namespace"], params["service_name"])

    if action == "get_pod_logs":
        return get_pod_logs(
            params["namespace"],
            params["pod_name"],
            params.get("container_name"),
        )

    if action == "get_pod_previous_logs":
        return get_pod_previous_logs(
            params["namespace"],
            params["pod_name"],
            params.get("container_name"),
        )

    if action == "get_pod_node":
        return get_pod_node(params["namespace"], params["pod_name"])

    if action == "get_pod_status":
        return get_pod_status(params["namespace"], params["pod_name"])

    if action == "rollout_restart_deployment":
        return rollout_restart_deployment(params["namespace"], params["deployment_name"])

    return False, f"Unsupported action: {action}"


def parse_status_output(output):
    if isinstance(output, dict):
        return output

    if isinstance(output, str):
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return None

    return None


def maybe_execute_follow_up(state_result: PodStateEvaluation):
    follow_up_action = state_result.get("suggested_follow_up_action")
    follow_up_params = state_result.get("suggested_follow_up_params", {})

    result = {
        "executed": False,
        "action": follow_up_action,
        "params": follow_up_params,
        "success": None,
        "output": None,
    }

    if not follow_up_action:
        return result

    _section("FOLLOW-UP")
    print(f"Follow-up action: {follow_up_action}")
    print(f"Follow-up params: {follow_up_params}")

    if not AUTO_FOLLOW_UP:
        print("[INFO] AUTO_FOLLOW_UP is disabled. Skipping follow-up execution.")
        return result

    success, output = execute_action(follow_up_action, follow_up_params)

    _section("FOLLOW-UP OUTPUT")
    print(output)

    result["executed"] = True
    result["success"] = success
    result["output"] = output
    return result


def _section(title: str):
    """Imprime separador de seção padronizado."""
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def print_incident_summary(summary: dict):
    print(f"\n{'═' * 60}")
    print(f"  INCIDENT SUMMARY")
    print(f"{'═' * 60}")
    print(f"Incident: {summary['incident']}")
    print(f"Initial action: {summary['initial_action']}")
    print(f"Initial action success: {summary['initial_action_success']}")
    print(f"Detected state: {summary['detected_state']}")
    print(f"Health status: {summary['health_status']}")
    print(f"Container name: {summary['container_name']}")
    print(f"Restart count: {summary['restart_count']}")
    print(f"Follow-up action: {summary['follow_up_action']}")
    print(f"Follow-up executed: {summary['follow_up_executed']}")
    print(f"Remediation action: {summary['remediation_action']}")
    print(f"Remediation executed: {summary['remediation_executed']}")
    print(f"Remediation success: {summary['remediation_success']}")
    print(f"Probable cause: {summary['probable_cause']}")
    print(f"Confidence: {summary['confidence']}")
    print(f"Matched pattern: {summary['matched_pattern']}")
    print(f"Cause-based plan applied: {summary['cause_based_plan_applied']}")
    print(f"Recommended checks executed: {summary['recommended_checks_executed']}")
    print(f"Requires human review: {summary['requires_human_review']}")
    print(f"Safe remediation selected: {summary['safe_remediation_selected']}")
    print(f"Cause explanation: {summary['cause_explanation']}")
    print(f"Final outcome: {summary['final_outcome']}")
    print(f"{'═' * 60}")


def process_user_input(query: str, ctx: SessionContext | None = None, dry_run: bool = False, reporter: IncidentReporter = None):
    """Recebe a descrição do incidente e executa o pipeline completo."""
    _real_remediator = _KubectlFunctionsAdapter()
    active_remediator = DryRunRemediator(_real_remediator) if dry_run else _real_remediator
    print("=" * 60)
    print("SRE AGENT :: HTTP + SSH + K8s + Incident Analysis")
    print("=" * 60)
    if ctx and ctx.active_namespace:
        print(f"[SESSION] namespace={ctx.active_namespace}", end="")
        if ctx.active_pod:
            print(f"  pod={ctx.active_pod}", end="")
        print()
    print(f"[CONFIG] AUTO_REMEDIATE={AUTO_REMEDIATE}")
    print(f"[CONFIG] AUTO_FOLLOW_UP={AUTO_FOLLOW_UP}")
    print()

    incident = query
    analysis = suggest_remediation(incident)

    input_type = classify_input(analysis["action"])

    if input_type == "request":
        if not analysis["action"]:
            print("\n[!] Unknown command. Try: list namespaces, list pods in namespace default, etc.")
            return
        if ctx:
            analysis["params"] = ctx.fill(analysis["params"])
        params_check = analysis["params"]
        if analysis["action"] in _REQUIRED_NAMESPACE_ACTIONS:
            if not params_check.get("namespace"):
                print("[ERROR] Namespace não especificado e não encontrado no contexto.")
                print("        Use: set namespace <nome>  ou inclua 'in namespace <nome>' no comando.")
                return
            if analysis["action"] in _REQUIRED_POD_ACTIONS:
                if not params_check.get("pod_name"):
                    print("[ERROR] Pod não especificado e não encontrado no contexto.")
                    print("        Use: set namespace <nome> e inclua o nome do pod no comando.")
                    return
        if analysis["action"] == "rollout_restart_deployment":
            success, output = active_remediator.rollout_restart_deployment(
                namespace=analysis["params"]["namespace"],
                deployment_name=analysis["params"]["deployment_name"],
            )
        else:
            success, output = execute_action(analysis["action"], analysis["params"])
        print()
        if success:
            print(output)
            if ctx:
                ctx.update(analysis["params"])
        else:
            print(f"[ERROR] {output}")
        return

    summary = {
        "incident": incident,
        "initial_action": analysis["action"],
        "initial_action_success": None,
        "detected_state": None,
        "health_status": None,
        "container_name": None,
        "restart_count": None,
        "follow_up_action": None,
        "follow_up_executed": False,
        "remediation_action": None,
        "remediation_executed": False,
        "remediation_success": None,
        "probable_cause": None,
        "confidence": None,
        "matched_pattern": None,
        "cause_based_plan_applied": False,
        "recommended_checks_executed": None,
        "requires_human_review": None,
        "safe_remediation_selected": None,
        "cause_explanation": None,
        "final_outcome": "No action performed.",
    }

    _section("ANALYSIS")
    print(f"Reason: {analysis['reason']}")
    print(f"Suggested action: {analysis['action']}")
    print(f"Parameters: {analysis['params']}")

    action = analysis["action"]
    params = analysis["params"]
    if ctx:
        params = ctx.fill(params)

    if action in _REQUIRED_NAMESPACE_ACTIONS:
        if not params.get("namespace"):
            print("[ERROR] Namespace não especificado e não encontrado no contexto.")
            print("        Use: set namespace <nome>  ou inclua 'in namespace <nome>' no comando.")
            return
        if action in _REQUIRED_POD_ACTIONS:
            if not params.get("pod_name"):
                print("[ERROR] Pod não especificado e não encontrado no contexto.")
                print("        Use: set namespace <nome> e inclua o nome do pod no comando.")
                return

    if not action:
        print("\n[-] No remediation suggested for this incident.")
        print_incident_summary(summary)
        write_incident_summary(summary)
        return

    success, output = execute_action(action, params)
    summary["initial_action_success"] = success
    if ctx and success:
        ctx.update(params)

    _section("ACTION OUTPUT")
    print(output)

    workload_info = None
    diagnosis_report = None

    if action == "get_pod_status" and success:
        status_data = parse_status_output(output)

        if not status_data:
            print("\n[-] Failed to parse pod status output for state evaluation.")
            summary["final_outcome"] = "Failed to parse pod status output."
            print_incident_summary(summary)
            write_incident_summary(summary)
            return

        parsed_status = status_data.get("parsed_status")
        container_name = status_data.get("container_name")
        restart_count = status_data.get("restart_count")

        state_result = evaluate_pod_state(
            parsed_status,
            namespace=params.get("namespace"),
            pod_name=params.get("pod_name"),
            container_name=container_name,
        )

        summary["detected_state"] = parsed_status
        summary["health_status"] = state_result["health_status"]
        summary["container_name"] = container_name
        summary["restart_count"] = restart_count
        summary["follow_up_action"] = state_result["suggested_follow_up_action"]
        summary["remediation_action"] = state_result["recommended_action"]

        _section("STATE EVALUATION")
        print(f"Health status: {state_result['health_status']}")
        print(f"Requires remediation: {state_result['requires_remediation']}")
        print(f"Recommended action: {state_result['recommended_action']}")
        print(f"Suggested follow-up action: {state_result['suggested_follow_up_action']}")
        print(f"Suggested follow-up params: {state_result['suggested_follow_up_params']}")

        # classificar workload antes de remediar
        if params.get("pod_name") and params.get("namespace"):
            workload_classifier = WorkloadClassifier(active_remediator)
            workload_info = workload_classifier.classify(
                pod_name=params["pod_name"],
                namespace=params["namespace"],
            )
            print(f"\n{'─' * 60}")
            print("  WORKLOAD")
            print(f"{'─' * 60}")
            print(f"Pod:            {workload_info.pod_name}")
            print(f"Workload type:  {workload_info.workload_type}")
            if workload_info.workload_name:
                print(f"Workload name:  {workload_info.workload_name}")
            if workload_info.action_target:
                print(f"Action target:  {workload_info.action_target}")
            if workload_info.restart_warning:
                print(f"[WARNING] {workload_info.restart_warning}")
            if workload_info.error:
                print(f"[ERROR] Workload classification failed: {workload_info.error}")

        if state_result["health_status"] != "healthy" and parsed_status:
            diagnosis_report = _diagnosis_engine.investigate(
                state=parsed_status,
                pod_name=params.get("pod_name"),
                namespace=params.get("namespace"),
                container_name=container_name,
            )
            _section("DIAGNOSIS")
            print(f"State:                 {diagnosis_report.state}")
            print(f"Cause category:        {diagnosis_report.cause_category}")
            print(f"Confidence:            {diagnosis_report.confidence}")
            print(f"Hypothesis:            {diagnosis_report.hypothesis}")
            if diagnosis_report.evidence:
                print(f"Evidence ({len(diagnosis_report.evidence)} items collected):")
                for e in diagnosis_report.evidence:
                    print(f"  · {e[:100]}")
            if diagnosis_report.recommended_actions:
                print("Recommended actions:")
                for i, act in enumerate(diagnosis_report.recommended_actions, 1):
                    print(f"  {i}. {act}")
            print(f"Safe to automate:      {diagnosis_report.safe_to_automate}")
            print(f"Requires human review: {diagnosis_report.requires_human_review}")

        follow_up_result = maybe_execute_follow_up(state_result)
        summary["follow_up_executed"] = follow_up_result["executed"]

        cause_result = None
        plan = None

        if follow_up_result["executed"] and follow_up_result["output"]:
            cause_result = infer_probable_cause(follow_up_result["output"])
            summary["probable_cause"] = cause_result["probable_cause"]
            summary["confidence"] = cause_result["confidence"]
            summary["matched_pattern"] = cause_result["matched_pattern"]
            _section("LOG ANALYSIS")
            print(f"Probable cause: {cause_result['probable_cause']}")
            print(f"Confidence: {cause_result['confidence']}")
            print(f"Matched pattern: {cause_result['matched_pattern']}")

            plan = plan_next_steps(cause_result["matched_pattern"])
            summary["cause_based_plan_applied"] = True
            summary["recommended_checks_executed"] = plan["recommended_checks"]
            summary["requires_human_review"] = plan["requires_human_review"]
            summary["safe_remediation_selected"] = plan["safe_remediation"]
            summary["cause_explanation"] = plan["explanation"]
            _section("REMEDIATION PLAN")
            print(f"Recommended checks: {plan['recommended_checks']}")
            print(f"Requires human review: {plan['requires_human_review']}")
            print(f"Explanation: {plan['explanation']}")
            if (
                not plan["requires_human_review"]
                and cause_result["confidence"] != "low"
                and plan["safe_remediation"]
            ):
                print(f"Safe remediation: {plan['safe_remediation']}")
            else:
                print("[INFO] Safe remediation skipped: requires human review or low confidence.")

        cause_allows_remediation = (
            plan is None
            or (
                not plan["requires_human_review"]
                and cause_result["confidence"] != "low"
            )
        )

        if (
            AUTO_REMEDIATE
            and state_result["requires_remediation"]
            and state_result["recommended_action"] == "delete_pod"
            and cause_allows_remediation
        ):
            namespace = params["namespace"]
            pod_name = params["pod_name"]

            # gate: bloquear restart para Job e CronJob
            if workload_info and workload_info.workload_type in NO_RESTART:
                _section("AUTO-REMEDIATION")
                print(f"[WORKLOAD GATE] Remediação bloqueada para {workload_info.workload_type}.")
                if workload_info.workload_type == "Job":
                    print("  Jobs não se resolvem com restart. Ações recomendadas:")
                    print("  1. Analisar logs do pod falho")
                    print("  2. Corrigir a causa raiz")
                    print("  3. Criar novo Job se necessário")
                elif workload_info.workload_type == "CronJob":
                    print("  CronJobs são gerenciados automaticamente. Ações recomendadas:")
                    print("  1. Analisar logs do pod falho")
                    print("  2. Verificar schedule e configuração do CronJob")
                    print("  3. Aguardar próximo ciclo ou triggerar manualmente")
                summary["remediation_executed"] = False
                summary["final_outcome"] = f"Auto-remediation blocked: workload type {workload_info.workload_type} does not support restart."
                # pular remediação
            else:
                allowed, reason = can_auto_remediate(namespace, pod_name, "delete_pod")
                _section("AUTO-REMEDIATION")
                print(f"Remediation guard: {reason}")

                if allowed:
                    register_remediation_attempt(namespace, pod_name, "delete_pod")

                    if workload_info and workload_info.recommended_action == "rollout_restart_statefulset":
                        print(f"[OWNER] Pod pertence ao StatefulSet '{workload_info.workload_name}'. Executando rollout restart.")
                        rem_success, rem_output = active_remediator.rollout_restart_statefulset(
                            namespace=namespace,
                            statefulset_name=workload_info.workload_name,
                        )
                        print(f"[REMEDIATION] rollout restart statefulset: {'OK' if rem_success else 'FAILED'} — {rem_output}")
                    elif workload_info and workload_info.recommended_action == "rollout_restart_daemonset":
                        print(f"[OWNER] Pod pertence ao DaemonSet '{workload_info.workload_name}'. Executando rollout restart.")
                        rem_success, rem_output = active_remediator.rollout_restart_daemonset(
                            namespace=namespace,
                            daemonset_name=workload_info.workload_name,
                        )
                        print(f"[REMEDIATION] rollout restart daemonset: {'OK' if rem_success else 'FAILED'} — {rem_output}")
                    elif workload_info and workload_info.recommended_action == "rollout_restart_deployment":
                        print(f"[OWNER] Pod pertence ao deployment '{workload_info.workload_name}'. Preferindo rollout restart.")
                        rem_success, rem_output = active_remediator.rollout_restart_deployment(
                            namespace=namespace,
                            deployment_name=workload_info.workload_name,
                        )
                        print(f"[REMEDIATION] rollout restart: {'OK' if rem_success else 'FAILED'} — {rem_output}")
                    else:
                        rem_success, rem_output = active_remediator.delete_pod(
                            namespace=namespace,
                            pod_name=pod_name,
                        )
                        print(f"[REMEDIATION] delete pod: {'OK' if rem_success else 'FAILED'} — {rem_output}")

                    _section("AUTO-REMEDIATION OUTPUT")
                    print(rem_output)

                    summary["remediation_executed"] = True
                    summary["remediation_success"] = rem_success

                    if rem_success:
                        summary["final_outcome"] = "Follow-up collected and auto-remediation applied successfully."
                    else:
                        summary["final_outcome"] = "Follow-up collected, but auto-remediation failed."
                else:
                    summary["remediation_action"] = "delete_pod"
                    summary["remediation_executed"] = False
                    summary["remediation_success"] = False
                    summary["final_outcome"] = "Auto-remediation was blocked by guard."
                    print("\n[-] Auto-remediation blocked by guard.")
        else:
            if follow_up_result["executed"]:
                summary["final_outcome"] = "Diagnostic follow-up executed. No remediation applied."
            else:
                summary["final_outcome"] = "State evaluated. No remediation applied."
    else:
        if success:
            summary["final_outcome"] = "Action executed successfully."
        else:
            summary["final_outcome"] = "Action execution failed."

    print_incident_summary(summary)
    write_incident_summary(summary)

    if reporter:
        report = reporter.build(
            user_input=query,
            namespace=params.get("namespace", ""),
            pod_name=params.get("pod_name", ""),
            input_type="incident",
            action=analysis.get("action", ""),
            action_success=summary.get("initial_action_success", False),
            detected_state=summary.get("detected_state"),
            health_status=summary.get("health_status"),
            container_name=summary.get("container_name"),
            restart_count=summary.get("restart_count"),
            workload_type=workload_info.workload_type if workload_info else None,
            workload_name=workload_info.workload_name if workload_info else None,
            action_target=workload_info.action_target if workload_info else None,
            cause_category=diagnosis_report.cause_category if diagnosis_report else None,
            hypothesis=diagnosis_report.hypothesis if diagnosis_report else None,
            diagnosis_confidence=diagnosis_report.confidence if diagnosis_report else None,
            follow_up_action=summary.get("follow_up_action"),
            follow_up_executed=summary.get("follow_up_executed", False),
            remediation_action=summary.get("remediation_action"),
            remediation_executed=summary.get("remediation_executed", False),
            remediation_success=summary.get("remediation_success"),
            probable_cause=summary.get("probable_cause"),
            matched_pattern=summary.get("matched_pattern"),
            confidence=summary.get("confidence"),
            requires_human_review=summary.get("requires_human_review"),
            final_outcome=summary.get("final_outcome", ""),
            dry_run=dry_run,
        )
        if summary.get("health_status") != "healthy":
            reporter.save(report)


def print_help():
    """Exibe os comandos disponíveis do agente."""
    print(f"\n{'─' * 60}")
    print("  COMANDOS DISPONÍVEIS")
    print(f"{'─' * 60}")
    print("""
  GERAL
    help / ?              → exibe esta ajuda
    exit / quit           → encerra o agente

  CLUSTER
    list namespaces       → lista todos os namespaces
    list nodes            → lista todos os nodes
    list all pods         → lista pods em todos os namespaces

  NAMESPACE
    list pods in <namespace>
    list pods running in <namespace>
    list pods wide in <namespace>
    list services in <namespace>
    list deployments in <namespace>

  TROUBLESHOOTING
    check pod <pod> in <namespace>
    describe pod <pod> in <namespace>
    show logs for pod <pod> in <namespace>
    which node is pod <pod> in <namespace>

  SESSÃO (contexto ativo entre comandos)
    set namespace <name>  → define namespace ativo
    show context          → exibe contexto atual
    clear context         → limpa contexto da sessão
    history               → exibe histórico de comandos

  INCIDENTS
    incidents             → lista incidents da sessão atual
    incidents last <N>    → lista os últimos N incidents da sessão
    incidents all         → lista todos os incidents (todas as sessões)
""")
    print(f"{'─' * 60}")


def run_interactive_mode(dry_run: bool = False):
    """Inicia o loop REPL interativo do agente."""
    ctx = SessionContext()
    history = []
    session_id = str(uuid.uuid4())[:8]
    reporter = IncidentReporter(session_id=session_id)
    print(f"[SESSION ID] {session_id}")
    if dry_run:
        print("[DRY-RUN] Modo simulação ativo — nenhuma ação destrutiva será executada.")
    print("SRE Agent started.")
    print("Type your request or 'exit' to quit.\n")

    while True:
        try:
            query = input(ctx.prompt()).strip()
        except KeyboardInterrupt:
            print("\nInterrupted. Goodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break

        if not query:
            continue

        if query.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        if query.lower() == "history":
            if not history:
                print("[HISTORY] Nenhum comando registrado.")
            else:
                print(f"\n{'─' * 60}")
                print("  HISTORY")
                print(f"{'─' * 60}")
                for i, cmd in enumerate(history, 1):
                    print(f"  {i:>3}. {cmd}")
                print(f"{'─' * 60}")
            continue

        history.append(query)

        if query.lower() in ("help", "?"):
            print_help()
            continue

        if query.lower().startswith("set namespace "):
            ns = query.split("set namespace ", 1)[1].strip()
            if ns:
                ctx.update({"namespace": ns})
                print(f"[SESSION] namespace ativo: {ns}")
            else:
                print("[ERROR] Informe o namespace. Ex: set namespace sre-demo")
            continue

        if query.lower() == "show context":
            if ctx.active_namespace or ctx.active_pod:
                if ctx.active_namespace:
                    print(f"[SESSION] namespace: {ctx.active_namespace}")
                if ctx.active_pod:
                    print(f"[SESSION] pod: {ctx.active_pod}")
            else:
                print("[SESSION] contexto limpo")
            continue

        if query.lower() == "clear context":
            ctx.clear()
            print("[SESSION] contexto limpo")
            continue

        if query.lower().strip() == "incidents all":
            all_reports = reporter.load_all()
            if not all_reports:
                print("[INCIDENTS] Nenhum incident registrado.")
            else:
                print(f"\n{'─' * 60}")
                print(f"  INCIDENTS — todos ({len(all_reports)} registros)")
                print(f"{'─' * 60}")
                for r in all_reports:
                    state = r.detected_state or "—"
                    health = r.health_status or "—"
                    outcome = r.final_outcome[:50] if r.final_outcome else "—"
                    dr = " [DRY-RUN]" if r.dry_run else ""
                    session = f"[{r.session_id}]" if r.session_id else ""
                    print(f"  {r.incident_id} {session}{dr}")
                    print(f"    input:   {r.user_input[:60]}")
                    print(f"    state:   {state} | health: {health}")
                    print(f"    outcome: {outcome}")
                    print()
                print(f"{'─' * 60}")
            continue

        _incidents_match = re.match(r"^incidents(?:\s+last\s+(\d+))?$", query.lower().strip())
        if _incidents_match:
            n = int(_incidents_match.group(1)) if _incidents_match.group(1) else None
            session_reports = reporter.load_session()
            if n:
                session_reports = session_reports[-n:]
            if not session_reports:
                print("[INCIDENTS] Nenhum incident registrado nesta sessão.")
            else:
                print(f"\n{'─' * 60}")
                print(f"  INCIDENTS — sessão {reporter.session_id} ({len(session_reports)} registros)")
                print(f"{'─' * 60}")
                for r in session_reports:
                    state = r.detected_state or "—"
                    health = r.health_status or "—"
                    outcome = r.final_outcome[:50] if r.final_outcome else "—"
                    dr = " [DRY-RUN]" if r.dry_run else ""
                    print(f"  {r.incident_id}{dr}")
                    print(f"    input:   {r.user_input[:60]}")
                    print(f"    state:   {state} | health: {health}")
                    print(f"    outcome: {outcome}")
                    print()
                print(f"{'─' * 60}")
            continue

        process_user_input(query, ctx, dry_run=dry_run, reporter=reporter)


def run_single_command_mode(query: str, dry_run: bool = False):
    """Executa o agente uma única vez com a query fornecida via argumento."""
    session_id = str(uuid.uuid4())[:8]
    reporter = IncidentReporter(session_id=session_id)
    print(f"[SESSION ID] {session_id}")
    if dry_run:
        print("[DRY-RUN] Modo simulação ativo — nenhuma ação destrutiva será executada.")
    process_user_input(query, dry_run=dry_run, reporter=reporter)


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    query_args = [a for a in args if a != "--dry-run"]
    query = " ".join(query_args).strip() if query_args else None

    if query:
        run_single_command_mode(query, dry_run=dry_run)
    else:
        run_interactive_mode(dry_run=dry_run)


if __name__ == "__main__":
    main()