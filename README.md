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
- List pods
- List pods (wide)
- List services
- List deployments

### 🔬 Troubleshooting
- Get pod status (structured JSON)
- Describe pod
- Describe service
- Get pod logs (container-aware)
- Get pod previous logs (CrashLoopBackOff)
- Get pod node

### 🛠️ Remediation
- Restart pods (via delete)
- Detect CrashLoopBackOff and act automatically
- Guarded auto-remediation (limit per workload)

### 🧠 Intelligent Diagnostics (Deterministic)
- Detect pod health state (healthy / unhealthy / unknown)
- Suggest follow-up actions automatically
- Execute diagnostic follow-up before remediation
- Infer probable cause from logs using heuristics:
  - Connection issues
  - Permission errors
  - Missing files
  - Image pull failures
  - Architecture mismatch
  - Memory issues

### 🖥️ Interactive CLI
- REPL mode with persistent session context
- Single-command mode for scripting
- Command history in memory
- Built-in help reference

### 🗂️ Session Context
- Active namespace persisted across commands
- Active pod inferred from last operation
- Dynamic prompt: `sre-agent [namespace]>`
- Short commands without repeating namespace/pod

---

## ⚙️ How it works

1. User describes an incident in natural language  
2. The analyzer parses the request  
3. The agent maps it to an action  
4. The remediator executes a `kubectl` command  
5. The state evaluator determines health and next steps  
6. The agent executes diagnostic follow-up (if applicable)  
7. The log analyzer infers the probable cause from log output  
8. The cause-based remediator produces a deterministic action plan  
9. The agent applies auto-remediation (if needed and allowed by safety gates)  
10. A structured incident summary is generated and stored  

---

## 🧩 Architecture

User Input  
→ Analyzer  
→ Action Mapping  
→ Remediator (kubectl)  
→ State Evaluator  
→ Follow-up Engine  
→ Log Analyzer  
→ Cause-Based Remediator  
→ Remediation Guard  
→ Incident Logger  

---

## 📦 Requirements

- Python 3.10+
- kubectl configured
- Access to a Kubernetes cluster

---

## 🚀 Usage

### Run the agent

**Interactive REPL mode** (recommended):
```bash
source venv/bin/activate
python main.py
```

**Single command mode**:
```bash
source venv/bin/activate
python main.py "list pods in namespace sre-demo"
```
## 🧪 Example commands

### 1. Cluster-wide (no namespace required)

*List all namespaces:*
```bash
list namespaces
```

*List all nodes:*
```bash
list nodes
```

*List all pods across all namespaces:*
```bash
list all pods
```

### 2. Namespace operations (explicit namespace)

*List pods in a namespace:*
```bash
list pods in namespace sre-demo
```

*List pods wide:*
```bash
list pods wide in namespace sre-demo
```

*List services:*
```bash
list services in namespace sre-demo
```

*List deployments:*
```bash
list deployments in namespace sre-demo
```

*Get pod node:*
```bash
which node is pod demo-nginx-xxx running on in namespace sre-demo
```

*Describe service:*
```bash
describe service demo-nginx in namespace sre-demo
```

*Restart pod (CrashLoop):*
```bash
pod demo-nginx-xxx is in CrashLoopBackOff in namespace sre-demo, please restart pod
```

### 3. Session context — set namespace, then use short commands

*Set active namespace once:*
```bash
set namespace sre-demo
```

*From here on, namespace is inferred automatically:*
```bash
list pods
list services
list deployments
```

### 4. Troubleshooting with active context

*Check pod status (full diagnostic + remediation pipeline):*
```bash
check pod demo-nginx-xxx
```

*Describe pod:*
```bash
describe pod demo-nginx-xxx
```

*Get logs:*
```bash
logs
```

*Get previous logs (CrashLoopBackOff):*
```bash
show previous logs
```

*Restart pod:*
```bash
restart pod demo-nginx-xxx
```

### 5. Inspect / history / help

*Show active session context:*
```bash
show context
```

*Clear session context:*
```bash
clear context
```

*Show command history:*
```bash
history
```

*Show all available commands:*
```bash
help
```

---

## ⚠️ Important Notes

- This agent uses rule-based NLP (regex), not LLMs  
- Designed for local or controlled environments
- All decisions are deterministic and explainable 

---

## 📊 Incident Summary (New)

After execution, the agent generates a structured summary:

- Detected state  
- Health status  
- Container name  
- Restart count  
- Follow-up executed  
- Probable cause  
- Confidence  
- Matched pattern  
- Cause-based plan applied  
- Recommended checks  
- Requires human review  
- Safe remediation selected  
- Cause explanation  
- Remediation applied  
- Final outcome  

Additionally, all incidents are stored in:

```bash
incident_history.log
```
---

## 🔒 Safety & Control

- Auto-remediation is protected by multiple safety gates:
  - Max 2 remediations per workload (remediation guard)  
  - Blocked if `requires_human_review` is true for the matched cause  
  - Blocked if log analysis confidence is `low`  
  - Blocked if no safe remediation is defined for the pattern  

- All remediation actions are logged:

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

-  Local, deterministic, low-cost SRE automation
-  Full control over execution
-  Explainable decision-making
-  No external APIs or token usage
