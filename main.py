import json

from analyzers.incident_analyzer import suggest_remediation
from incident_logger import write_incident_summary
from remediators.kubectl_remediator import (
    delete_pod,
    describe_pod,
    describe_service,
    get_pod_logs,
    get_pod_node,
    get_pod_previous_logs,
    get_pod_status,
    list_deployments,
    list_pods,
    list_pods_wide,
    list_services,
)
from state_evaluator import evaluate_pod_state
from remediation_guard import can_auto_remediate, register_remediation_attempt

AUTO_REMEDIATE = True
AUTO_FOLLOW_UP = True


def execute_action(action: str, params: dict):
    if action == "delete_pod":
        return delete_pod(params["namespace"], params["pod_name"])

    if action == "list_pods":
        return list_pods(params["namespace"])

    if action == "list_pods_wide":
        return list_pods_wide(params["namespace"])

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


def maybe_execute_follow_up(state_result: dict):
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

    print("\n[+] Follow-up recommendation detected")
    print(f"Follow-up action: {follow_up_action}")
    print(f"Follow-up params: {follow_up_params}")

    if not AUTO_FOLLOW_UP:
        print("[INFO] AUTO_FOLLOW_UP is disabled. Skipping follow-up execution.")
        return result

    success, output = execute_action(follow_up_action, follow_up_params)

    print("\n[+] Follow-up execution output")
    print(output)

    result["executed"] = True
    result["success"] = success
    result["output"] = output
    return result


def print_incident_summary(summary: dict):
    print("\n" + "=" * 60)
    print("INCIDENT SUMMARY")
    print("=" * 60)
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
    print(f"Final outcome: {summary['final_outcome']}")
    print("=" * 60)


def main():
    print("=" * 60)
    print("SRE AGENT :: HTTP + SSH + K8s + Incident Analysis")
    print("=" * 60)
    print(f"[CONFIG] AUTO_REMEDIATE={AUTO_REMEDIATE}")
    print(f"[CONFIG] AUTO_FOLLOW_UP={AUTO_FOLLOW_UP}")
    print()

    incident = input("Describe the incident: ").strip()
    analysis = suggest_remediation(incident)

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
        "final_outcome": "No action performed.",
    }

    print("\n[+] Analysis result")
    print(f"Reason: {analysis['reason']}")
    print(f"Suggested action: {analysis['action']}")
    print(f"Parameters: {analysis['params']}")

    action = analysis["action"]
    params = analysis["params"]

    if not action:
        print("\n[-] No remediation suggested for this incident.")
        print_incident_summary(summary)
        write_incident_summary(summary)
        return

    success, output = execute_action(action, params)
    summary["initial_action_success"] = success

    print("\n[+] Action output")
    print(output)

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

        print("\n[+] State evaluation")
        print(f"Health status: {state_result['health_status']}")
        print(f"Requires remediation: {state_result['requires_remediation']}")
        print(f"Recommended action: {state_result['recommended_action']}")
        print(f"Suggested follow-up action: {state_result['suggested_follow_up_action']}")
        print(f"Suggested follow-up params: {state_result['suggested_follow_up_params']}")

        follow_up_result = maybe_execute_follow_up(state_result)
        summary["follow_up_executed"] = follow_up_result["executed"]

        if (
            AUTO_REMEDIATE
            and state_result["requires_remediation"]
            and state_result["recommended_action"] == "delete_pod"
        ):
            namespace = params["namespace"]
            pod_name = params["pod_name"]

            allowed, reason = can_auto_remediate(namespace, pod_name, "delete_pod")
            print(f"\n[+] Remediation guard: {reason}")

            if allowed:
                register_remediation_attempt(namespace, pod_name, "delete_pod")
                rem_success, rem_output = execute_action("delete_pod", params)

                print("\n[+] Auto-remediation output")
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


if __name__ == "__main__":
    main()