"""Deploy Steam Sniper to VPS via paramiko.

Usage: cd tools/steam-sniper && uv run python deploy.py

Connects to VPS 72.56.37.150, uploads project files to /opt/steam-sniper/,
installs dependencies via uv, writes systemd units, sets up nginx, enables+starts services.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import paramiko

# Force UTF-8 stdout on Windows — apt/uv output contains Unicode chars (→, ✓)
# that break default cp1251 encoding.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# --- Constants ---

VPS_HOST = "72.56.37.150"
VPS_USER = "root"
REMOTE_DIR = "/opt/steam-sniper"
SERVICE_DASHBOARD = "steam-sniper-dashboard"
SERVICE_BOT = "steam-sniper-bot"
SERVICE_SNAPSHOT_TIMER = "steam-sniper-snapshot.timer"

# Project files to upload (relative to this script's directory)
PROJECT_FILES = [
    "server.py",
    "build_image_cache.py",
    "listings_snapshot.py",
    "main.py",
    "db.py",
    "category.py",
    "dashboard.html",
    "pyproject.toml",
    ".env",
    "scripts/build_listings_snapshot.py",
]

# Optional data files to upload when present.
OPTIONAL_DATA_FILES = [
    "data/image_cache.json",
    "data/listings_snapshot.db",
]

# Static directories to upload recursively
STATIC_DIRS = ["static"]

# Systemd unit files (local path -> remote path)
SYSTEMD_UNITS = {
    "deploy/steam-sniper-dashboard.service": f"/etc/systemd/system/{SERVICE_DASHBOARD}.service",
    "deploy/steam-sniper-bot.service": f"/etc/systemd/system/{SERVICE_BOT}.service",
    "deploy/steam-sniper-snapshot.service": "/etc/systemd/system/steam-sniper-snapshot.service",
    "deploy/steam-sniper-snapshot.timer": f"/etc/systemd/system/{SERVICE_SNAPSHOT_TIMER}",
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
    last_error: Exception | None = None
    for attempt in range(1, 4):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                VPS_HOST,
                username=VPS_USER,
                pkey=pkey,
                look_for_keys=True,
                timeout=15,
                banner_timeout=30,
                auth_timeout=30,
            )
            print("  Connected.")
            return client
        except paramiko.AuthenticationException:
            import getpass

            print("  SSH key auth failed. Enter credentials:")
            cred = getpass.getpass(f"  Passphrase for {VPS_USER}@{VPS_HOST}: ")
            client.connect(
                VPS_HOST,
                username=VPS_USER,
                password=cred,
                timeout=15,
                banner_timeout=30,
                auth_timeout=30,
            )
            print("  Connected.")
            return client
        except Exception as exc:
            last_error = exc
            client.close()
            if attempt == 3:
                break
            print(f"  Connect attempt {attempt}/3 failed: {exc}")
            time.sleep(2)

    raise RuntimeError(f"SSH connect failed after 3 attempts: {last_error}")


def _ensure_remote_dir(sftp: paramiko.SFTPClient, path: str) -> None:
    """Create remote directory if it doesn't exist (mkdir -p equivalent).

    Uses string split instead of Path — Path on Windows converts / to \\ which
    breaks SFTP paths on remote Linux.
    """
    dirs_to_create: list[str] = []
    current = path
    while current and current != "/" and "/" in current:
        try:
            sftp.stat(current)
            break
        except (FileNotFoundError, IOError):
            dirs_to_create.append(current)
            current = current.rsplit("/", 1)[0]

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
        remote_dir = remote_path.rsplit("/", 1)[0]
        _ensure_remote_dir(sftp, remote_dir)
        sftp.put(str(local_path), remote_path)
        print(f"  {filename} -> {remote_path}")

    print("\n[4.5/10] Uploading optional data files...")
    for filename in OPTIONAL_DATA_FILES:
        local_path = local_root / filename
        if not local_path.exists():
            print(f"  WARNING: {local_path} not found, skipping")
            continue
        remote_path = f"{REMOTE_DIR}/{filename}"
        remote_dir = remote_path.rsplit("/", 1)[0]
        _ensure_remote_dir(sftp, remote_dir)
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
            # Ensure remote directory exists (string split — NOT Path, to avoid
            # Windows backslash conversion on remote Linux SFTP path)
            remote_dir = remote_path.rsplit("/", 1)[0]
            _ensure_remote_dir(sftp, remote_dir)
            sftp.put(str(local_file), remote_path)
            print(f"  {rel} -> {remote_path}", flush=True)

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
            f"systemctl enable --now {SERVICE_DASHBOARD} {SERVICE_BOT} {SERVICE_SNAPSHOT_TIMER}",
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
        snapshot_timer_status = run(
            client,
            f"systemctl is-active {SERVICE_SNAPSHOT_TIMER}",
            step="verify-snapshot-timer",
        )

        print("\n" + "=" * 50)
        print("  Deploy complete!")
        print("=" * 50)
        print(f"\n  Dashboard:  http://{VPS_HOST}/")
        print(f"  Direct app: http://{VPS_HOST}:8100")
        print(f"  Dashboard:  {dash_status}")
        print(f"  Bot:        {bot_status}")
        print(f"  Snapshot:   {snapshot_timer_status}")

        print("\n  HTTPS setup (when domain ready):")
        print(f"    1. Register subdomain at duckdns.org -> point to {VPS_HOST}")
        print(f"    2. SSH to VPS: ssh root@{VPS_HOST}")
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
