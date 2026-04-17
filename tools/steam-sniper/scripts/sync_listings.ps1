param(
  [string]$OutputPath = "",
  [string]$VpsHost = "72.56.37.150",
  [string]$VpsUser = "root",
  [string]$RemotePath = "/opt/steam-sniper/data/listings_snapshot.db",
  [string]$SshKey = "",
  [switch]$BuildOnly
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
if (-not $OutputPath) {
  $OutputPath = Join-Path $root "data\listings_snapshot.db"
}

if (-not $SshKey) {
  $candidates = @(
    (Join-Path $HOME ".ssh\vps_key"),
    (Join-Path $HOME ".ssh\id_ed25519"),
    (Join-Path $HOME ".ssh\id_rsa")
  )
  foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
      $SshKey = $candidate
      break
    }
  }
}

Push-Location $root
try {
  uv run python scripts/build_listings_snapshot.py --output "$OutputPath"

  if ($BuildOnly) {
    Write-Host "Build complete, upload skipped."
    exit 0
  }

  if (-not $SshKey) {
    throw "SSH key not found. Pass -SshKey explicitly."
  }

  $scp = Get-Command scp.exe -ErrorAction Stop
  $ssh = Get-Command ssh.exe -ErrorAction Stop
  $remoteTmp = "$RemotePath.tmp"

  & $scp.Source -i $SshKey "$OutputPath" "${VpsUser}@${VpsHost}:$remoteTmp"
  & $ssh.Source -i $SshKey "${VpsUser}@${VpsHost}" "mv '$remoteTmp' '$RemotePath' && chmod 644 '$RemotePath'"
}
finally {
  Pop-Location
}
