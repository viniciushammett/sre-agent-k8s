import pytest
from analyzers.incident_analyzer import classify_input, suggest_remediation


# ---------------------------------------------------------------------------
# 1. Classificação request vs incident
# ---------------------------------------------------------------------------

def test_classify_list_namespaces():
    result = suggest_remediation("list namespaces")
    assert classify_input(result["action"]) == "request"


def test_classify_list_nodes():
    result = suggest_remediation("list nodes")
    assert classify_input(result["action"]) == "request"


def test_classify_list_all_pods():
    result = suggest_remediation("list all pods")
    assert classify_input(result["action"]) == "request"


def test_classify_check_pod_incident():
    result = suggest_remediation("check pod nginx in namespace default")
    assert classify_input(result["action"]) == "incident"


def test_classify_pod_crashing_incident():
    result = suggest_remediation("pod nginx is crashing")
    assert classify_input(result["action"]) == "incident"


# ---------------------------------------------------------------------------
# 2. Regex cluster-wide
# ---------------------------------------------------------------------------

def test_list_namespaces_action():
    result = suggest_remediation("list namespaces")
    assert result["action"] == "list_namespaces"


def test_list_nodes_action():
    result = suggest_remediation("list nodes")
    assert result["action"] == "list_nodes"


def test_list_all_pods_action():
    result = suggest_remediation("list all pods")
    assert result["action"] == "list_all_pods"


def test_list_all_pods_running_action():
    result = suggest_remediation("list all pods running")
    assert result["action"] == "list_all_pods"


def test_list_all_pods_in_all_namespaces_action():
    result = suggest_remediation("list all pods in all namespaces")
    assert result["action"] == "list_all_pods"


# ---------------------------------------------------------------------------
# 3. Regex list_pods com variações de namespace
# ---------------------------------------------------------------------------

def test_list_pods_in_namespace():
    result = suggest_remediation("list pods in sre-demo")
    assert result["action"] == "list_pods"
    assert result["params"]["namespace"] == "sre-demo"


def test_list_pods_in_namespace_keyword():
    result = suggest_remediation("list pods in namespace sre-demo")
    assert result["action"] == "list_pods"
    assert result["params"]["namespace"] == "sre-demo"


def test_list_pods_running_in_namespace():
    result = suggest_remediation("list pods running in sre-demo")
    assert result["action"] == "list_pods"
    assert result["params"]["namespace"] == "sre-demo"


def test_list_pods_running_in_namespace_keyword():
    result = suggest_remediation("list pods running in namespace sre-demo")
    assert result["action"] == "list_pods"
    assert result["params"]["namespace"] == "sre-demo"


def test_list_pods_in_namespace_suffix():
    result = suggest_remediation("list pods in sre-demo namespace")
    assert result["action"] == "list_pods"
    assert result["params"]["namespace"] == "sre-demo"


# ---------------------------------------------------------------------------
# 4. Regex de outros comandos
# ---------------------------------------------------------------------------

def test_check_pod_in_namespace():
    result = suggest_remediation("check pod nginx-123 in namespace sre-demo")
    assert result["action"] == "get_pod_status"
    assert result["params"]["pod_name"] == "nginx-123"
    assert result["params"]["namespace"] == "sre-demo"


def test_show_logs_for_pod():
    result = suggest_remediation("show logs for pod nginx-123 in namespace sre-demo")
    assert result["action"] == "get_pod_logs"
    assert result["params"]["pod_name"] == "nginx-123"
    assert result["params"]["namespace"] == "sre-demo"


def test_describe_pod_in_namespace():
    result = suggest_remediation("describe pod nginx-123 in namespace sre-demo")
    assert result["action"] == "describe_pod"
    assert result["params"]["pod_name"] == "nginx-123"
    assert result["params"]["namespace"] == "sre-demo"


# ---------------------------------------------------------------------------
# 5. Casos negativos
# ---------------------------------------------------------------------------

def test_unknown_input_what_is_kubernetes():
    result = suggest_remediation("what is kubernetes")
    assert result["action"] is None


def test_unknown_input_help_me():
    result = suggest_remediation("help me please")
    assert result["action"] is None


def test_empty_input():
    result = suggest_remediation("")
    assert result["action"] is None
