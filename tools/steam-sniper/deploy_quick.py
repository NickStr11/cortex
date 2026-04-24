"""Quick deploy: upload only changed frontend/server files and restart dashboard.

Use when frontend/server changes don't need uv sync, nginx reload, or
listings_snapshot.db refresh. Much faster than deploy.py.

Usage: cd tools/steam-sniper && uv run python deploy_quick.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

VPS_HOST = "72.56.37.150"
VPS_USER = "root"
REMOTE_DIR = "/opt/steam-sniper"
SERVICE_DASHBOARD = "steam-sniper-dashboard"

FILES = [
    "db.py",
    "server.py",
    "category.py",
    "dashboard.html",
    "static/css/styles.css",
    "static/js/catalog.js",
    "static/js/cases.js",
    "static/js/item_detail.js",
    "static/js/lists.js",
    "static/js/main.js",
    "static/js/stats.js",
    "static/js/theme.js",
    "static/js/watchlist.js",
    "static/sw.js",
]


def connect() -> paramiko.SSHClient:
    key_paths = [
        Path.home() / ".ssh" / "vps_key",
        Path.home() / ".ssh" / "id_ed25519",
        Path.home() / ".ssh" / "id_rsa",
    ]
    pkey = None
    for kp in key_paths:
        if not kp.exists():
            continue
        try:
            pkey = paramiko.Ed25519Key.from_private_key_file(str(kp))
            print(f"  Using key: {kp}")
            break
        except paramiko.SSHException:
            try:
                pkey = paramiko.RSAKey.from_private_key_file(str(kp))
                print(f"  Using key: {kp}")
                break
            except paramiko.SSHException:
                continue

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, username=VPS_USER, pkey=pkey, look_for_keys=True, timeout=15)
    return client


def main() -> None:
    print(f"Quick deploy → {VPS_USER}@{VPS_HOST}")
    client = connect()
    sftp = client.open_sftp()
    local_root = Path(__file__).parent

    for rel in FILES:
        local = local_root / rel
        if not local.exists():
            print(f"  SKIP (missing): {rel}")
            continue
        remote = f"{REMOTE_DIR}/{rel}"
        # ensure remote dir
        remote_dir = remote.rsplit("/", 1)[0]
        try:
            sftp.stat(remote_dir)
        except (FileNotFoundError, IOError):
            client.exec_command(f"mkdir -p {remote_dir}")
        sftp.put(str(local), remote)
        print(f"  {rel} → {remote}")

    sftp.close()

    print(f"\nRestarting {SERVICE_DASHBOARD}...")
    stdin, stdout, stderr = client.exec_command(
        f"systemctl restart {SERVICE_DASHBOARD} && systemctl is-active {SERVICE_DASHBOARD}"
    )
    out = stdout.read().decode("utf-8").strip()
    err = stderr.read().decode("utf-8").strip()
    code = stdout.channel.recv_exit_status()
    print(f"  status: {out}")
    if err:
        print(f"  stderr: {err}")
    client.close()

    if code != 0:
        print("DEPLOY FAILED")
        sys.exit(1)
    print(f"\nDone. http://{VPS_HOST}/")


if __name__ == "__main__":
    main()
