"""Deploy Steam Sniper to VPS via paramiko.

Usage: cd tools/steam-sniper && uv run python deploy.py

Connects to VPS 194.87.140.204, uploads project files to /opt/steam-sniper/,
installs dependencies via uv, writes systemd units, sets up nginx, enables+starts services.
"""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

# --- Constants ---

VPS_HOST = "194.87.140.204"
VPS_USER = "root"
REMOTE_DIR = "/opt/steam-sniper"
SERVICE_DASHBOARD = "steam-sniper-dashboard"
SERVICE_BOT = "steam-sniper-bot"

# Project files to upload (relative to this script's directory)
PROJECT_FILES = [
    "server.py",
    "main.py",
    "db.py",
    "category.py",
    "dashboard.html",
    "pyproject.toml",
    ".env",
]

# Static directories to upload recursively
STATIC_DIRS = ["static"]

# Systemd unit files (local path -> remote path)
SYSTEMD_UNITS = {
    "deploy/steam-sniper-dashboard.service": f"/etc/systemd/system/{SERVICE_DASHBOARD}.service",
    "deploy/steam-sniper-bot.service": f"/etc/systemd/system/{SERVICE_BOT}.service",
}

# Nginx config (local path -> remote path)
NGINX_CONF = {
    "deploy/nginx-steam-sniper.conf": "/etc/nginx/sites-available/steam-sniper",
}


def run(client: paramiko.SSHClient, cmd: str, *, step: str = "") -> str:
    """Execute command via SSH, log output, raise on non-zero exit."""
    if step:
        print(f"  [{step}] {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    exit_code = stdout.channel.recv_exit_status()

    if out:
        print(f"    stdout: {out}")
    if err:
        print(f"    stderr: {err}")

    if exit_code != 0:
        msg = f"Command failed (exit {exit_code}): {cmd}"
        if err:
            msg += f"\n  stderr: {err}"
        raise RuntimeError(msg)

    return out


def connect() -> paramiko.SSHClient:
    """Connect to VPS using SSH keys."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Try default key locations
    key_paths = [
        Path.home() / ".ssh" / "vps_key",
        Path.home() / ".ssh" / "id_ed25519",
        Path.home() / ".ssh" / "id_rsa",
    ]

    pkey = None
    for kp in key_paths:
        if kp.exists():
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

    print(f"\n[1/10] Connecting to {VPS_USER}@{VPS_HOST}...")
    try:
        client.connect(
            VPS_HOST,
            username=VPS_USER,
            pkey=pkey,
            look_for_keys=True,
            timeout=15,
        )
    except paramiko.AuthenticationException:
        import getpass

        print("  SSH key auth failed. Enter credentials:")
        cred = getpass.getpass(f"  Passphrase for {VPS_USER}@{VPS_HOST}: ")
        client.connect(VPS_HOST, username=VPS_USER, password=cred, timeout=15)

    print("  Connected.")
    return client


def _ensure_remote_dir(sftp: paramiko.SFTPClient, path: str) -> None:
    """Create remote directory if it doesn't exist (mkdir -p equivalent)."""
    dirs_to_create: list[str] = []
    current = path
    while current and current != "/":
        try:
            sftp.stat(current)
            break
        except FileNotFoundError:
            dirs_to_create.append(current)
            current = str(Path(current).parent)

    for d in reversed(dirs_to_create):
        try:
            sftp.mkdir(d)
        except IOError:
            pass  # already exists (race condition or stat missed it)


def upload_files(client: paramiko.SSHClient) -> None:
    """Upload project files, static dirs, and systemd units to VPS."""
    local_root = Path(__file__).parent
    sftp = client.open_sftp()

    # Upload project files
    print(f"\n[4/10] Uploading project files to {REMOTE_DIR}/...")
    for filename in PROJECT_FILES:
        local_path = local_root / filename
        if not local_path.exists():
            print(f"  WARNING: {local_path} not found, skipping")
            continue
        remote_path = f"{REMOTE_DIR}/{filename}"
        sftp.put(str(local_path), remote_path)
        print(f"  {filename} -> {remote_path}")

    # Upload static directories recursively
    print(f"\n[5/10] Uploading static assets...")
    for static_dir in STATIC_DIRS:
        local_dir = local_root / static_dir
        if not local_dir.is_dir():
            continue
        for local_file in local_dir.rglob("*"):
            if local_file.is_dir():
                continue
            rel = local_file.relative_to(local_root)
            remote_path = f"{REMOTE_DIR}/{rel.as_posix()}"
            # Ensure remote directory exists
            remote_dir = str(Path(remote_path).parent)
            _ensure_remote_dir(sftp, remote_dir)
            sftp.put(str(local_file), remote_path)
            print(f"  {rel} -> {remote_path}")

    # Upload systemd units
    print("\n[6/10] Uploading systemd unit files...")
    for local_rel, remote_path in SYSTEMD_UNITS.items():
        local_path = local_root / local_rel
        if not local_path.exists():
            raise FileNotFoundError(f"Unit file missing: {local_path}")
        sftp.put(str(local_path), remote_path)
        print(f"  {local_rel} -> {remote_path}")

    # Upload nginx config
    print("\n[6.5/10] Uploading nginx config...")
    for local_rel, remote_path in NGINX_CONF.items():
        local_path = local_root / local_rel
        if not local_path.exists():
            raise FileNotFoundError(f"Nginx config missing: {local_path}")
        sftp.put(str(local_path), remote_path)
        print(f"  {local_rel} -> {remote_path}")

    sftp.close()


def main() -> None:
    """Deploy Steam Sniper to VPS."""
    print("=" * 50)
    print("  Steam Sniper -- VPS Deploy")
    print("=" * 50)

    client = connect()

    try:
        # Step 2: Ensure uv installed
        print("\n[2/10] Checking uv installation...")
        run(
            client,
            "command -v /root/.local/bin/uv || curl -LsSf https://astral.sh/uv/install.sh | sh",
            step="uv",
        )

        # Step 3: Create remote dirs
        print(f"\n[3/10] Creating {REMOTE_DIR}/data/...")
        run(client, f"mkdir -p {REMOTE_DIR}/data", step="mkdir")

        # Step 4-6.5: Upload files
        upload_files(client)

        # Step 7: Install dependencies
        print("\n[7/10] Installing dependencies (uv sync)...")
        run(
            client,
            f"cd {REMOTE_DIR} && /root/.local/bin/uv sync",
            step="uv sync",
        )

        # Step 7.5: Setup nginx
        print("\n[7.5/10] Setting up nginx reverse proxy...")
        run(client, "apt-get install -y nginx certbot python3-certbot-nginx", step="nginx")
        run(
            client,
            "ln -sf /etc/nginx/sites-available/steam-sniper /etc/nginx/sites-enabled/steam-sniper",
            step="symlink",
        )
        run(client, "rm -f /etc/nginx/sites-enabled/default", step="rm-default")
        run(client, "nginx -t && systemctl reload nginx", step="nginx-reload")

        # Step 8: Reload systemd
        print("\n[8/10] Reloading systemd daemon...")
        run(client, "systemctl daemon-reload", step="systemd")

        # Step 9: Enable + restart services
        print("\n[9/10] Enabling and starting services...")
        run(
            client,
            f"systemctl enable --now {SERVICE_DASHBOARD} {SERVICE_BOT}",
            step="enable",
        )
        run(
            client,
            f"systemctl restart {SERVICE_DASHBOARD} {SERVICE_BOT}",
            step="restart",
        )

        # Step 10: Verify
        print("\n[10/10] Verifying services...")
        dash_status = run(
            client,
            f"systemctl is-active {SERVICE_DASHBOARD}",
            step="verify-dashboard",
        )
        bot_status = run(
            client,
            f"systemctl is-active {SERVICE_BOT}",
            step="verify-bot",
        )

        print("\n" + "=" * 50)
        print("  Deploy complete!")
        print("=" * 50)
        print(f"\n  Dashboard:  http://{VPS_HOST}:8100")
        print(f"  Dashboard:  {dash_status}")
        print(f"  Bot:        {bot_status}")

        print("\n  HTTPS setup (when domain ready):")
        print("    1. Register subdomain at duckdns.org -> point to 194.87.140.204")
        print("    2. SSH to VPS: ssh root@194.87.140.204")
        print("    3. Run: certbot --nginx -d YOUR_SUBDOMAIN.duckdns.org")
        print("    4. Edit /etc/nginx/sites-available/steam-sniper:")
        print("       - Uncomment HTTPS server block")
        print("       - Uncomment HTTP->HTTPS redirect")
        print("       - Replace SUBDOMAIN with your subdomain")
        print("    5. nginx -t && systemctl reload nginx")
        print()

    except Exception as e:
        print(f"\n  DEPLOY FAILED: {e}")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
