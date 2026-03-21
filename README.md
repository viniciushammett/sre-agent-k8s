# 🚀 SRE Agent for Kubernetes (AI-powered)

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

---

## 🧠 What this agent does

The agent can interpret human-like commands and execute actions such as:

### 🔎 Observability
- List pods
- List pods (wide)
- List services
- List deployments

### 🔬 Troubleshooting
- Get pod status
- Describe pod
- Describe service
- Get pod logs
- Get pod node

### 🛠️ Remediation
- Restart pods (via delete)
- Detect CrashLoopBackOff and act automatically

---

## ⚙️ How it works

1. User describes an incident in natural language
2. The analyzer parses the request
3. The agent maps it to an action
4. The remediator executes a `kubectl` command
5. Output is returned to the user

---

## 🧩 Architecture
User Input → Analyzer → Action Mapping → Remediator → Kubernetes

---

## 📦 Requirements

- Python 3.10+
- kubectl configured
- Access to a Kubernetes cluster

---

## 🚀 Usage

### Run the agent

```bash
sudo python3 main.py
```
## 🧪 Example commands:

*List pods:*
```bash
please list pods in namespace sre-demo
```

*List pods (wide):*
```bash
please list pods wide in namespace sre-demo
```

*Get pod node:*
```bash
which node is pod demo-nginx-xxx running on in namespace sre-demo
```

*Get logs:*
```bash
show logs for pod demo-nginx-xxx in namespace sre-demo
```

*Describe pod:*
```bash
describe pod demo-nginx-xxx in namespace sre-demo
```

*Describe service:*
```bash
describe service demo-nginx in namespace sre-demo
```

*Restart pod (CrashLoop simulation):*
```bash
pod demo-nginx-xxx is in CrashLoopBackOff in namespace sre-demo, please restart pod
```
## ⚠️ Important Notes

- This agent uses rule-based NLP (regex), not LLMs  
- Designed for local or controlled environments 

---

## 💡 Why this project?

Most modern AI agents rely on external LLMs (Claude, GPT, etc.), which introduces:

- 💰 Token costs  
- 🔐 Security concerns  
- 🌐 External dependencies  

This project explores an alternative:

👉 Local, deterministic, low-cost SRE automation
