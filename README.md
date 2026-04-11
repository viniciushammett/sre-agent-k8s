# SRE Agent for Kubernetes (AI-powered)

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Automation-326CE5?logo=kubernetes&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)
![AI Type](https://img.shields.io/badge/AI-Rule--Based-orange)

A lightweight SRE Agent designed to analyze incidents described in natural language and execute Kubernetes operations automatically.

This project simulates real-world SRE workflows by combining:

- Incident analysis (NLP via rules)
- Kubernetes operations
- Automated remediation
- Deterministic diagnostics and root cause hints

---

## 🧠 What this agent does

The agent can interpret human-like commands and execute actions such as:

### 🔎 Observability
- List pods / wide / services / deployments
- List namespaces / nodes / all pods (cluster-wide)

### 🔬 Troubleshooting
- Get pod status (structured JSON)
- Describe pod / service
- Get pod logs (container-aware)
- Get pod previous logs (CrashLoopBackOff)
- Get pod node

### 🛠️ Remediation
- Restart pods via delete (standalone pods)
- Rollout restart deployments (preferred when pod has a deployment owner)
- Rollout restart StatefulSets (with impact warning)
- Rollout restart DaemonSets (with cluster-wide impact warning)
- Detect CrashLoopBackOff and act automatically
- Guarded auto-remediation (limit per workload)

### 🧠 Intelligent Diagnostics (Deterministic)
- Detect pod health state (healthy / unhealthy / unknown)
- Guided diagnosis by workload state:
  - CrashLoopBackOff — previous logs + restart count
  - OOMKilled — memory limits extraction
  - ImagePullBackOff / ErrImagePull — registry and image info
  - Pending — scheduling constraints, taints, PVC
  - CreateContainerConfigError — secret / configmap / volume detection
  - Running unhealthy — liveness / readiness probe analysis
- Infer probable cause from logs using heuristics:
  - Connection issues
  - Permission errors
  - Missing files
  - Image pull failures
  - Architecture mismatch
  - Memory issues

### 🗂️ Workload-Aware Actions
- Resolve full ownerReference chain: Pod → ReplicaSet → Deployment / StatefulSet / DaemonSet / Job → CronJob
- Apply workload-specific remediation rules
- Block restart for Job and CronJob with actionable guidance

### 🖥️ Interactive CLI
- REPL mode with persistent session context
- Single-command mode for scripting
- Dry-run mode (`--dry-run`) — simulate destructive actions safely
- Command history in memory
- Built-in help reference

### 🗂️ Session Context
- Active namespace persisted across commands
- Active pod inferred from last operation
- Dynamic prompt: `sre-agent [namespace]>`
- Short commands without repeating namespace/pod

### 📊 Incident Reporting
- Structured JSONL export (`incident_history.jsonl`) — append-only
- Only unhealthy incidents are persisted — healthy pods are not incidents
- Session ID per session displayed in header
- Query commands: `incidents`, `incidents last N`, `incidents all`

---

## ⚙️ How it works

1. User describes an incident in natural language
2. The analyzer parses the request and classifies it (request vs incident)
3. The agent maps it to an action
4. The remediator executes a `kubectl` command
5. The state evaluator determines health and next steps
6. The WorkloadClassifier resolves the pod's owner chain
7. The agent executes diagnostic follow-up (if applicable)
8. The DiagnosisEngine investigates the workload state
9. The log analyzer infers the probable cause from log output
10. The cause-based remediator produces a deterministic action plan
11. The agent applies auto-remediation (if needed and allowed by safety gates)
12. A structured incident summary is generated, displayed and stored

---

## 🧩 Architecture

```
User Input
→ Incident Analyzer (NLP / regex)
→ Action Mapping
→ Remediator (kubectl)
→ State Evaluator
→ WorkloadClassifier (owner resolution)
→ Follow-up Engine
→ DiagnosisEngine (guided investigation)
→ Log Analyzer
→ Cause-Based Remediator
→ Remediation Guard
→ Incident Reporter (JSONL)
→ Incident Logger
```

---

## 📦 Requirements

- Python 3.10+
- kubectl configured
- Access to a Kubernetes cluster

---

## ☁️ Cloud Compatibility

The agent is cloud-agnostic by design. It uses `kubectl` as the sole
execution path and inherits the current kubectl context from the environment.

Any cluster reachable via kubectl is supported:

| Provider | Setup |
|---|---|
| AWS EKS | `aws eks update-kubeconfig --name <cluster>` |
| Azure AKS | `az aks get-credentials --name <cluster> --resource-group <rg>` |
| GCP GKE | `gcloud container clusters get-credentials <cluster>` |
| OCI | `oci ce cluster create-kubeconfig --cluster-id <id>` |
| Local (minikube / kind / k3d) | already configured |

No code changes required. The agent works wherever `kubectl get pods` works.

---

## 🚀 Usage

### Run the agent

**Interactive REPL mode** (recommended):
```bash
source venv/bin/activate
python main.py
```

**Single command mode:**
```bash
source venv/bin/activate
python main.py "list pods in namespace sre-demo"
```

**Dry-run mode** (simulate destructive actions):
```bash
source venv/bin/activate
python main.py --dry-run
python main.py --dry-run "check pod demo-nginx-xxx in namespace sre-demo"
```

### Exit codes (single command mode)

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | kubectl error |
| 2 | Invalid input |
| 3 | Timeout |
| 99 | Unexpected error |

---

## 🧪 Example commands

### 1. Cluster-wide (no namespace required)

```bash
list namespaces
list nodes
list all pods
```

### 2. Namespace operations (explicit namespace)

```bash
list pods in namespace sre-demo
list pods wide in namespace sre-demo
list services in namespace sre-demo
list deployments in namespace sre-demo
which node is pod demo-nginx-xxx running on in namespace sre-demo
describe service demo-nginx in namespace sre-demo
rollout restart deployment demo-nginx in namespace sre-demo
```

### 3. Session context — set namespace, then use short commands

```bash
set namespace sre-demo
list pods
list services
list deployments
```

### 4. Troubleshooting with active context

```bash
check pod demo-nginx-xxx
describe pod demo-nginx-xxx
logs
show previous logs
restart pod demo-nginx-xxx
rollout restart deployment demo-nginx
```

### 5. Inspect / history / help

```bash
show context
clear context
history
help
```

### 6. Incident reporting

```bash
incidents                  # current session incidents
incidents last 5           # last 5 incidents of session
incidents all              # all incidents across sessions
```

---

## ⚠️ Important Notes

- This agent uses rule-based NLP (regex), not LLMs
- Designed for local or controlled environments
- All decisions are deterministic and explainable
- Dry-run mode simulates all destructive actions safely

---

## 📊 Incident Summary

After execution, the agent generates a structured summary:

- Detected state
- Health status
- Workload type and owner
- Container name / restart count
- Diagnosis: cause category, hypothesis, evidence, confidence
- Follow-up executed
- Probable cause / matched pattern
- Cause-based plan applied
- Recommended checks
- Requires human review
- Remediation applied
- Final outcome

Incidents are stored in two formats:

```bash
incident_history.log    # human-readable log
incident_history.jsonl  # structured JSONL (unhealthy incidents only)
```

---

## 🔒 Safety & Control

Auto-remediation is protected by multiple safety gates:
- Max 2 remediations per workload (remediation guard)
- Blocked if `requires_human_review` is true for the matched cause
- Blocked if log analysis confidence is `low`
- Blocked if no safe remediation is defined for the pattern
- Job and CronJob workloads are always blocked — restart doesn't apply
- Dry-run mode simulates all destructive actions without executing kubectl

All remediation actions are logged:

```bash
remediation.log
```

---

## 💡 Why this project?

Most modern AI agents rely on external LLMs (Claude, GPT, etc.), which introduces:

- 💰 Token costs
- 🔐 Security concerns
- 🌐 External dependencies

This project explores an alternative:

- Local, deterministic, low-cost SRE automation
- Full control over execution
- Explainable decision-making
- No external APIs or token usage