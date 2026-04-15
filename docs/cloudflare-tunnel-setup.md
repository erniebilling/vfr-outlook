# Cloudflare Tunnel Setup: www.vfr-outlook.broken-top.com

Exposes the app publicly via a Cloudflare Tunnel — no public IP or open inbound ports required.

## Architecture

```
Browser → Cloudflare Edge → cloudflared pods (in cluster)
                                    ↓
              /api/* → vfr-backend.vfr-outlook.svc:8000
              /*     → vfr-frontend.vfr-outlook.svc:80
```

## Prerequisites

- `cloudflared` CLI installed locally
- Access to the `broken-top.com` zone in Cloudflare

## Setup Steps

### 1. Install cloudflared and authenticate

```bash
# macOS
brew install cloudflare/cloudflare/cloudflared

# Linux
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

cloudflared tunnel login
```

### 2. Create the tunnel and DNS record

```bash
cloudflared tunnel create vfr-outlook
# Note the tunnel ID (UUID) printed in the output

cloudflared tunnel route dns vfr-outlook www.vfr-outlook.broken-top.com
```

This creates a CNAME in Cloudflare DNS: `www.vfr-outlook.broken-top.com → <tunnel-id>.cfargotunnel.com`

### 3. Create the credentials secret in the cluster

```bash
kubectl create secret generic cloudflared-credentials \
  --from-file=credentials.json=$HOME/.cloudflare/<tunnel-id>.json \
  -n vfr-outlook
```

### 4. Update the tunnel ID in the ConfigMap

Edit `k8s/cloudflared.yaml` and replace `<TUNNEL_ID>` with the UUID from step 2.

### 5. Apply the manifests

```bash
kubectl apply -f k8s/cloudflared.yaml -n vfr-outlook
kubectl apply -f k8s/backend.yaml -n vfr-outlook
kubectl apply -f k8s/ingress.yaml -n vfr-outlook
```

### 6. Verify

```bash
# Check cloudflared pods are running
kubectl get pods -n vfr-outlook -l app=cloudflared

# Check tunnel has active connections
cloudflared tunnel info vfr-outlook
```

## Kubernetes Resources

The tunnel is defined in `k8s/cloudflared.yaml`:

- **ConfigMap** `cloudflared-config` — tunnel ID and ingress routing rules
- **Deployment** `cloudflared` — 2 replicas for redundancy, mounts config and credentials

The credentials JSON is stored in **Secret** `cloudflared-credentials` (created manually above, not tracked in git).

## Updating the Tunnel

If you need to recreate the credentials secret:

```bash
kubectl delete secret cloudflared-credentials -n vfr-outlook
kubectl create secret generic cloudflared-credentials \
  --from-file=credentials.json=$HOME/.cloudflare/<tunnel-id>.json \
  -n vfr-outlook
kubectl rollout restart deployment/cloudflared -n vfr-outlook
```

## Teardown

```bash
kubectl delete -f k8s/cloudflared.yaml -n vfr-outlook
kubectl delete secret cloudflared-credentials -n vfr-outlook
cloudflared tunnel delete vfr-outlook
```
