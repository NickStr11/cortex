Add-Type -AssemblyName System.Windows.Forms

$img = [System.Windows.Forms.Clipboard]::GetImage()

if ($null -eq $img) {
    Write-Host "Clipboard is empty. Use Win+Shift+S first." -ForegroundColor Red
    exit 1
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$filename = "screenshot_$timestamp.png"
$dir = Join-Path $PSScriptRoot "..\screenshots"

if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }

$filepath = Join-Path $dir $filename
$img.Save($filepath, [System.Drawing.Imaging.ImageFormat]::Png)
$img.Dispose()

$absolute = (Resolve-Path $filepath).Path
Write-Host "Saved: $absolute" -ForegroundColor Green
Set-Clipboard -Value $absolute
Write-Host "Path copied to clipboard. Paste it into Claude Code." -ForegroundColor Cyan
