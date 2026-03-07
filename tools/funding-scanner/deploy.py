"""Deploy funding-scanner to Google Cloud VM via gcloud SCP."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

VM = "cortex-vm"
ZONE = "europe-west3-b"
REMOTE_DIR = "/opt/funding-scanner"

LOCAL_DIR = Path(__file__).parent
FILES = [
    "config.py",
    "exchanges.py",
    "scanner.py",
    "db.py",
    "alerts.py",
    "main.py",
    "web.py",
    "pyproject.toml",
]

SYSTEMD_SCANNER = """\
[Unit]
Description=Funding Rate Scanner (hourly scan)
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/opt/funding-scanner
EnvironmentFile=/opt/funding-scanner/.env
ExecStart=/root/.local/bin/uv run python main.py
TimeoutStartSec=120
"""

SYSTEMD_TIMER = """\
[Unit]
Description=Run Funding Scanner every hour

[Timer]
OnCalendar=*:00:00
Persistent=true
RandomizedDelaySec=60

[Install]
WantedBy=timers.target
"""

SYSTEMD_WEB = """\
[Unit]
Description=Funding Scanner Web Dashboard
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/funding-scanner
EnvironmentFile=/opt/funding-scanner/.env
ExecStart=/root/.local/bin/uv run uvicorn web:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""


def gcloud_ssh(cmd: str) -> str:
    """Run command on VM via gcloud."""
    full = f'gcloud compute ssh {VM} --zone={ZONE} --command="{cmd}"'
    result = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=120)
    if result.returncode != 0 and result.stderr:
        err = result.stderr.strip()
        if "WARNING" not in err and "Updated" not in err:
            print(f"  stderr: {err[:200]}")
    return result.stdout


def gcloud_scp(local: str, remote: str) -> None:
    """Copy file to VM via gcloud SCP."""
    cmd = f'gcloud compute scp "{local}" {VM}:{remote} --zone={ZONE}'
    subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)


def deploy() -> None:
    print("Deploying to Google Cloud VM...")

    # Create remote dir
    gcloud_ssh(f"mkdir -p {REMOTE_DIR}")

    # Upload files
    for f in FILES:
        local = LOCAL_DIR / f
        remote = f"{REMOTE_DIR}/{f}"
        print(f"  Uploading {f}...")
        gcloud_scp(str(local), remote)

    # Install uv if missing
    uv_check = gcloud_ssh("which uv || echo NO_UV").strip()
    if "NO_UV" in uv_check:
        print("  Installing uv...")
        gcloud_ssh("curl -LsSf https://astral.sh/uv/install.sh | sh")

    # Sync deps
    print("  Syncing dependencies...")
    out = gcloud_ssh(f"cd {REMOTE_DIR} && /root/.local/bin/uv sync 2>&1 | tail -5")
    print(f"  {out.strip()}")

    # Create .env if missing
    env_check = gcloud_ssh(f"test -f {REMOTE_DIR}/.env && echo EXISTS || echo MISSING").strip()
    if "MISSING" in env_check:
        # Read TG token from local project .env
        tg_token = _get_tg_token()
        env_content = f"TG_BOT_TOKEN={tg_token}\\nTG_CHAT_ID=691773226\\n"
        gcloud_ssh(f"echo -e '{env_content}' > {REMOTE_DIR}/.env")
        print("  Created .env")
    else:
        print("  .env exists")

    # Write systemd units
    _write_systemd("funding-scanner.service", SYSTEMD_SCANNER)
    _write_systemd("funding-scanner.timer", SYSTEMD_TIMER)
    _write_systemd("funding-web.service", SYSTEMD_WEB)
    print("  Wrote systemd units")

    # Reload and enable
    gcloud_ssh("systemctl daemon-reload")
    gcloud_ssh("systemctl enable --now funding-scanner.timer")
    gcloud_ssh("systemctl enable --now funding-web.service")
    print("  Timer + web enabled")

    # Open firewall port 8080
    print("  Checking firewall...")
    subprocess.run(
        'gcloud compute firewall-rules create allow-funding-web --allow tcp:8080 --target-tags=http-server --quiet 2>&1',
        shell=True, capture_output=True, text=True,
    )

    # Test run
    print("\n  Running first scan...")
    out = gcloud_ssh(f"cd {REMOTE_DIR} && /root/.local/bin/uv run python main.py 2>&1 | tail -10")
    print(out)

    # Check web
    web_status = gcloud_ssh("systemctl is-active funding-web.service").strip()
    print(f"  Web service: {web_status}")
    print(f"\n  Dashboard: http://34.159.55.61:8080")
    print("  Deploy complete!")


def _get_tg_token() -> str:
    """Read TG_BOT_TOKEN from local .env files."""
    for env_path in [LOCAL_DIR / ".env", LOCAL_DIR.parent.parent / ".env"]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("TG_BOT_TOKEN="):
                    return line.split("=", 1)[1].strip()
    return "FILL_ME"


def _write_systemd(name: str, content: str) -> None:
    """Write systemd unit file via heredoc."""
    escaped = content.replace("'", "'\\''")
    gcloud_ssh(f"cat > /etc/systemd/system/{name} << 'UNIT_EOF'\n{content}UNIT_EOF")


if __name__ == "__main__":
    deploy()
