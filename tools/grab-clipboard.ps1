Add-Type -AssemblyName System.Windows.Forms
$img = [System.Windows.Forms.Clipboard]::GetImage()
if ($null -eq $img) {
    Write-Error "No image in clipboard. Use Win+Shift+S first."
    exit 1
}
$p = Join-Path $env:TEMP "screenshot_claude.png"
$img.Save($p, [System.Drawing.Imaging.ImageFormat]::Png)
$img.Dispose()
Write-Output $p
