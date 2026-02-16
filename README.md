# Auto Pod Deletion Pipeline

An automated Kubernetes security pipeline that detects suspicious shell activity inside containers using **Falco** and automatically deletes the offending pods via a custom webhook.

## 📋 Overview

This project implements a security response pipeline with the following flow:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Shell spawned  │ ──▶ │  Falco detects  │ ──▶ │  Falcosidekick  │ ──▶ │  Webhook deletes│
│  in container   │     │  the event      │     │  sends alert    │     │  the pod        │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Components

| Component | Description |
|-----------|-------------|
| **Falco** | Runtime security tool that detects abnormal behavior in containers |
| **Falcosidekick** | Forwards Falco alerts to various outputs (webhook in our case) |
| **Webhook Server** | Flask-based server that receives alerts and deletes malicious pods |
| **Custom Rules** | Falco rules to detect shell spawning in containers |

---

## 🛠️ Prerequisites

- **Kubernetes cluster** (minikube, kind, k3s, or cloud-based)
- **kubectl** configured to access your cluster
- **Helm 3** installed
- **Docker** (optional, for building custom images)

---

## 🚀 Initial Setup

### Step 1: Start Your Kubernetes Cluster

If using **minikube**:
```bash
minikube start --driver=docker
```

If using **kind**:
```bash
kind create cluster --name auto-pod-deletion
```

### Step 2: Add Falco Helm Repository

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update
```

### Step 3: Create the Webhook Namespace

```bash
kubectl create namespace webhook
```

---

## 📦 Deployment

### Option A: Quick Deployment (All-in-One)

This method uses a single manifest that includes everything needed for the webhook:

```bash
# Deploy the webhook server (includes namespace, deployment, service, RBAC)
kubectl apply -f webhook/all-in-one.yaml

# Wait for webhook to be ready
kubectl wait --for=condition=ready pod -l app=webhook-server -n webhook --timeout=120s
```

### Option B: Manual Deployment (Step by Step)

#### 1. Build and Push Webhook Image (Optional)

If you want to use your own image:

```bash
cd webhook
docker build -t <your-dockerhub-username>/webhook-server:latest .
docker push <your-dockerhub-username>/webhook-server:latest
```

Then update `webhook/webhook.yaml` with your image name and apply:

```bash
kubectl create namespace webhook
kubectl apply -f webhook/webhook.yaml
```

---

### Step 4: Install Falco with Custom Rules

#### Create the Custom Rules ConfigMap

```bash
kubectl create configmap falco-custom-rules \
  --from-file=custom-rules.yaml=custom-rules.yaml \
  -n falco --dry-run=client -o yaml | kubectl apply -f -
```

#### Install Falco using Helm

```bash
helm install falco falcosecurity/falco \
  --namespace falco \
  --create-namespace \
  -f values.yaml
```

**Alternative:** Use the pre-configured values file in the `falco/` directory:

```bash
helm install falco falcosecurity/falco \
  --namespace falco \
  --create-namespace \
  -f falco/values.yaml
```

#### Verify Falco Installation

```bash
# Check Falco pods are running
kubectl get pods -n falco

# Check Falco logs
kubectl logs -l app.kubernetes.io/name=falco -n falco -f
```

---

## ✅ Verify the Setup

### 1. Check Webhook Server Status

```bash
kubectl get pods -n webhook
kubectl logs -l app=webhook-server -n webhook -f
```

### 2. Check Falcosidekick Status

```bash
kubectl get pods -n falco -l app.kubernetes.io/name=falcosidekick
```

---

## 🧪 Testing the Pipeline

### Deploy an Attacker Pod

```bash
# Deploy the test attacker pod
kubectl apply -f attacker.yaml

# Or use the one in attacker/ directory
kubectl apply -f attacker/attacker.yaml
```

### Trigger the Detection

Open a shell inside the attacker pod:

```bash
kubectl exec -it ubuntu-attacker -- /bin/bash
```

### Expected Behavior

1. Falco detects the shell spawn
2. Falcosidekick forwards the alert to the webhook
3. The webhook receives the alert and deletes the pod
4. Your `kubectl exec` session will be terminated

### Monitor the Pipeline

In separate terminals, monitor:

```bash
# Terminal 1: Watch pods
kubectl get pods -w

# Terminal 2: Watch webhook logs
kubectl logs -l app=webhook-server -n webhook -f

# Terminal 3: Watch Falco logs
kubectl logs -l app.kubernetes.io/name=falco -n falco -f
```

---

## 🔧 Custom Test Pod

A custom test container is provided that simulates a vulnerable workload:

### Build and Deploy Custom Test Pod

```bash
cd custom-test

# Build the image
docker build -t <your-dockerhub-username>/custom-test:latest .
docker push <your-dockerhub-username>/custom-test:latest

# Deploy the pod
kubectl apply -f custom-pod.yaml
```

### Test with Custom Pod

```bash
kubectl exec -it custom-attacker -- /bin/bash
```

---

## 📁 Project Structure

```
auto-pod deletion/
├── README.md                    # This file
├── attacker.yaml                # Simple attacker pod for testing
├── custom-rules.yaml            # Falco custom rules (standalone)
├── values.yaml                  # Helm values for Falco installation
├── attacker/
│   └── attacker.yaml            # Alternative attacker pod manifest
├── custom-test/
│   ├── custom-pod.yaml          # Custom test pod deployment
│   └── dockerfile               # Dockerfile for custom test image
├── falco/
│   └── values.yaml              # Complete Falco Helm values
└── webhook/
    ├── all-in-one.yaml          # Complete webhook deployment (recommended)
    ├── Dockerfile               # Webhook server Docker image
    ├── webhook.py               # Flask webhook server source
    └── webhook.yaml             # Separate webhook K8s manifests
```

---

## 🔍 Configuration Details

### Falco Custom Rule

The detection rule triggers when a shell (bash, sh, zsh) is spawned inside a container:

```yaml
- rule: Terminal shell in container
  desc: Detects shell spawned inside a container
  condition: container.id != host and proc.name in (bash, sh, zsh)
  output: "Shell spawned inside container (user=%user.name command=%proc.cmdline container=%container.name k8s_pod=%k8s.pod.name k8s_ns=%k8s.ns.name)"
  priority: NOTICE
  tags: ["container", "shell"]
```

### Webhook Configuration

The webhook listens on port 5000 and:
- Receives JSON alerts from Falcosidekick
- Checks if the alert rule contains "shell"
- Extracts pod name and namespace from the alert
- Deletes the offending pod using `kubectl`

---

## 🧹 Cleanup

To remove all components:

```bash
# Delete test pods
kubectl delete -f attacker.yaml --ignore-not-found
kubectl delete -f attacker/attacker.yaml --ignore-not-found
kubectl delete -f custom-test/custom-pod.yaml --ignore-not-found

# Delete webhook
kubectl delete -f webhook/all-in-one.yaml --ignore-not-found

# Uninstall Falco
helm uninstall falco -n falco

# Delete namespaces
kubectl delete namespace webhook --ignore-not-found
kubectl delete namespace falco --ignore-not-found
```

---

## ⚠️ Important Notes

1. **Production Use**: This is a demonstration project. For production, consider:
   - Adding authentication to the webhook
   - Implementing rate limiting
   - Adding more sophisticated rules
   - Using TLS for webhook communication

2. **RBAC**: The webhook service account has cluster-wide pod deletion permissions. Restrict this in production.

3. **False Positives**: The current rule triggers on ANY shell spawn. You may want to add exceptions for legitimate use cases.

---

## 🐛 Troubleshooting

### Webhook not receiving alerts

1. Check Falcosidekick configuration:
   ```bash
   kubectl get configmap -n falco -o yaml | grep webhook
   ```

2. Verify webhook service is reachable:
   ```bash
   kubectl run test-curl --rm -it --image=curlimages/curl -- \
     curl -X POST http://webhook-service.webhook.svc.cluster.local:5000/ \
     -H "Content-Type: application/json" \
     -d '{"rule":"test shell","output_fields":{"k8s.pod.name":"test","k8s.ns.name":"default"}}'
   ```

### Falco not detecting shell spawn

1. Verify Falco is running:
   ```bash
   kubectl logs -l app.kubernetes.io/name=falco -n falco --tail=50
   ```

2. Check custom rules are loaded:
   ```bash
   kubectl exec -it $(kubectl get pod -l app.kubernetes.io/name=falco -n falco -o jsonpath='{.items[0].metadata.name}') -n falco -- cat /etc/falco/rules.d/
   ```

### Pod not being deleted

1. Check webhook logs for errors:
   ```bash
   kubectl logs -l app=webhook-server -n webhook
   ```

2. Verify RBAC permissions:
   ```bash
   kubectl auth can-i delete pods --as=system:serviceaccount:webhook:webhook-sa
   ```

---

## 📚 References

- [Falco Documentation](https://falco.org/docs/)
- [Falcosidekick Documentation](https://github.com/falcosecurity/falcosidekick)
- [Falco Helm Charts](https://github.com/falcosecurity/charts)
