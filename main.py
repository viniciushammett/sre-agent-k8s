from analyzers.incident_analyzer import suggest_remediation
from remediators.kubectl_remediator import (
    delete_pod,
    describe_pod,
    describe_service,
    get_pod_logs,
    get_pod_node,
    get_pod_status,
    list_deployments,
    list_pods,
    list_services,
)


def main():
    print("=" * 60)
    print("SRE AGENT :: HTTP + SSH + K8s + Incident Analysis")
    print("=" * 60)

    incident = input("\nDescribe the incident: ").strip()
    analysis = suggest_remediation(incident)

    action = analysis.get("action")
    params = analysis.get("params", {})
    reason = analysis.get("reason", "")

    print("\n[+] Analysis result")
    print(f"Reason: {reason}")
    print(f"Suggested action: {action}")
    print(f"Parameters: {params}")

    if action == "list_pods":
        success, output = list_pods(params["namespace"], params.get("wide", False))
    elif action == "list_deployments":
        success, output = list_deployments(params["namespace"])
    elif action == "get_pod_status":
        success, output = get_pod_status(params["namespace"], params["pod_name"])
    elif action == "describe_pod":
        success, output = describe_pod(params["namespace"], params["pod_name"])
    elif action == "describe_service":
        success, output = describe_service(params["namespace"], params["service_name"])
    elif action == "delete_pod":
        success, output = delete_pod(params["namespace"], params["pod_name"])
    elif action == "list_services":
        success, output = list_services(params["namespace"])
    elif action == "get_pod_node":
        success, output = get_pod_node(params["namespace"], params["pod_name"])
    elif action == "get_pod_logs":
        success, output = get_pod_logs(params["namespace"], params["pod_name"])
    else:
        print("\n[-] No remediation suggested for this incident.")
        return

    print("\n[+] Execution result")
    print(f"Success: {success}")
    print(output)


if __name__ == "__main__":
    main()