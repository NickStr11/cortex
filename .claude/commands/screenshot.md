Пользователь сделал скриншот (Win+Shift+S). Сохрани и прочитай.

1. Выполни: `powershell.exe -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; if ([System.Windows.Forms.Clipboard]::ContainsImage()) { [System.Windows.Forms.Clipboard]::GetImage().Save('C:/tmp/clipboard_screenshot.png'); Write-Output 'saved' } else { Write-Output 'no image in clipboard' }"`
2. Прочитай `C:/tmp/clipboard_screenshot.png` через Read tool
3. Опиши что на скриншоте и спроси что с ним делать
