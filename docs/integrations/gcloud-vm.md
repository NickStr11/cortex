# Google Cloud VM

## Instance
- **Name**: cortex-vm
- **Type**: e2-small
- **OS**: Ubuntu 22.04
- **IP**: 34.159.55.61
- **Zone**: europe-west3-b
- **Budget**: ~$13/month from $300 free credits (expire May 2026)

## SSH Access

Regular SSH keys do NOT work. Use gcloud CLI only.

```bash
# Interactive shell
gcloud compute ssh cortex-vm --zone=europe-west3-b

# Run a command
gcloud compute ssh cortex-vm --zone=europe-west3-b --command="systemctl status cortex-daily"

# Copy file TO VM
gcloud compute scp local_file cortex-vm:/remote/path --zone=europe-west3-b

# Copy file FROM VM
gcloud compute scp cortex-vm:/remote/path local_file --zone=europe-west3-b
```

## Services

### cortex-daily (TG Digest)
- **Timer**: `cortex-daily.timer` fires at 03:00 UTC (06:00 MSK)
- **Service**: `cortex-daily.service` runs digest pipeline

```bash
# Check timer
systemctl status cortex-daily.timer

# Check last run logs
journalctl -u cortex-daily -n 50

# Manual trigger
systemctl start cortex-daily
```

## Python Environment
- System python3 available
- Venv: `/opt/cortex/.venv`
- Activate: `source /opt/cortex/.venv/bin/activate`
- Install deps: `pip install -r requirements.txt`

## File Locations
- Project root: `/opt/cortex/`
- Digest code: `/opt/cortex/tools/tg-monitor/`
- Env vars: `/opt/cortex/.env`

## Gotchas
- No Docker installed. Everything runs via systemd + venv.
- Firewall: only SSH (22) open by default. Open ports via GCP console if needed.
- Disk: 10GB standard, check with `df -h`.
