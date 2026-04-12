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
- Rollout restart StatefulSets (with PVC impact warning)
- Rollout restart DaemonSets (with cluster-wide impact warning)
- Detect CrashLoopBackOff and act automatically
- Guarded auto-remediation (limit per workload)

### 🧠 Intelligent Diagnostics (Deterministic)
- Guided diagnosis by workload state:
  - CrashLoopBackOff — previous logs + restart count
  - OOMKilled — memory limits extraction
  - ImagePullBackOff / ErrImagePull — registry and image info
  - Pending — scheduling constraints, taints, PVC
  - CreateContainerConfigError — secret / configmap / volume detection
  - Running unhealthy — liveness / readiness probe analysis
- Infer probable cause from logs:
  - Connection issues, permission errors, missing files
  - Image pull failures, architecture mismatch, memory issues

### 🗂️ Workload-Aware Actions
- Resolve full ownerReference chain: Pod → ReplicaSet → Deployment / StatefulSet / DaemonSet / Job → CronJob
- Apply workload-specific remediation rules
- Block restart for Job and CronJob with actionable guidance

### 🖥️ Interactive CLI
- REPL mode with persistent session context
- Single-command mode for scripting
- Dry-run mode (`--dry-run`) — simulate destructive actions safely
- Auto mode (`--auto`) — skip confirmation dialogs
- Command history with arrow key navigation (↑↓)
- Built-in help reference

### 🗂️ Session Context
- Active namespace and pod persisted across commands
- Pod cleared automatically when namespace changes
- Dynamic prompt: `sre-agent [namespace]>`
- Short commands without repeating namespace/pod
- `use last` — reuse last pod and action from context

### 🔍 Pod Resolver
- Partial name resolution: `check pod payment-worker` → resolves to `payment-worker-698f78f485-rh7r6`
- Ambiguity handling: lists candidates when multiple matches found
- Suggests last used pod when pod not found

### 📊 Incident Reporting
- Structured JSONL export (`incident_history.jsonl`) — append-only
- Only unhealthy incidents are persisted
- Session ID per session displayed in header
- `incidents` filters by active namespace
- `incidents last N`, `incidents all` with namespace tag per record

---

## ⚙️ How it works

1. User describes an incident in natural language
2. The analyzer parses and classifies the request (request vs incident)
3. Pod Resolver resolves partial names to real pod names
4. The agent maps to an action and executes via `kubectl`
5. The state evaluator determines health and next steps
6. The WorkloadClassifier resolves the pod's owner chain
7. The DiagnosisEngine investigates the workload state
8. The log analyzer infers the probable cause
9. In interactive mode: confirmation dialog before remediation
10. A structured incident summary is generated and optionally displayed

---

## 🧩 Architecture

```
User Input
→ Incident Analyzer (NLP / regex)
→ Pod Resolver (partial name resolution)
→ Action Mapping
→ Remediator (kubectl)
→ State Evaluator
→ WorkloadClassifier (owner resolution)
→ Follow-up Engine
→ DiagnosisEngine (guided investigation)
→ Log Analyzer
→ Confirmation Dialog (interactive mode)
→ Cause-Based Remediator
→ Remediation Guard
→ Incident Reporter (JSONL)
→ Incident Logger
```

---

## ☁️ Cloud Compatibility

The agent is cloud-agnostic by design. It uses `kubectl` as the sole execution path and inherits the current kubectl context from the environment.

| Provider | Setup |
|---|---|
| AWS EKS | `aws eks update-kubeconfig --name <cluster>` |
| Azure AKS | `az aks get-credentials --name <cluster> --resource-group <rg>` |
| GCP GKE | `gcloud container clusters get-credentials <cluster>` |
| OCI | `oci ce cluster create-kubeconfig --cluster-id <id>` |
| Local (minikube / kind / k3d) | already configured |

No code changes required. The agent works wherever `kubectl get pods` works.

---

## 📦 Requirements

- Python 3.10+
- kubectl configured and pointing to a cluster

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
python main.py "list pods in namespace sre-demo"
```

**Dry-run mode** (simulate destructive actions):
```bash
python main.py --dry-run
python main.py --dry-run "check pod demo-nginx in namespace sre-demo"
```

**Auto mode** (skip confirmation dialogs):
```bash
python main.py --auto
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

### 1. Cluster-wide

```bash
list namespaces
list nodes
list all pods
```

### 2. Namespace operations

```bash
list pods in namespace sre-demo
list pods wide in namespace sre-demo
list services in namespace sre-demo
list deployments in namespace sre-demo
rollout restart deployment demo-nginx in namespace sre-demo
```

### 3. Session context — set namespace once, use short commands

```bash
set namespace sre-demo
list pods
list services
check pod demo-nginx          # resolves partial name automatically
logs                          # uses active pod from context
show previous logs            # uses active pod from context
prev logs                     # same as above
describe pod                  # uses active pod from context
use last                      # reuse last pod and action
```

### 4. Pod name variations (all recognized)

```bash
check pod demo-nginx
inspect pod demo-nginx
analyze pod demo-nginx
get status of pod demo-nginx
```

### 5. Remediation

```bash
restart pod demo-nginx
rollout restart deployment demo-nginx
```

### 6. Inspect / history / help

```bash
show context
clear context
history
clear
help
```

### 7. Incident reporting

```bash
incidents                  # current namespace incidents
incidents last 5           # last 5 of current namespace
incidents all              # all namespaces with [ns:...] tag
```

---

## ⚠️ Important Notes

- Rule-based NLP (regex), not LLMs — fully deterministic
- Designed for local or controlled environments
- Dry-run mode simulates all destructive actions safely
- Partial pod names are automatically resolved

---

## 📊 Incident Summary

After execution, the agent generates a structured summary (optional in interactive mode):

- Detected state / health status
- Workload type and owner
- Diagnosis: cause category, hypothesis, evidence, confidence
- Follow-up executed / probable cause
- Remediation applied / final outcome

Incidents stored in:

```bash
incident_history.log    # human-readable
incident_history.jsonl  # structured JSONL (unhealthy only)
```

---

## 🔒 Safety & Control

- Max 2 remediations per workload (remediation guard)
- Blocked if `requires_human_review` is true
- Blocked if log analysis confidence is `low`
- Job and CronJob workloads always blocked — restart doesn't apply
- Dry-run mode simulates without executing kubectl
- Interactive confirmation before any destructive action

```bash
remediation.log    # all remediation actions logged
```

---

## 💡 Why this project?

Most modern AI agents rely on external LLMs (Claude, GPT, etc.), which introduces token costs, security concerns, and external dependencies.

This project explores an alternative:

- Local, deterministic, low-cost SRE automation
- Full control over execution
- Explainable decision-making
- No external APIs or token usage
